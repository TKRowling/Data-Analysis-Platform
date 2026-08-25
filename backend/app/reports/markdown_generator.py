"""Markdown rendering of assembled report sections."""
from __future__ import annotations

from app.reports.generator import Section, timestamp


def _escape(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(caption: str, columns: list[str], rows: list[list]) -> str:
    header = "| " + " | ".join(_escape(c) for c in columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = "\n".join("| " + " | ".join(_escape(cell) for cell in row) + " |" for row in rows)
    return f"**{caption}**\n\n{header}\n{divider}\n{body}" if rows else f"**{caption}**\n\n_No rows._"


def render(title: str, sections: list[Section]) -> str:
    parts = [f"# {title}", "", f"Generated {timestamp()}", ""]
    for section in sections:
        parts.append(f"## {section.title}")
        parts.append("")
        if section.body:
            parts.append(section.body)
            parts.append("")
        for table in section.tables:
            parts.append(_table(table.caption, table.columns, table.rows))
            parts.append("")
    return "\n".join(parts).rstrip() + "\n"
