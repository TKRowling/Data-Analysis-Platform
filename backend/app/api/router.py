from fastapi import APIRouter
from app.api.routes import ai_analysis, dataset, datasource, eda, feature_engineering, reports, visualization

router = APIRouter()
router.include_router(datasource.router)
router.include_router(dataset.router)
router.include_router(eda.router)
router.include_router(feature_engineering.router)
router.include_router(ai_analysis.router)
router.include_router(visualization.router)
router.include_router(reports.router)

@router.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
