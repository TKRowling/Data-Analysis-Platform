from pathlib import Path

import pandas as pd

from app.data.csv_loader import load_csv
from app.data.excel_loader import load_excel

SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls"}


def load_bytes(filename: str, content: bytes) -> pd.DataFrame:
    """Parse an uploaded file into a dataframe based on its extension."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        return load_csv(content)
    if suffix in {".xlsx", ".xls"}:
        return load_excel(content)
    raise ValueError(f"Unsupported data file: {suffix or filename}")
