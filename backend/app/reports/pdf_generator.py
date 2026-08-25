"""PDF rendering with ReportLab.

Pure Python, so `pip install` works on Windows without GTK/Pango. The correlation matrix is
drawn as a shaded ReportLab table rather than an exported image, which keeps the dependency
list free of a headless browser or Kaleido.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.reports.generator import Section, timestamp

INK = colors.HexColor("#17213a")
BLUE = colors.HexColor("#3157d5")
MUTED = colors.HexColor("#6f7890")
LINE = colors.HexColor("#dce2f0")
HEADER_BG = colors.HexColor("#f6f8fc")

MAX_TABLE_ROWS = 60
PAGE_WIDTH = A4[0] - 36 * mm


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("DatumTitle", parent=base["Title"], textColor=BLUE, fontSize=26,
                                leading=31, alignment=TA_LEFT, spaceAfter=4),
        "stamp": ParagraphStyle("DatumStamp", parent=base["Normal"], textColor=MUTED, fontSize=9, spaceAfter=18),
        "heading": ParagraphStyle("DatumHeading", parent=base["Heading2"], textColor=INK, fontSize=15,
                                  leading=19, spaceBefore=16, spaceAfter=8),
        "caption": ParagraphStyle("DatumCaption", parent=base["Normal"], textColor=MUTED, fontSize=8,
                                  leading=11, spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("DatumBody", parent=base["Normal"], textColor=INK, fontSize=10,
                               leading=15, spaceAfter=6),
        "cell": ParagraphStyle("DatumCell", parent=base["Normal"], fontSize=7.5, leading=10, textColor=INK),
        "cellhead": ParagraphStyle("DatumCellHead", parent=base["Normal"], fontSize=7, leading=9,
                                   textColor=colors.HexColor("#5c6780")),
    }


def _escape(value) -> str:
    return (str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _data_table(caption: str, columns: list[str], rows: list[list], styles) -> list:
    if not rows:
        return [Paragraph(_escape(caption).upper(), styles["caption"]), Paragraph("No rows.", styles["body"])]
    shown = rows[:MAX_TABLE_ROWS]
    header = [Paragraph(_escape(c).upper(), styles["cellhead"]) for c in columns]
    body = [[Paragraph(_escape(cell), styles["cell"]) for cell in row] for row in shown]
    table = Table([header] + body, repeatRows=1, hAlign="LEFT",
                  colWidths=[PAGE_WIDTH / len(columns)] * len(columns))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    flowables = [Paragraph(_escape(caption).upper(), styles["caption"]), table]
    if len(rows) > MAX_TABLE_ROWS:
        flowables.append(Paragraph(f"Showing {MAX_TABLE_ROWS} of {len(rows)} rows.", styles["caption"]))
    return flowables


def _matrix_table(matrix: dict, styles) -> list:
    columns, values = matrix["columns"], matrix["values"]
    if not columns:
        return []
    # Wide matrices become unreadable at A4 width; the strong-pairs table already covers them.
    if len(columns) > 12:
        return [Paragraph(f"Correlation matrix omitted: {len(columns)} numeric columns is too wide "
                          f"to render legibly. See the strong correlations table above.", styles["caption"])]
    header = [Paragraph("", styles["cellhead"])] + [Paragraph(_escape(c), styles["cellhead"]) for c in columns]
    body, shading = [], []
    for row_index, (name, row) in enumerate(zip(columns, values), start=1):
        cells = [Paragraph(f"<b>{_escape(name)}</b>", styles["cell"])]
        for col_index, value in enumerate(row, start=1):
            cells.append(Paragraph("—" if value is None else f"{value:.2f}", styles["cell"]))
            if value is not None:
                intensity = min(abs(float(value)), 1.0) * 0.6
                tint = colors.Color(1 - intensity * 0.75, 1 - intensity * 0.55, 1) if value >= 0 \
                    else colors.Color(1, 1 - intensity * 0.65, 1 - intensity * 0.55)
                shading.append(("BACKGROUND", (col_index, row_index), (col_index, row_index), tint))
        body.append(cells)
    width = PAGE_WIDTH / (len(columns) + 1)
    table = Table([header] + body, repeatRows=1, hAlign="LEFT", colWidths=[width] * (len(columns) + 1))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("BACKGROUND", (0, 1), (0, -1), HEADER_BG),
        ("GRID", (0, 0), (-1, -1), 0.3, LINE),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ] + shading))
    return [Paragraph("CORRELATION MATRIX", styles["caption"]), table]


def _footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 12 * mm, "Produced by Data Analytics Platform — every figure computed from the source dataset.")
    canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Page {document.page}")
    canvas.restoreState()


def render(title: str, sections: list[Section]) -> bytes:
    styles = _styles()
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, title=title, author="Data Analytics Platform",
                                 leftMargin=18 * mm, rightMargin=18 * mm,
                                 topMargin=18 * mm, bottomMargin=20 * mm)
    story: list = [Paragraph(_escape(title), styles["title"]),
                   Paragraph(f"Generated {timestamp()}", styles["stamp"])]

    for index, section in enumerate(sections):
        block: list = [Paragraph(_escape(section.title), styles["heading"])]
        if section.body:
            for paragraph in section.body.split("\n"):
                block.append(Paragraph(_escape(paragraph) if paragraph.strip() else "&nbsp;", styles["body"]))
        story.extend(block)
        for table in section.tables:
            story.extend(_data_table(table.caption, table.columns, table.rows, styles))
        if section.matrix:
            story.extend(_matrix_table(section.matrix, styles))
        if index < len(sections) - 1:
            story.append(Spacer(1, 10))

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
