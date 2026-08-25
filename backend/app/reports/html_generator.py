"""HTML rendering of assembled report sections. Self-contained: no external assets."""
from __future__ import annotations

from html import escape

from app.reports.generator import Section, timestamp

STYLE = """
:root{--ink:#17213a;--blue:#3157d5;--line:#dce2f0;--muted:#6f7890}
*{box-sizing:border-box}
body{font:16px/1.65 system-ui,-apple-system,'Segoe UI',sans-serif;max-width:940px;margin:48px auto;
padding:0 24px;color:var(--ink);background:#fff}
h1{color:var(--blue);font-size:34px;margin:0 0 6px}
.stamp{color:var(--muted);font-size:13px;margin:0 0 34px}
section{margin:28px 0;padding:26px;border:1px solid var(--line);border-radius:14px}
h2{margin:0 0 14px;font-size:20px}
.body{white-space:pre-wrap;margin-bottom:18px}
h3{font-size:13px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);margin:22px 0 10px}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th{text-align:left;background:#f6f8fc;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#5c6780}
th,td{padding:9px 12px;border-bottom:1px solid #eef1f7}
.matrix td{text-align:center;font-variant-numeric:tabular-nums}
.matrix th:first-child,.matrix td:first-child{text-align:left;font-weight:600;background:#f6f8fc}
footer{color:var(--muted);font-size:12px;margin-top:34px;text-align:center}
@media print{body{margin:0}section{break-inside:avoid;border-color:#ccc}}
"""


def _cell_color(value) -> str:
    if value is None:
        return "#ffffff"
    intensity = min(abs(float(value)), 1.0)
    alpha = 0.08 + 0.55 * intensity
    return f"rgba(49,87,213,{alpha:.2f})" if value >= 0 else f"rgba(232,93,117,{alpha:.2f})"


def _table_html(caption: str, columns: list[str], rows: list[list]) -> str:
    if not rows:
        return f"<h3>{escape(caption)}</h3><p>No rows.</p>"
    head = "".join(f"<th>{escape(str(c))}</th>" for c in columns)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>" for row in rows)
    return (f"<h3>{escape(caption)}</h3><div class='scroll'><table><thead><tr>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table></div>")


def _matrix_html(matrix: dict) -> str:
    columns, values = matrix["columns"], matrix["values"]
    if not columns:
        return ""
    head = "<th></th>" + "".join(f"<th>{escape(str(c))}</th>" for c in columns)
    rows = []
    for name, row in zip(columns, values):
        cells = "".join(
            f"<td style='background:{_cell_color(v)}'>{'—' if v is None else f'{v:.2f}'}</td>" for v in row)
        rows.append(f"<tr><td>{escape(str(name))}</td>{cells}</tr>")
    return ("<h3>Correlation matrix</h3><div class='scroll'><table class='matrix'>"
            f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


def render(title: str, sections: list[Section]) -> str:
    blocks = []
    for section in sections:
        inner = [f"<h2>{escape(section.title)}</h2>"]
        if section.body:
            inner.append(f"<div class='body'>{escape(section.body)}</div>")
        for table in section.tables:
            inner.append(_table_html(table.caption, table.columns, table.rows))
        if section.matrix:
            inner.append(_matrix_html(section.matrix))
        blocks.append(f"<section>{''.join(inner)}</section>")
    return (f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{escape(title)}</title><style>{STYLE}</style></head><body>"
            f"<h1>{escape(title)}</h1><p class='stamp'>Generated {timestamp()}</p>"
            f"{''.join(blocks)}"
            f"<footer>Produced by Datum. Every figure was computed from the source dataset.</footer>"
            f"</body></html>")
