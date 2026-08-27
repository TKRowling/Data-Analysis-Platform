"""Pattern recognition agent.

Owns relationships between columns: correlation, movement over time, and how rows split
into segments. Never claims causation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.agents.base import Agent, AgentResult, AnalysisPlan, Skill
from app.core.exceptions import AnalysisError
from app.tools.correlation.correlation import correlation_matrix
from app.tools.correlation.thresholds import STRONG, direction, strength
from app.tools.statistics.aggregation import aggregate
from app.utils.dataframe_utils import finite, json_records, numeric_columns

MIN_TREND_POINTS = 3
SMALL_SEGMENT = 5
COUNT_COLUMN = "__segment_rows"


class PatternAgent(Agent):
    name = "pattern_agent"
    title = "Pattern recognition agent"
    role = "Finds correlations, relationships, trends over time, and segments."

    skills = (
        Skill(
            intent="correlation",
            summary="Strength and direction of the link between two numeric columns, "
                    "or the strongest pairs across the whole dataset.",
            tool="tools.correlation.pair_relationship",
            example="Show me the correlation between age and income.",
            numeric=("x", "y"), chart="scatter",
        ),
        Skill(
            intent="trend",
            summary="Direction and rate of change of a numeric column over a date column.",
            tool="numpy.polyfit over tools aggregation",
            example="What's the revenue trend over time?",
            required=("metric",), numeric=("metric",), temporal=("x",), chart="line",
        ),
        Skill(
            intent="segmentation",
            summary="Split rows into cohorts by a categorical column and compare them.",
            tool="tools.statistics.aggregation.aggregate",
            example="Generate a summary of customer segments.",
            required=("group",), categorical=("group",), numeric=("metric",), chart="bar",
        ),
    )

    def handlers(self):
        return {"correlation": self._correlation, "relationship": self._correlation,
                "trend": self._trend, "segmentation": self._segmentation}

    # --------------------------------------------------------------- correlation
    def _correlation(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        left, right = plan.columns.x, plan.columns.y

        if left and right:
            if left == right:
                raise AnalysisError("Pick two different columns to correlate")
            pair = frame[[left, right]].dropna()
            if len(pair) < 3:
                raise AnalysisError(f"Only {len(pair)} rows have both {left} and {right} — "
                                    "too few to correlate")
            value = finite(pair[left].corr(pair[right]))
            if value is None:
                raise AnalysisError(f"Could not compute a correlation between {left} and {right} "
                                    "— one of them may be constant")
            answer = (f"{left} and {right} show a {strength(value)} {direction(value)} association "
                      f"(r = {value}, n = {len(pair):,}). Correlation does not establish causation.")
            return AgentResult(self.name, "correlation", answer,
                               {"columns": [left, right], "correlation": value,
                                "strength": strength(value), "direction": direction(value),
                                "observations": int(len(pair))},
                               plan.chart or "scatter")

        # No pair named — survey the whole frame.
        if len(numeric_columns(frame)) < 2:
            raise AnalysisError("Correlation needs at least two numeric columns")
        corr = correlation_matrix(frame)
        pairs = []
        for index, a in enumerate(corr.columns):
            for b in corr.columns[index + 1:]:
                value = corr.loc[a, b]
                if pd.notna(value):
                    rounded = round(float(value), 4)
                    pairs.append({"left": a, "right": b, "correlation": rounded,
                                  "strength": strength(rounded), "direction": direction(rounded)})
        pairs.sort(key=lambda item: abs(item["correlation"]), reverse=True)
        strong = [p for p in pairs if abs(p["correlation"]) >= STRONG]

        answer = f"Checked {len(pairs)} numeric pairs. {len(strong)} exceeded |r| = {STRONG}."
        if pairs:
            answer += (f" The strongest is {pairs[0]['left']} and {pairs[0]['right']} "
                       f"at r = {pairs[0]['correlation']}.")
        return AgentResult(self.name, "correlation", answer,
                           {"rows": pairs[:20], "strong_count": len(strong),
                            "columns": list(corr.columns),
                            "matrix": [[finite(v) for v in row] for row in corr.to_numpy()]},
                           plan.chart or "heatmap")

    # --------------------------------------------------------------------- trend
    def _trend(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        metric, time_column = plan.columns.metric, plan.columns.x
        if not metric:
            raise AnalysisError("Name a numeric column to measure the trend of")
        if not time_column:
            time_column = next((c for c in frame.columns
                                if pd.api.types.is_datetime64_any_dtype(frame[c])), None)
            if not time_column:
                raise AnalysisError("Trend analysis needs a date or time column")

        clean = frame[[time_column, metric]].dropna().sort_values(time_column)
        clean = clean[np.isfinite(pd.to_numeric(clean[metric], errors="coerce"))]
        if len(clean) < MIN_TREND_POINTS:
            raise AnalysisError(f"Only {len(clean)} rows have both {time_column} and {metric} "
                                "— too few for a trend")

        ordinals = pd.to_datetime(clean[time_column]).map(pd.Timestamp.toordinal).to_numpy(float)
        values = clean[metric].to_numpy(float)
        slope, intercept = np.polyfit(ordinals, values, 1)
        moving = "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"
        span_days = int(ordinals[-1] - ordinals[0]) or 1

        series = clean.set_index(time_column)[metric]
        if span_days > MIN_TREND_POINTS:
            series = series.resample("D").mean().dropna()

        caveats = []
        if len(clean) < 20:
            caveats.append(f"Only {len(clean)} observations — the trend is indicative, not reliable.")

        answer = (f"{metric} is {moving} over {span_days} days of {time_column}, at about "
                  f"{finite(slope)} per day. A linear fit describes direction only, not seasonality.")
        return AgentResult(self.name, "trend", answer,
                           {"metric": metric, "time_column": time_column,
                            "slope_per_day": finite(slope), "intercept": finite(intercept),
                            "direction": moving, "span_days": span_days,
                            "observations": int(len(clean)),
                            "points": [{"date": str(i.date()), "value": finite(v)}
                                       for i, v in series.head(200).items()]},
                           plan.chart or "line", caveats=caveats)

    # -------------------------------------------------------------- segmentation
    def _segmentation(self, record, plan: AnalysisPlan) -> AgentResult:
        frame = record.frame
        group = plan.columns.group
        if not group:
            raise AnalysisError("Segmentation needs a categorical column to group by")
        metric = plan.columns.metric or next(iter(numeric_columns(frame)), None)

        # A private count column, renamed at the end, so a real column named "rows" cannot collide.
        counts = frame.groupby(group, dropna=False).size().reset_index(name=COUNT_COLUMN)
        if metric and metric != group:
            measured = aggregate(frame, metric, "mean", group)
            table = counts.merge(measured, on=group, how="left")
        else:
            metric = None
            table = counts
        table = table.sort_values(COUNT_COLUMN, ascending=False).rename(columns={COUNT_COLUMN: "rows"})

        rows = json_records(table.head(30))
        small = [r[group] for r in rows if isinstance(r.get("rows"), int) and r["rows"] < SMALL_SEGMENT]
        largest = rows[0] if rows else None

        caveats = []
        if small:
            caveats.append(f"{len(small)} segments have fewer than {SMALL_SEGMENT} rows; "
                           "their averages are unstable.")

        answer = f"{group} splits the data into {len(table)} segments."
        if largest:
            answer += f" The largest is {largest[group]} with {largest['rows']:,} rows."
            if metric and isinstance(largest.get(metric), (int, float)):
                answer += f" Its mean {metric} is {largest[metric]:,.2f}."

        return AgentResult(self.name, "segmentation", answer,
                           {"group": group, "metric": metric, "rows": rows,
                            "segments": int(len(table)), "small_segments": small[:10]},
                           plan.chart or "bar", caveats=caveats)