"""Report generation use case. Sections are assembled once and rendered per format."""
from __future__ import annotations

from app.core.exceptions import AnalysisError
from app.reports import html_generator, markdown_generator, pdf_generator
from app.reports.generator import build_sections
from app.schemas.models import ReportRequest

RENDERERS = {
    "html": (html_generator.render, "text/html", "html"),
    "markdown": (markdown_generator.render, "text/markdown", "md"),
    "pdf": (pdf_generator.render, "application/pdf", "pdf"),
}


def generate(record, request: ReportRequest) -> tuple[str | bytes, str]:
    """Render the requested report. Returns (content, mime type)."""
    content, mime, _ = render(record, request)
    return content, mime


def render(record, request: ReportRequest) -> tuple[str | bytes, str, str]:
    """Render the requested report. Returns (content, mime type, file extension)."""
    if request.format not in RENDERERS:
        raise AnalysisError(f"Unsupported report format: {request.format}")
    if not request.sections:
        raise AnalysisError("Select at least one report section")
    sections = build_sections(record, request.sections, request.insights)
    if not sections:
        raise AnalysisError("None of the selected sections are recognised")
    renderer, mime, extension = RENDERERS[request.format]
    return renderer(request.title, sections), mime, extension
