"""Regression, classification, and forecasting. Metrics come from scikit-learn on a held-out split."""
from __future__ import annotations

import pandas as pd

from app.agents.base import Agent, AgentResult, AnalysisPlan
from app.core.exceptions import AnalysisError
from app.tools.prediction.classification import train_classifier
from app.tools.prediction.forecasting import naive_forecast, trend_forecast
from app.tools.prediction.regression import train_regression
from app.utils.dataframe_utils import finite, numeric_columns


class PredictiveAgent(Agent):
    name = "predictive_agent"

    regression = staticmethod(train_regression)
    classification = staticmethod(train_classifier)
    forecast = staticmethod(naive_forecast)

    def run(self, record, plan: AnalysisPlan) -> AgentResult:
        handler = {"regression": self._regression, "classification": self._classification,
                   "forecast": self._forecast}.get(plan.intent)
        if handler is None:
            raise AnalysisError(f"The predictive agent cannot handle '{plan.intent}'")
        return handler(record, plan)

    def _features(self, record, plan: AnalysisPlan, target: str) -> list[str]:
        chosen = [c for c in plan.columns.features if c in record.frame.columns and c != target]
        if chosen:
            return chosen[:10]
        return [c for c in numeric_columns(record.frame) if c != target][:5]

    def _regression(self, record, plan: AnalysisPlan) -> AgentResult:
        target = plan.columns.target or plan.columns.metric
        if not target:
            raise AnalysisError("Name the numeric column to predict, for example: predict revenue from units and price")
        features = self._features(record, plan, target)
        if not features:
            raise AnalysisError(f"No numeric feature columns available to predict {target}")
        try:
            result = train_regression(record.frame, features, target)
        except ValueError as exc:
            raise AnalysisError(str(exc)) from exc
        r2, rmse = round(result["r2"], 4), round(result["rmse"], 4)
        quality = "explains most of the variance" if r2 >= .7 else "explains some of the variance" if r2 >= .3 else "explains little of the variance"
        answer = (f"A linear model of {target} from {', '.join(features)} reached R² = {r2} on {result['test_rows']} "
                  f"held-out rows, which {quality}. RMSE is {rmse}, and the strongest association is "
                  f"{result['strongest_feature']}. This is an association, not a causal claim.")
        return AgentResult(self.name, "regression", answer, {**result, "r2": r2, "rmse": rmse},
                           plan.chart or "scatter")

    def _classification(self, record, plan: AnalysisPlan) -> AgentResult:
        target = plan.columns.target or plan.columns.group
        if not target:
            raise AnalysisError("Name the categorical column to predict")
        features = self._features(record, plan, target)
        if not features:
            raise AnalysisError(f"No numeric feature columns available to predict {target}")
        try:
            result = train_classifier(record.frame, features, target)
        except ValueError as exc:
            raise AnalysisError(str(exc)) from exc
        accuracy, baseline = round(result["accuracy"], 4), round(result["baseline_accuracy"], 4)
        verdict = (f"ahead of the {baseline} majority-class baseline" if result["beats_baseline"]
                   else f"at or below the {baseline} majority-class baseline, so these features carry little signal")
        answer = (f"A logistic model predicting {target} from {', '.join(features)} reached {accuracy} accuracy "
                  f"on {result['test_rows']} held-out rows — {verdict}. The strongest feature is {result['strongest_feature']}.")
        return AgentResult(self.name, "classification", answer,
                           {**result, "accuracy": accuracy, "baseline_accuracy": baseline}, plan.chart or "bar")

    def _forecast(self, record, plan: AnalysisPlan) -> AgentResult:
        metric = plan.columns.metric or plan.columns.target
        if not metric:
            raise AnalysisError("Name the numeric column to forecast")
        frame = record.frame
        time_column = plan.columns.x or next((c for c in frame.columns if str(frame[c].dtype).startswith("datetime")), None)
        if time_column:
            clean = frame[[time_column, metric]].dropna().sort_values(time_column)
            series = pd.Series(clean[metric].to_numpy(float), index=pd.DatetimeIndex(clean[time_column]))
        else:
            series = frame[metric].dropna().reset_index(drop=True)
        try:
            result = trend_forecast(series, periods=max(plan.limit, 3))
        except ValueError as exc:
            raise AnalysisError(str(exc)) from exc
        projected = [finite(v) for v in result["forecast"]]
        answer = (f"{metric} is {result['direction']} across {result['observations']} observations "
                  f"(trend fit R² = {round(result['fit_r2'], 4)}). Projecting that line forward gives "
                  f"{', '.join(str(v) for v in projected)}. This extrapolates past behaviour and assumes nothing changes.")
        return AgentResult(self.name, "forecast", answer,
                           {**result, "forecast": projected, "metric": metric, "time_column": time_column},
                           plan.chart or "line")
