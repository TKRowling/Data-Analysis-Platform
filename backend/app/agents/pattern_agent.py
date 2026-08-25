"""Correlation, pairwise relationships, trends over time, and segmentation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.agents.base import Agent, AgentResult, AnalysisPlan
from app.core.exceptions import AnalysisError
from app.tools.correlation.correlation import correlation_matrix
from app.tools.correlation.relationship import pair_relationship
from app.tools.statistics.aggregation import aggregate
from app.utils.dataframe_utils import finite, json_records, numeric_columns

STRONG, MODERATE = 0.7, 0.4


class PatternAgent(Agent):
    name = "pattern_agent"

    matrix = staticmethod(correlation_matrix)
    relationship = staticmethod(pair_relationship)

    def run(self, record, plan: AnalysisPlan) -> AgentResult:
        handler = {"correlation": self._correlation, "relationship": self._correlation,
                   "trend": self._trend, "segmentation": self._segmentation}.get(plan.intent)
        if handler is None:
            raise AnalysisError(f"The pattern agent cannot handle '{plan.intent}'")
        return handler(record, plan)

    def _correlation(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        left, right = plan.columns.x, plan.columns.y
        if left and right:
            if frame[left].dropna().empty or frame[right].dropna().empty:
                raise AnalysisError(f"{left} or {right} has no values to correlate")
            result = pair_relationship(frame, left, right)
            value = finite(result["correlation"])
            if value is None:
                raise AnalysisError(f"Could not compute a correlation between {left} and {right}")
            direction = "positive" if value >= 0 else "negative"
            answer = (f"{left} and {right} show a {result['strength']} {direction} association "
                      f"(r = {value}). Correlation does not establish causation.")
            return AgentResult(self.name, "correlation", answer,
                               {"columns": [left, right], "correlation": value,
                                "strength": result["strength"], "direction": direction},
                               plan.chart or "scatter")

        # No pair named - report the strongest relationships across the whole frame.
        numeric = numeric_columns(frame)
        if len(numeric) < 2:
            raise AnalysisError("Correlation needs at least two numeric columns")
        corr = correlation_matrix(frame)
        pairs = []
        for i, a in enumerate(corr.columns):
            for b in corr.columns[i + 1:]:
                value = corr.loc[a, b]
                if pd.notna(value):
                    pairs.append({"left": a, "right": b, "correlation": round(float(value), 4),
                                  "strength": "strong" if abs(value) >= STRONG else "moderate" if abs(value) >= MODERATE else "weak"})
        pairs.sort(key=lambda item: abs(item["correlation"]), reverse=True)
        strong = [p for p in pairs if abs(p["correlation"]) >= STRONG]
        answer = (f"Checked {len(pairs)} numeric pairs. {len(strong)} exceeded |r| = 0.7."
                  + (f" The strongest is {pairs[0]['left']} and {pairs[0]['right']} at r = {pairs[0]['correlation']}." if pairs else ""))
        return AgentResult(self.name, "correlation", answer,
                           {"rows": pairs[:20], "strong_count": len(strong),
                            "columns": list(corr.columns),
                            "matrix": [[finite(v) for v in row] for row in corr.to_numpy()]},
                           plan.chart or "heatmap")

    def _trend(self, record, plan: AnalysisPlan) -> AgentResult:
        metric, time_column = plan.columns.metric, plan.columns.x
        if not metric:
            raise AnalysisError("Name a numeric column to measure the trend of")
        frame = record.frame
        if not time_column:
            candidates = [c for c in frame.columns if str(frame[c].dtype).startswith("datetime")]
            if not candidates:
                raise AnalysisError("Trend analysis needs a date or time column")
            time_column = candidates[0]
        clean = frame[[time_column, metric]].dropna().sort_values(time_column)
        if len(clean) < 3:
            raise AnalysisError(f"Only {len(clean)} rows have both {time_column} and {metric} — too few for a trend")
        ordinals = pd.to_datetime(clean[time_column]).map(pd.Timestamp.toordinal).to_numpy(float)
        values = clean[metric].to_numpy(float)
        slope, intercept = np.polyfit(ordinals, values, 1)
        direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"
        span_days = int(ordinals[-1] - ordinals[0]) or 1
        series = clean.set_index(time_column)[metric].resample("D").mean().dropna() if span_days > 3 else clean.set_index(time_column)[metric]
        answer = (f"{metric} is {direction} over {span_days} days of {time_column}, at about "
                  f"{finite(slope)} per day. A linear fit describes direction only, not seasonality.")
        return AgentResult(self.name, "trend", answer,
                           {"metric": metric, "time_column": time_column, "slope_per_day": finite(slope),
                            "intercept": finite(intercept), "direction": direction, "span_days": span_days,
                            "points": [{"date": str(index.date()), "value": finite(value)} for index, value in series.head(200).items()]},
                           plan.chart or "line")

    def _segmentation(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        group = plan.columns.group
        if not group:
            raise AnalysisError("Segmentation needs a categorical column to group by")
        metric = plan.columns.metric or next(iter(numeric_columns(frame)), None)
        counts = frame.groupby(group, dropna=False).size().reset_index(name="rows")
        if metric:
            measured = aggregate(frame, metric, "mean", group)
            table = counts.merge(measured, on=group, how="left").sort_values("rows", ascending=False)
        else:
            table = counts.sort_values("rows", ascending=False)
        rows = json_records(table.head(30))
        small = [r[group] for r in rows if isinstance(r.get("rows"), int) and r["rows"] < 5]
        largest = rows[0] if rows else None
        answer = (f"{group} splits the data into {len(table)} segments."
                  + (f" The largest is {largest[group]} with {largest['rows']} rows." if largest else "")
                  + (f" {len(small)} segments have fewer than 5 rows and are not reliable." if small else ""))
        return AgentResult(self.name, "segmentation", answer,
                           {"group": group, "metric": metric, "rows": rows, "segments": len(table),
                            "small_segments": small[:10]},
                           plan.chart or "bar")
