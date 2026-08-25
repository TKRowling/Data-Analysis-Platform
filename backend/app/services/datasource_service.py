from app.schemas.datasource import DatabaseConnection
from app.services.dataset_service import load_database, load_upload, preview

def upload(filename: str, content: bytes) -> dict:
    return preview(load_upload(filename, content))

def connect(config: DatabaseConnection) -> dict:
    return preview(load_database(config))

