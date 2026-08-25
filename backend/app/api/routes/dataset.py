from fastapi import APIRouter, Query
from app.services import dataset_service

router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.get("")
def datasets():
    return [dataset_service.preview(item, 0) for item in dataset_service.store.list()]

@router.get("/{dataset_id}")
def get_dataset(dataset_id: str, limit: int = Query(20, ge=1, le=100)):
    return dataset_service.preview(dataset_service.store.get(dataset_id), limit)

