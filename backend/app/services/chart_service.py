"""Chart construction. Figures are built by the deterministic builders in app.tools.visualization."""
from __future__ import annotations

import json

from plotly.utils import PlotlyJSONEncoder

from app.core.exceptions import AnalysisError
from app.schemas.models import ChartRequest
from app.tools.visualization import bar_chart, box_plot, heatmap, histogram, line_chart, pie_chart, scatter_chart

NEEDS_X = {"bar", "line", "scatter", "histogram", "pie"}
NEEDS_Y = {"line", "scatter"}


def _aggregate(frame, request: ChartRequest):
    """Collapse the frame to one row per X value. Returns (frame, y_column)."""
    if not request.x:
        raise AnalysisError("X axis is required for aggregation")
    if request.aggregation == "count":
        return frame.groupby(request.x, dropna=False).size().reset_index(name="count"), "count"
    if not request.y:
        raise AnalysisError(f"Y axis is required to aggregate with '{request.aggregation}'")
    grouped = frame.groupby(request.x, dropna=False)[request.y].agg(request.aggregation).reset_index()
    return grouped, request.y


def create_chart(record, request: ChartRequest) -> dict:
    frame = record.frame.copy()
    for col in (request.x, request.y, request.color):
        if col and col not in frame:
            raise AnalysisError(f"Unknown column: {col}")

    if request.chart_type != "heatmap":
        if request.chart_type in NEEDS_X and not request.x:
            raise AnalysisError(f"A {request.chart_type} chart needs an X axis column")
        if request.aggregation == "none" and request.chart_type in NEEDS_Y and not request.y:
            raise AnalysisError(f"A {request.chart_type} chart needs a Y axis column")

    if request.aggregation != "none" and request.chart_type != "heatmap":
        frame, y = _aggregate(frame, request)
        color = request.color if request.color in frame.columns else None
    else:
        y, color = request.y, request.color

    if request.chart_type == "pie" and not y:
        raise AnalysisError("A pie chart needs a numeric Y column for slice sizes, or an aggregation such as 'count'")

    builders = {
        "bar": lambda: bar_chart(frame, x=request.x, y=y, color=color, title=request.title),
        "line": lambda: line_chart(frame, x=request.x, y=y, color=color, title=request.title),
        "scatter": lambda: scatter_chart(frame, x=request.x, y=y, color=color, title=request.title),
        "histogram": lambda: histogram(frame, x=request.x, color=color, title=request.title),
        "box": lambda: box_plot(frame, x=request.x, y=y, color=color, title=request.title),
        "pie": lambda: pie_chart(frame, names=request.x, values=y, title=request.title),
        "heatmap": lambda: heatmap(frame, title=request.title or "Correlation heatmap"),
    }
    if request.chart_type not in builders:
        raise AnalysisError(f"Unsupported chart type: {request.chart_type}")
    try:
        figure = builders[request.chart_type]()
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Chart could not be generated: {exc}") from exc
    figure.update_layout(template="plotly_white", margin=dict(l=40, r=20, t=60, b=40))
    # Plotly returns numpy arrays and pandas timestamps that FastAPI's encoder cannot handle.
    # PlotlyJSONEncoder normalises them to plain JSON types.
    return json.loads(json.dumps(figure.to_plotly_json(), cls=PlotlyJSONEncoder))
