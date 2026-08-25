from fastapi import APIRouter

from app.dependencies import ActiveDataset
from app.schemas.feature_engineering import FeatureRequest, FeatureTransformRequest
from app.services import feature_service

router = APIRouter(prefix="/datasets/{dataset_id}/features", tags=["feature engineering"])


@router.post("", status_code=201)
def create(record: ActiveDataset, request: FeatureRequest):
    """Add a calculated column from an arithmetic expression."""
    return feature_service.create_feature(record, request.name, request.expression)


@router.post("/transform", status_code=201)
def transform(record: ActiveDataset, request: FeatureTransformRequest):
    """Apply a named transform (scaling, encoding, binning, date parts) to a column."""
    return feature_service.transform_feature(record, request.column, request.transform,
                                             request.name, request.bins)
