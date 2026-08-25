"""Assembles report sections once, so HTML, Markdown, and PDF never drift apart."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.services.eda_service import correlation, overview, quality, statistics

SECTION_ORDER = ["executive_summary", "overview", "quality", "statistics", "correlation", "distribution", "insights"]

SECTION_TITLES = {
    "executive_summary": "Executive summary",
    "overview": "Dataset overview",
    "quality": "Data quality",
    "statistics": "Statistical summary",
    "correlation": "Correlation analysis",
    "distribution": "Distributions",
    "insights": "AI analysis",
}


@dataclass
class Table:
    caption: str
    columns: list[str]
    rows: list[list]


@dataclass
class Section:
    key: str
    title: str
    body: str = ""
    tables: list[Table] = field(default_factory=list)
    matrix: dict | None = None


def number(value, digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def _executive_summary(record, ov, qu, co) -> str:
    body = (f"This report analyses {ov['rows']:,} records across {ov['columns_count']} variables from "
            f"{record.name}. The dataset scores {qu['score']}/100 for quality, with "
            f"{qu['duplicate_rows']:,} duplicate rows and {len(qu['missing'])} columns containing missing "
            f"values. By type the data is {ov['kinds']['numeric']} numeric and "
            f"{ov['kinds']['categorical']} categorical.")
    if co["strong"]:
        top = co["strong"][0]
        body += (f" The strongest relationship is between {top['left']} and {top['right']} "
                 f"(r = {top['value']}), which is an association and not evidence of causation.")
    return body


def _insight_body(insights: list[dict]) -> str:
    if not insights:
        return "No AI analysis was included in this report."
    blocks = []
    for entry in insights:
        answer = str(entry.get("answer", "")).strip()
        question = str(entry.get("question", "")).strip()
        blocks.append(f"Q: {question}\n{answer}" if question else answer)
    blocks.append("Every figure above was computed from this dataset by the analysis engine.")
    return "\n\n".join(b for b in blocks if b)


def build_sections(record, requested: list[str], insights: list[dict] | None = None) -> list[Section]:
    """Compute every requested section. All figures come from the EDA service."""
    wanted = [key for key in SECTION_ORDER if key in set(requested)]
    ov, qu, st, co = overview(record), quality(record), statistics(record), correlation(record)
    sections: list[Section] = []

    for key in wanted:
        title = SECTION_TITLES[key]

        if key == "executive_summary":
            sections.append(Section(key, title, _executive_summary(record, ov, qu, co)))

        elif key == "overview":
            body = (f"Rows: {ov['rows']:,}\nColumns: {ov['columns_count']}\n"
                    f"Memory: {ov['memory_bytes'] / 1024 / 1024:.2f} MB\n"
                    f"Column types: {ov['kinds']['numeric']} numeric, {ov['kinds']['categorical']} categorical, "
                    f"{ov['kinds']['datetime']} datetime, {ov['kinds']['boolean']} boolean")
            table = Table("Column profile", ["Column", "Type", "Non-null", "Missing", "Unique"],
                          [[c["name"], c["kind"], number(c["non_null"]), number(c["missing"]), number(c["unique"])]
                           for c in ov["columns"]])
            sections.append(Section(key, title, body, [table]))

        elif key == "quality":
            body = (f"Overall quality score: {qu['score']}/100\n"
                    f"Duplicate rows: {qu['duplicate_rows']:,} ({qu['duplicate_percent']}%)\n"
                    f"Columns with missing values: {len(qu['missing'])}\n"
                    f"Datatype issues detected: {len(qu['datatype_issues'])}\n\n"
                    "Outliers are detected with the IQR rule and are reported, not removed.")
            tables = []
            if qu["missing"]:
                tables.append(Table("Missing values", ["Column", "Missing", "Percent"],
                                    [[m["column"], number(m["count"]), f"{m['percent']}%"] for m in qu["missing"]]))
            flagged = [o for o in qu["outliers"] if o["count"]]
            if flagged:
                tables.append(Table("IQR outliers", ["Column", "Count", "Percent", "Lower bound", "Upper bound"],
                                    [[o["column"], number(o["count"]), f"{o['percent']}%",
                                      number(o["lower_bound"]), number(o["upper_bound"])] for o in flagged]))
            if qu["datatype_issues"]:
                tables.append(Table("Datatype consistency", ["Column", "Issue", "Detail"],
                                    [[d["column"], d["issue"].replace("_", " "), d["detail"]]
                                     for d in qu["datatype_issues"]]))
            sections.append(Section(key, title, body, tables))

        elif key == "statistics":
            tables = []
            if st["numeric"]:
                tables.append(Table("Numeric columns", ["Column", "Count", "Mean", "Median", "Std", "Min", "Max"],
                                    [[n["column"], number(n["count"]), number(n["mean"]), number(n["median"]),
                                      number(n["std"]), number(n["min"]), number(n["max"])] for n in st["numeric"]]))
            if st["categorical"]:
                rows = []
                for c in st["categorical"]:
                    top = c["top_values"][0] if c["top_values"] else None
                    frequent = f"{top['value']} ({top['count']})" if top else "—"
                    rows.append([c["column"], number(c["unique"]), number(c["missing"]), frequent])
                tables.append(Table("Categorical columns", ["Column", "Distinct", "Missing", "Most frequent"], rows))
            body = f"{len(st['numeric'])} numeric and {len(st['categorical'])} categorical columns were profiled."
            sections.append(Section(key, title, body, tables))

        elif key == "correlation":
            if co["strong"]:
                body = (f"{len(co['strong'])} column pairs exceed the |r| >= 0.7 threshold, using the "
                        f"{co['method']} method. Correlation measures association only.")
                tables = [Table("Strong correlations", ["Left", "Right", "r", "Direction"],
                                [[s["left"], s["right"], number(s["value"], 4), s["direction"]] for s in co["strong"]])]
            else:
                body = f"No column pairs met the |r| >= 0.7 threshold using the {co['method']} method."
                tables = []
            matrix = {"columns": co["columns"], "values": co["matrix"]} if co["columns"] else None
            sections.append(Section(key, title, body, tables, matrix=matrix))

        elif key == "distribution":
            rows = []
            for n in st["numeric"]:
                skew = n["skewness"]
                shape = ("symmetric" if skew is not None and abs(skew) < .5
                         else "right-skewed" if skew and skew > 0 else "left-skewed")
                rows.append([n["column"], number(n["mean"]), number(n["median"]), number(n["std"]),
                             number(skew, 3), shape])
            tables = [Table("Distribution shape", ["Column", "Mean", "Median", "Std", "Skew", "Shape"], rows)] if rows else []
            sections.append(Section(key, title, "Shape of each numeric column.", tables))

        elif key == "insights":
            sections.append(Section(key, title, _insight_body(insights or [])))

    return sections


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
