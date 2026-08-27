"""Statistical agent — the calculator.

Owns anything that reduces a column to a number: totals, averages, rankings, spread,
and IQR outlier detection. Every figure comes from app.tools.
"""
from __future__ import annotations

from app.agents.base import Agent, AgentResult, AnalysisPlan, Skill
from app.core.exceptions import AnalysisError
from app.tools.distribution import numeric_distribution
from app.tools.quality import iqr_outliers
from app.tools.statistics.aggregation import aggregate
from app.utils.dataframe_utils import finite, finite_series, json_records


class StatisticalAgent(Agent):
    name = "statistical_agent"
    title = "Statistical agent"
    role = "Calculates totals, averages, rankings, spread, and outliers."

    skills = (
        Skill(
            intent="aggregation",
            summary="Total, average, median, or count of a numeric column, optionally per category.",
            tool="tools.statistics.aggregation.aggregate",
            example="What's the average revenue by region?",
            required=("metric",), numeric=("metric",), categorical=("group",), chart="bar",
        ),
        Skill(
            intent="ranking",
            summary="The best or worst N categories by a numeric measure.",
            tool="tools.statistics.aggregation.aggregate",
            example="What are the top 5 products by sales?",
            required=("metric", "group"), numeric=("metric",), categorical=("group",), chart="bar",
        ),
        Skill(
            intent="descriptive",
            summary="Mean, median, spread, and shape of one numeric column.",
            tool="tools.distribution.numeric_distribution",
            example="Describe the distribution of price.",
            required=("metric",), numeric=("metric",), chart="histogram",
        ),
        Skill(
            intent="outlier",
            summary="Values beyond 1.5 x IQR from the quartiles of a numeric column.",
            tool="tools.quality.iqr_outliers",
            example="Identify outliers in the price column.",
            required=("metric",), numeric=("metric",), chart="box",
        ),
    )

    def handlers(self):
        return {"aggregation": self._aggregation, "ranking": self._ranking,
                "descriptive": self._descriptive, "outlier": self._outlier}

    # ---------------------------------------------------------------- aggregation
    def _aggregation(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        metric, group = plan.columns.metric, plan.columns.group
        if not metric:
            raise AnalysisError("Name a numeric column to calculate, for example: average revenue by region")

        if group:
            table = aggregate(frame, metric, plan.operation, group).sort_values(metric, ascending=False)
            rows = json_records(table.head(50))
            top = rows[0] if rows else None
            answer = f"Calculated {plan.operation} of {metric} across {len(table)} {group} groups."
            if top and isinstance(top.get(metric), (int, float)):
                answer += f" {top[group]} is highest at {top[metric]:,.2f}."
            data = {"group": group, "metric": metric, "operation": plan.operation,
                    "rows": rows, "groups": int(len(table))}
            return AgentResult(self.name, "aggregation", answer, data, plan.chart or "bar")

        series = finite_series(frame[metric])
        if series.empty:
            raise AnalysisError(f"{metric} has no usable numeric values to aggregate")
        value = finite(getattr(series, plan.operation)())
        answer = f"The {plan.operation} of {metric} is {value:,.2f} across {len(series):,} values."
        data = {"metric": metric, "operation": plan.operation, "value": value, "count": int(len(series))}
        return AgentResult(self.name, "aggregation", answer, data, plan.chart)

    # ------------------------------------------------------------------- ranking
    def _ranking(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        metric, group = plan.columns.metric, plan.columns.group
        if not (metric and group):
            raise AnalysisError("Ranking needs a category and a numeric measure, "
                                "for example: top 5 products by revenue")

        table = aggregate(frame, metric, plan.operation, group).nlargest(plan.limit, metric)
        rows = json_records(table)
        if not rows:
            raise AnalysisError(f"No {group} groups have a usable {metric} value")

        total = float(finite_series(frame[metric]).sum())
        caveats: list[str] = []
        answer = f"The top {len(rows)} {group} values by {plan.operation} of {metric}:"
        # A share is only meaningful when the measure is non-negative and sums above zero.
        if total > 0 and finite_series(frame[metric]).min() >= 0:
            share = float(table[metric].sum() / total * 100)
            answer = (f"The top {len(rows)} {group} values account for {share:.1f}% "
                      f"of total {metric}.")
        else:
            share = None
            caveats.append(f"{metric} contains negative or zero-summing values, so a share of "
                           "the total would be misleading and is omitted.")

        leader = rows[0]
        if isinstance(leader.get(metric), (int, float)):
            answer += f" {leader[group]} leads with {leader[metric]:,.2f}."

        return AgentResult(self.name, "ranking", answer,
                           {"group": group, "metric": metric, "operation": plan.operation,
                            "rows": rows, "combined_share_percent": round(share, 2) if share is not None else None,
                            "limit": plan.limit},
                           plan.chart or "bar", caveats=caveats)

    # --------------------------------------------------------------- descriptive
    def _descriptive(self, record, plan: AnalysisPlan) -> AgentResult:
        metric = plan.columns.metric
        if not metric:
            raise AnalysisError("Name a numeric column to describe")
        series = record.frame[metric]
        usable = finite_series(series)
        if usable.empty:
            raise AnalysisError(f"{metric} has no usable numeric values to describe")

        shape = numeric_distribution(series)
        stats = {"count": int(len(usable)), "mean": finite(shape["mean"]),
                 "median": finite(shape["median"]), "std": finite(shape["std"]),
                 "skewness": finite(shape["skewness"])}
        box = {k: finite(v) for k, v in (shape["box"] or {}).items()}
        skew = stats["skewness"]
        descriptor = ("roughly symmetric" if skew is not None and abs(skew) < .5
                      else "right-skewed" if skew and skew > 0 else "left-skewed")

        caveats = []
        dropped = int(series.notna().sum()) - len(usable)
        if dropped:
            caveats.append(f"{dropped} non-finite values in {metric} were excluded.")

        answer = (f"{metric} has a mean of {stats['mean']} and a median of {stats['median']} "
                  f"across {stats['count']:,} values, with a standard deviation of {stats['std']}. "
                  f"The distribution is {descriptor}.")
        return AgentResult(self.name, "descriptive", answer,
                           {"column": metric, "statistics": stats, "box": box,
                            "histogram": {"counts": shape["counts"],
                                          "edges": [finite(v) for v in shape["edges"]]}},
                           plan.chart or "histogram", caveats=caveats)

    # ------------------------------------------------------------------- outlier
    def _outlier(self, record, plan: AnalysisPlan) -> AgentResult:
        metric = plan.columns.metric
        if not metric:
            raise AnalysisError("Name a numeric column for outlier detection, "
                                "for example: outliers in the price column")
        series = record.frame[metric]
        usable = finite_series(series)
        if usable.empty:
            raise AnalysisError(f"{metric} has no usable numeric values to inspect")

        summary = iqr_outliers(series)
        low, high = finite(summary["lower_bound"]), finite(summary["upper_bound"])
        # Match the tool exactly: flag against the same finite series it measured.
        mask = (usable < summary["lower_bound"]) | (usable > summary["upper_bound"])
        examples = json_records(record.frame.loc[mask[mask].index].head(10))

        answer = (f"Found {summary['count']} IQR outliers in {metric} "
                  f"({summary['percent']}% of usable values), outside the range {low} to {high}. "
                  "They are flagged, not removed — an outlier can be a genuine extreme value.")
        return AgentResult(self.name, "outlier", answer,
                           {"column": metric, "count": summary["count"], "percent": summary["percent"],
                            "lower_bound": low, "upper_bound": high, "rows": examples},
                           plan.chart or "box")