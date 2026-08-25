from fastapi import APIRouter, File, UploadFile
from app.schemas.datasource import DatabaseConnection
from app.services import datasource_service

router = APIRouter(prefix="/datasets", tags=["data source"])

@router.post("/upload", status_code=201)
async def upload(file: UploadFile = File(...)):
    return datasource_service.upload(file.filename or "dataset.csv", await file.read())

@router.post("/database", status_code=201)
def database(config: DatabaseConnection):
    return datasource_service.connect(config)

