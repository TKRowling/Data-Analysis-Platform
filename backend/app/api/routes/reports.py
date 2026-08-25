from fastapi import APIRouter
from fastapi.responses import Response

from app.dependencies import ActiveDataset
from app.schemas.report import ReportRequest
from app.services import report_service

router = APIRouter(prefix="/datasets/{dataset_id}/reports", tags=["reports"])


@router.post("")
def generate(record: ActiveDataset, request: ReportRequest):
    content, mime, extension = report_service.render(record, request)
    body = content if isinstance(content, bytes) else content.encode("utf-8")
    return Response(body, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="analysis-report.{extension}"'})
