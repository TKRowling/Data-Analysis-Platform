"""Predictive agent.

Fits a model on a held-out split and reports how it scored. It never presents a prediction
as fact, and it is deliberately blunt about weak models.
"""
from __future__ import annotations

import pandas as pd

from app.agents.base import Agent, AgentResult, AnalysisPlan, Skill
from app.core.exceptions import AnalysisError
from app.tools.correlation.thresholds import LEAKAGE
from app.tools.prediction.classification import train_classifier
from app.tools.prediction.forecasting import trend_forecast
from app.tools.prediction.regression import train_regression
from app.utils.dataframe_utils import finite, finite_series, numeric_columns

MAX_FEATURES = 10
AUTO_FEATURES = 5


class PredictiveAgent(Agent):
    name = "predictive_agent"
    title = "Predictive agent"
    role = "Fits regression, classification, and forecast models and reports their scores."

    skills = (
        Skill(
            intent="regression",
            summary="Predict a numeric target from numeric features; reports R2 and RMSE.",
            tool="tools.prediction.train_regression",
            example="Predict revenue from units and price.",
            required=("target",), numeric=("target", "features"), chart="scatter",
        ),
        Skill(
            intent="classification",
            summary="Predict a categorical target from numeric features; reports accuracy "
                    "against the majority-class baseline.",
            tool="tools.prediction.train_classifier",
            example="Can we classify grade from price and quantity?",
            required=("target",), categorical=("target",), numeric=("features",), chart="bar",
        ),
        Skill(
            intent="forecast",
            summary="Extrapolate a numeric column forward along a date column.",
            tool="tools.prediction.trend_forecast",
            example="Forecast revenue for the next 3 periods.",
            required=("metric",), numeric=("metric",), temporal=("x",), chart="line",
        ),
    )

    def handlers(self):
        return {"regression": self._regression, "classification": self._classification,
                "forecast": self._forecast}

    # ------------------------------------------------------------------ features
    def _features(self, record, plan: AnalysisPlan, target: str) -> tuple[list[str], list[str]]:
        """Return (features, caveats).

        Features the user named are honoured. When none were named we auto-select, and we
        drop any column that is near-perfectly correlated with the target — that is almost
        always a column derived from it (a calculated feature, a rescaled copy), and
        including it inflates the score while measuring nothing.

        This check is pairwise, so it catches linear duplicates only. It cannot see a
        multiplicative identity such as ``revenue = units * price``: neither factor is
        strongly correlated with the product on its own, yet together they reconstruct it
        exactly. That is why auto-selection always emits a caveat — a high R2 from features
        the user did not choose deserves a second look, not celebration.
        """
        frame = record.frame
        caveats: list[str] = []
        named = [c for c in plan.columns.features
                 if c in frame.columns and c != target and c in numeric_columns(frame)]
        if named:
            return named[:MAX_FEATURES], caveats

        candidates = [c for c in numeric_columns(frame) if c != target]
        leaked = []
        if target in numeric_columns(frame):
            target_values = frame[target]
            for column in list(candidates):
                pair = frame[[column, target]].dropna()
                if len(pair) < 3:
                    continue
                value = pair[column].corr(pair[target])
                if pd.notna(value) and abs(value) >= LEAKAGE:
                    candidates.remove(column)
                    leaked.append(column)
            del target_values

        if leaked:
            caveats.append(f"Excluded {', '.join(leaked)} — near-perfectly correlated with "
                           f"{target}, so almost certainly derived from it rather than "
                           "predictive of it.")
        chosen = candidates[:AUTO_FEATURES]
        if chosen:
            caveats.append(f"No features were named, so {', '.join(chosen)} were selected "
                           "automatically. Name the columns you care about for a targeted model.")
        return chosen, caveats

    # ---------------------------------------------------------------- regression
    def _regression(self, record, plan: AnalysisPlan) -> AgentResult:
        target = plan.columns.target or plan.columns.metric
        if not target:
            raise AnalysisError("Name the numeric column to predict, "
                                "for example: predict revenue from units and price")
        features, caveats = self._features(record, plan, target)
        if not features:
            raise AnalysisError(f"No usable numeric feature columns are available to predict {target}")

        result = _compute(train_regression, record.frame, features, target)
        r2, rmse = round(result["r2"], 4), round(result["rmse"], 4)
        verdict = ("explains most of the variance" if r2 >= .7
                   else "explains some of the variance" if r2 >= .3
                   else "explains little of the variance")
        if r2 < 0.3:
            caveats.append("A low R2 means these features do not explain the target well. "
                           "Treat this as evidence against the relationship, not a tuning problem.")

        answer = (f"A linear model of {target} from {', '.join(features)} reached R2 = {r2} on "
                  f"{result['test_rows']} held-out rows, which {verdict}. RMSE is {rmse}, and the "
                  f"strongest association is {result['strongest_feature']}. This is an association, "
                  "not a causal claim.")
        return AgentResult(self.name, "regression", answer, {**result, "r2": r2, "rmse": rmse},
                           plan.chart or "scatter", caveats=caveats)

    # ------------------------------------------------------------ classification
    def _classification(self, record, plan: AnalysisPlan) -> AgentResult:
        target = plan.columns.target or plan.columns.group
        if not target:
            raise AnalysisError("Name the categorical column to predict")
        features, caveats = self._features(record, plan, target)
        if not features:
            raise AnalysisError(f"No usable numeric feature columns are available to predict {target}")

        result = _compute(train_classifier, record.frame, features, target)
        accuracy, baseline = round(result["accuracy"], 4), round(result["baseline_accuracy"], 4)
        if result["beats_baseline"]:
            verdict = f"ahead of the {baseline} majority-class baseline"
        else:
            verdict = (f"at or below the {baseline} majority-class baseline, so these features "
                       "carry little signal")
            caveats.append("Always predicting the most common class would score as well. "
                           "That is a real finding about the data, not a model failure.")

        answer = (f"A logistic model predicting {target} from {', '.join(features)} reached "
                  f"{accuracy} accuracy on {result['test_rows']} held-out rows — {verdict}. "
                  f"The strongest feature is {result['strongest_feature']}.")
        return AgentResult(self.name, "classification", answer,
                           {**result, "accuracy": accuracy, "baseline_accuracy": baseline},
                           plan.chart or "bar", caveats=caveats)

    # ------------------------------------------------------------------ forecast
    def _forecast(self, record, plan: AnalysisPlan) -> AgentResult:
        metric = plan.columns.metric or plan.columns.target
        if not metric:
            raise AnalysisError("Name the numeric column to forecast")
        frame = record.frame
        time_column = plan.columns.x or next(
            (c for c in frame.columns if pd.api.types.is_datetime64_any_dtype(frame[c])), None)

        if time_column:
            clean = frame[[time_column, metric]].dropna().sort_values(time_column)
            values = pd.to_numeric(clean[metric], errors="coerce")
            keep = values.notna()
            series = pd.Series(values[keep].to_numpy(float),
                               index=pd.DatetimeIndex(clean.loc[keep, time_column]))
        else:
            series = finite_series(frame[metric]).reset_index(drop=True)

        result = _compute(trend_forecast, series, periods=max(plan.limit, 3))
        projected = [finite(v) for v in result["forecast"]]
        caveats = ["A linear extrapolation assumes the past trend continues and ignores seasonality."]
        if result["fit_r2"] < 0.3:
            caveats.append(f"The trend line fits poorly (R2 = {round(result['fit_r2'], 4)}), "
                           "so this projection carries very little information.")
        if not time_column:
            caveats.append("No date column was available, so points were treated as evenly spaced.")

        answer = (f"{metric} is {result['direction']} across {result['observations']} observations "
                  f"(trend fit R2 = {round(result['fit_r2'], 4)}). Projecting that line forward gives "
                  f"{', '.join(str(v) for v in projected)}.")
        return AgentResult(self.name, "forecast", answer,
                           {**result, "forecast": projected, "metric": metric,
                            "time_column": time_column},
                           plan.chart or "line", caveats=caveats)


def _compute(tool, *args, **kwargs):
    """Run a prediction tool, converting its guardrail errors into a clean 422.

    AnalysisError subclasses ValueError, so it is re-raised untouched rather than rewrapped.
    """
    try:
        return tool(*args, **kwargs)
    except AnalysisError:
        raise
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc