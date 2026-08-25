from dataclasses import dataclass
from datetime import datetime

@dataclass
class DatasetMetadata:
    id: str
    name: str
    source: str
    rows: int
    columns: int
    created_at: datetime

