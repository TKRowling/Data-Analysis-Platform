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
    return ai_analysis_service.analyze(record, request.question, request.conversation_id)


@router.get("/datasets/{dataset_id}/ai-analysis/memory")
def memory(record: ActiveDataset, conversation_id: str | None = None):
    """The exchanges this conversation remembers. Empty until the first question."""
    return {"conversation_id": conversation_id or record.id,
            "turns": ai_analysis_service.memory(record, conversation_id)}


@router.delete("/datasets/{dataset_id}/ai-analysis/memory", status_code=204)
def forget(record: ActiveDataset, conversation_id: str | None = None) -> None:
    """Start over. The next question is planned with no earlier context."""
    ai_analysis_service.forget(record, conversation_id)
