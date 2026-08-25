"""Aggregations, rankings, descriptive measures, and outlier detection."""
from __future__ import annotations

from app.agents.base import Agent, AgentResult, AnalysisPlan
from app.core.exceptions import AnalysisError
from app.tools.distribution import numeric_distribution
from app.tools.quality import iqr_outliers
from app.tools.statistics.aggregation import aggregate
from app.tools.statistics.descriptive_stats import describe_numeric
from app.utils.dataframe_utils import finite, json_records


class StatisticalAgent(Agent):
    name = "statistical_agent"

    # Preserved for direct tool access and backwards compatibility.
    aggregate = staticmethod(aggregate)
    describe = staticmethod(describe_numeric)

    def run(self, record, plan: AnalysisPlan) -> AgentResult:
        handler = {"aggregation": self._aggregation, "ranking": self._ranking,
                   "descriptive": self._descriptive, "outlier": self._outlier}.get(plan.intent)
        if handler is None:
            raise AnalysisError(f"The statistical agent cannot handle '{plan.intent}'")
        return handler(record, plan)

    def _aggregation(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        metric, group = plan.columns.metric, plan.columns.group
        if not metric:
            raise AnalysisError("Name a numeric column to calculate, for example: average revenue by region")
        if group:
            table = aggregate(frame, metric, plan.operation, group).sort_values(metric, ascending=False)
            rows = json_records(table.head(50))
            top = rows[0] if rows else None
            answer = (f"Calculated {plan.operation} of {metric} across {len(table)} {group} groups."
                      + (f" {top[group]} is highest at {top[metric]:,.2f}." if top and isinstance(top.get(metric), (int, float)) else ""))
            data = {"group": group, "metric": metric, "operation": plan.operation,
                    "rows": rows, "groups": len(table)}
        else:
            value = finite(getattr(frame[metric], plan.operation)())
            answer = f"The {plan.operation} of {metric} is {value:,.2f}." if value is not None else f"{metric} has no values to aggregate."
            data = {"metric": metric, "operation": plan.operation, "value": value}
        return AgentResult(self.name, "aggregation", answer, data, plan.chart or ("bar" if group else None))

    def _ranking(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        metric, group = plan.columns.metric, plan.columns.group
        if not (metric and group):
            raise AnalysisError("Ranking needs a category and a numeric measure, for example: top 5 products by revenue")
        table = aggregate(frame, metric, plan.operation, group).nlargest(plan.limit, metric)
        total = frame[metric].sum()
        share = float(table[metric].sum() / total * 100) if total else 0.0
        rows = json_records(table)
        leader = rows[0] if rows else None
        answer = (f"The top {len(rows)} {group} values account for {share:.1f}% of total {metric}."
                  + (f" {leader[group]} leads with {leader[metric]:,.2f}." if leader and isinstance(leader.get(metric), (int, float)) else ""))
        return AgentResult(self.name, "ranking", answer,
                           {"group": group, "metric": metric, "operation": plan.operation,
                            "rows": rows, "combined_share_percent": round(share, 2), "limit": plan.limit},
                           plan.chart or "bar")

    def _descriptive(self, record, plan: AnalysisPlan) -> AgentResult:
        metric = plan.columns.metric
        if not metric:
            raise AnalysisError("Name a numeric column to describe")
        series = record.frame[metric]
        shape = numeric_distribution(series)
        stats = {"count": int(series.dropna().count()), "mean": finite(shape["mean"]), "median": finite(shape["median"]),
                 "std": finite(shape["std"]), "skewness": finite(shape["skewness"])}
        box = {k: finite(v) for k, v in (shape["box"] or {}).items()}
        skew = stats["skewness"]
        descriptor = "roughly symmetric" if skew is not None and abs(skew) < .5 else ("right-skewed" if skew and skew > 0 else "left-skewed")
        answer = (f"{metric} has a mean of {stats['mean']} and a median of {stats['median']} across "
                  f"{stats['count']} values, with a standard deviation of {stats['std']}. The distribution is {descriptor}.")
        return AgentResult(self.name, "descriptive", answer,
                           {"column": metric, "statistics": stats, "box": box,
                            "histogram": {"counts": shape["counts"], "edges": [finite(v) for v in shape["edges"]]}},
                           plan.chart or "histogram")

    def _outlier(self, record, plan: AnalysisPlan) -> AgentResult:
        metric = plan.columns.metric
        if not metric:
            raise AnalysisError("Name a numeric column for outlier detection, for example: outliers in the price column")
        series = record.frame[metric]
        if series.dropna().empty:
            raise AnalysisError(f"{metric} has no values to inspect")
        summary = iqr_outliers(series)
        low, high = finite(summary["lower_bound"]), finite(summary["upper_bound"])
        mask = (series < summary["lower_bound"]) | (series > summary["upper_bound"])
        examples = json_records(record.frame.loc[mask.fillna(False)].head(10))
        answer = (f"Found {summary['count']} IQR outliers in {metric} ({summary['percent']}% of non-null values), "
                  f"outside the range {low} to {high}. They are flagged, not removed — an outlier can be a genuine extreme value.")
        return AgentResult(self.name, "outlier", answer,
                           {"column": metric, "count": summary["count"], "percent": summary["percent"],
                            "lower_bound": low, "upper_bound": high, "rows": examples},
                           plan.chart or "box")
