from fastapi import APIRouter

from app.dependencies import ActiveDataset
from app.schemas.ai_analysis import AIQuestion
from app.services import ai_analysis_service

router = APIRouter(tags=["AI analysis"])


@router.get("/ai/health")
def health():
    """Whether LLM routing and narration are available. Analysis works either way."""
    return ai_analysis_service.llm_status()


@router.post("/datasets/{dataset_id}/ai-analysis")
def analyze(record: ActiveDataset, request: AIQuestion):
    return ai_analysis_service.analyze(record, request.question)
