"""Data ingestion. Pure functions with no dependency on the service layer."""
from .csv_loader import load_csv
from .database_loader import load_query
from .excel_loader import load_excel
from .loader import SUPPORTED_SUFFIXES, load_bytes

__all__ = ["load_bytes", "load_csv", "load_excel", "load_query", "SUPPORTED_SUFFIXES"]
