from typing import Any
from pydantic import BaseModel

class DatasetSummary(BaseModel):
    id: str
    name: str
    source: str
    rows: int
    columns: int
    column_names: list[str]
    preview: list[dict[str, Any]]

