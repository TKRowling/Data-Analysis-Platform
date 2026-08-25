from __future__ import annotations

import re
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from app.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES
from app.core.exceptions import AnalysisError, DatasetNotFoundError
from app.data.database_loader import load_query
from app.data.loader import load_bytes
from app.schemas.models import DatabaseConnection
from app.utils.dataframe_utils import json_records as _json_records


@dataclass
class DatasetRecord:
    id: str
    name: str
    source: str
    frame: pd.DataFrame


class DatasetStore:
    def __init__(self) -> None:
        self._items: dict[str, DatasetRecord] = {}
        self._lock = threading.RLock()

    def add(self, name: str, source: str, frame: pd.DataFrame) -> DatasetRecord:
        record = DatasetRecord(str(uuid.uuid4()), name, source, normalize_frame(frame))
        with self._lock:
            self._items[record.id] = record
        return record

    def get(self, dataset_id: str) -> DatasetRecord:
        with self._lock:
            record = self._items.get(dataset_id)
        if record is None:
            raise DatasetNotFoundError(dataset_id)
        return record

    def list(self) -> list[DatasetRecord]:
        with self._lock:
            return list(self._items.values())


store = DatasetStore()


def normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(col).strip() for col in frame.columns]
    for col in frame.select_dtypes(include="object"):
        if any(token in col.lower() for token in ("date", "time", "created", "updated")):
            converted = pd.to_datetime(frame[col], errors="coerce")
            if converted.notna().mean() >= 0.8:
                frame[col] = converted
    return frame


def load_upload(filename: str, content: bytes) -> DatasetRecord:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise AnalysisError("Only CSV, XLSX, and XLS files are supported")
    if len(content) > MAX_UPLOAD_BYTES:
        raise AnalysisError("File exceeds the 100 MB limit")
    try:
        frame = load_bytes(filename, content)
    except Exception as exc:
        raise AnalysisError(f"Could not parse file: {exc}") from exc
    if frame.empty or len(frame.columns) == 0:
        raise AnalysisError("Dataset is empty")
    return store.add(filename, "file", frame)


def load_database(config: DatabaseConnection) -> DatasetRecord:
    if not re.match(r"^\s*select\b", config.query, re.I):
        raise AnalysisError("Only SELECT queries are allowed")
    driver = "postgresql+psycopg" if config.database_type == "postgresql" else "mysql+pymysql"
    from urllib.parse import quote_plus
    url = f"{driver}://{quote_plus(config.username)}:{quote_plus(config.password)}@{config.host}:{config.port}/{config.database}"
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            frame = load_query(connection, config.query)
        engine.dispose()
    except Exception as exc:
        raise AnalysisError(f"Database query failed: {exc}") from exc
    return store.add(config.database, config.database_type, frame)


def preview(record: DatasetRecord, limit: int = 20) -> dict:
    frame = record.frame
    return {
        "id": record.id, "name": record.name, "source": record.source,
        "rows": len(frame), "columns": len(frame.columns),
        "column_names": list(frame.columns),
        "preview": json_records(frame.head(limit)),
    }


def json_records(frame: pd.DataFrame) -> list[dict]:
    """Re-exported from :mod:`app.utils.dataframe_utils` so existing imports keep working."""
    return _json_records(frame)

