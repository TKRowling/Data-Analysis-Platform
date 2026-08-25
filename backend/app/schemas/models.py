from typing import Any, Literal
from pydantic import BaseModel, Field


class DatabaseConnection(BaseModel):
    database_type: Literal["postgresql", "mysql"]
    host: str
    port: int = Field(gt=0, le=65535)
    database: str
    username: str
    password: str
    query: str = Field(description="Read-only SELECT query")


class FeatureRequest(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    expression: str


class FeatureTransformRequest(BaseModel):
    column: str
    transform: Literal["standardize", "min_max", "one_hot", "frequency", "datetime_parts", "log", "bin"]
    name: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    bins: int = Field(default=4, ge=2, le=20)


class ChartRequest(BaseModel):
    chart_type: Literal["bar", "line", "scatter", "histogram", "box", "pie", "heatmap"]
    x: str | None = None
    y: str | None = None
    aggregation: Literal["none", "sum", "mean", "count", "min", "max"] = "none"
    color: str | None = None
    title: str | None = None


class AIQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class ReportRequest(BaseModel):
    title: str = "Dataset Analysis Report"
    sections: list[str] = ["executive_summary", "overview", "quality", "statistics", "correlation", "insights"]
    format: Literal["html", "markdown", "pdf"] = "html"
    insights: list[dict[str, Any]] = []

