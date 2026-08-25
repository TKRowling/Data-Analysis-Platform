from fastapi import APIRouter

from app.dependencies import ActiveDataset
from app.schemas.visualization import ChartRequest
from app.services import visualization_service

router = APIRouter(prefix="/datasets/{dataset_id}/charts", tags=["visualization"])


@router.post("")
def create(record: ActiveDataset, request: ChartRequest):
    return visualization_service.create_chart(record, request)
