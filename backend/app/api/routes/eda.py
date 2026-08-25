from fastapi import APIRouter, Query

from app.dependencies import ActiveDataset
from app.services import eda_service

router = APIRouter(prefix="/datasets/{dataset_id}/eda", tags=["exploratory analysis"])


@router.get("/overview")
def overview(record: ActiveDataset): return eda_service.overview(record)


@router.get("/statistics")
def statistics(record: ActiveDataset): return eda_service.statistics(record)


@router.get("/quality")
def quality(record: ActiveDataset): return eda_service.quality(record)


@router.get("/correlation")
def correlation(record: ActiveDataset, method: str = Query("pearson", pattern="^(pearson|spearman|kendall)$")):
    return eda_service.correlation(record, method)


@router.get("/distribution")
def distribution(record: ActiveDataset, column: str): return eda_service.distribution(record, column)
