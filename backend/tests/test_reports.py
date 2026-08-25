import pytest

from app.core.exceptions import AnalysisError
from app.reports.generator import build_sections
from app.schemas.models import ReportRequest
from app.services.report_service import render

ALL_SECTIONS = ["executive_summary", "overview", "quality", "statistics",
                "correlation", "distribution", "insights"]


def test_pdf_is_a_real_pdf(rich_record):
    content, mime, extension = render(rich_record, ReportRequest(sections=ALL_SECTIONS, format="pdf"))
    assert isinstance(content, bytes)
    assert content.startswith(b"%PDF")
    assert content.rstrip().endswith(b"%%EOF")
    assert len(content) > 2000
    assert (mime, extension) == ("application/pdf", "pdf")


def test_html_is_self_contained(rich_record):
    content, mime, _ = render(rich_record, ReportRequest(sections=ALL_SECTIONS, format="html"))
    assert content.startswith("<!doctype html")
    assert mime == "text/html"
    # A strict offline report must not pull in remote assets.
    assert "http://" not in content and "https://" not in content


def test_markdown_has_tables(rich_record):
    content, mime, extension = render(rich_record, ReportRequest(sections=ALL_SECTIONS, format="markdown"))
    assert content.startswith("# ")
    assert "| ---" in content
    assert (mime, extension) == ("text/markdown", "md")


def test_all_formats_report_the_same_figures(rich_record):
    request = ReportRequest(sections=["overview"], format="markdown")
    markdown, _, _ = render(rich_record, request)
    html, _, _ = render(rich_record, request.model_copy(update={"format": "html"}))
    rows = f"{len(rich_record.frame):,}"
    assert rows in markdown and rows in html


def test_sections_are_ordered_not_arbitrary(rich_record):
    sections = build_sections(rich_record, ["insights", "overview", "executive_summary"])
    assert [s.key for s in sections] == ["executive_summary", "overview", "insights"]


def test_insights_are_included(rich_record):
    content, _, _ = render(rich_record, ReportRequest(
        sections=["insights"], format="markdown",
        insights=[{"question": "Top region?", "answer": "North leads with 1,234."}]))
    assert "North leads with 1,234." in content
    assert "Top region?" in content


def test_empty_section_list_is_rejected(rich_record):
    with pytest.raises(AnalysisError):
        render(rich_record, ReportRequest(sections=[], format="html"))


def test_unknown_section_names_are_ignored(rich_record):
    with pytest.raises(AnalysisError):
        render(rich_record, ReportRequest(sections=["not_a_section"], format="html"))


def test_pdf_survives_a_wide_correlation_matrix(rich_record):
    """Wide matrices are summarised rather than rendered illegibly."""
    frame = rich_record.frame
    for index in range(15):
        frame[f"extra_{index}"] = frame["units"] * (index + 1)
    content, _, _ = render(rich_record, ReportRequest(sections=["correlation"], format="pdf"))
    assert content.startswith(b"%PDF")
