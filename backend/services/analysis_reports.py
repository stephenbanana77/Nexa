"""Insight Report generation with SQL evidence and analysis memory."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.project import AnalysisReport, Conversation, Dataset, Message
from services.semantic_layer import list_semantic_layer
from services.sql_policy import inspect_sql_policy
from tools import get_engine, load_dataset


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _is_numeric(dtype: str) -> bool:
    return any(token in dtype.lower() for token in ("int", "float", "double", "decimal", "number"))


def _schema(dataset: Dataset) -> list[dict]:
    return list(dataset.schema_info or [])


def _recent_memory(db: Session, project_id: str) -> dict:
    conversations = (
        db.query(Conversation)
        .filter(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.desc())
        .limit(3)
        .all()
    )
    conversation_ids = [c.id for c in conversations]
    messages: list[Message] = []
    if conversation_ids:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id.in_(conversation_ids))
            .order_by(Message.created_at.desc())
            .limit(10)
            .all()
        )
    reports = (
        db.query(AnalysisReport)
        .filter(AnalysisReport.project_id == project_id)
        .order_by(AnalysisReport.created_at.desc())
        .limit(3)
        .all()
    )
    return {
        "recent_questions": [
            {"role": m.role, "content": m.content[:240], "metadata": m.metadata_ or {}}
            for m in reversed(messages)
        ],
        "recent_reports": [
            {
                "id": r.id,
                "title": r.title,
                "highlights": (r.content or {}).get("highlights", [])[:5],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
    }


def analysis_memory_context(db: Session, project_id: str) -> str:
    memory = _recent_memory(db, project_id)
    lines: list[str] = []
    if memory["recent_questions"]:
        lines.append("RECENT ANALYSIS CONTEXT:")
        for item in memory["recent_questions"][-6:]:
            lines.append(f"- {item['role']}: {item['content']}")
    if memory["recent_reports"]:
        lines.append("RECENT REPORT FINDINGS:")
        for report in memory["recent_reports"]:
            highlights = "; ".join(report.get("highlights") or [])
            lines.append(f"- {report['title']}: {highlights}")
    return "\n".join(lines)


def _run_block(project_id: str, title: str, sql: str) -> dict[str, Any]:
    decision = inspect_sql_policy(sql)
    block = {
        "title": title,
        "sql": sql,
        "policy": decision.to_dict(),
        "columns": [],
        "rows": [],
        "row_count": 0,
        "finding": "",
        "error": None,
    }
    if not decision.is_safe:
        block["error"] = decision.reason
        return block
    try:
        result = get_engine(project_id).query(decision.final_sql or sql)
        block["columns"] = result.columns
        block["rows"] = result.rows[:10]
        block["row_count"] = result.row_count
        if result.rows:
            top = result.rows[0]
            block["finding"] = f"{title}: top result is " + ", ".join(str(v) for v in top[:3])
        else:
            block["finding"] = f"{title}: no rows returned."
    except Exception as exc:
        block["error"] = str(exc)
    return block


def generate_report(db: Session, project_id: str, dataset: Dataset, title: str | None = None) -> AnalysisReport:
    load_dataset(project_id, dataset.file_path, dataset.source_type)
    schema = _schema(dataset)
    numeric = [c for c in schema if _is_numeric(str(c.get("type", "")))]
    dimensions = [c for c in schema if not _is_numeric(str(c.get("type", "")))]
    semantic = list_semantic_layer(db, project_id, dataset.id)
    memory = _recent_memory(db, project_id)

    report_title = title or f"{dataset.name} Insight Report"
    blocks: list[dict[str, Any]] = []

    if numeric:
        metric = numeric[0]["name"]
        blocks.append(_run_block(
            project_id,
            f"Total {metric}",
            f"SELECT ROUND(SUM({_quote(metric)}), 2) AS total_{metric.replace(' ', '_').lower()} FROM data",
        ))
        blocks.append(_run_block(
            project_id,
            f"Average {metric}",
            f"SELECT ROUND(AVG({_quote(metric)}), 2) AS avg_{metric.replace(' ', '_').lower()} FROM data",
        ))

    if numeric and dimensions:
        metric = numeric[0]["name"]
        dim = dimensions[0]["name"]
        blocks.append(_run_block(
            project_id,
            f"Top {dim} by {metric}",
            (
                f"SELECT {_quote(dim)} AS dimension, ROUND(SUM({_quote(metric)}), 2) AS metric "
                f"FROM data GROUP BY {_quote(dim)} ORDER BY metric DESC LIMIT 10"
            ),
        ))

    if len(numeric) > 1 and dimensions:
        metric = numeric[1]["name"]
        dim = dimensions[0]["name"]
        blocks.append(_run_block(
            project_id,
            f"Top {dim} by {metric}",
            (
                f"SELECT {_quote(dim)} AS dimension, ROUND(SUM({_quote(metric)}), 2) AS metric "
                f"FROM data GROUP BY {_quote(dim)} ORDER BY metric DESC LIMIT 10"
            ),
        ))

    missing_exprs = [
        f"ROUND(SUM(CASE WHEN {_quote(c['name'])} IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS {c['name'].replace(' ', '_').lower()}_missing_pct"
        for c in schema[:8]
    ]
    if missing_exprs:
        blocks.append(_run_block(project_id, "Data quality snapshot", "SELECT " + ", ".join(missing_exprs) + " FROM data"))

    highlights = [b["finding"] for b in blocks if b.get("finding") and not b.get("error")]
    semantic_lines = [
        f"- Metric `{m['name']}` = `{m['expression']}`" for m in semantic["metrics"][:8]
    ] + [
        f"- Dimension `{d['name']}` -> `{d['column']}`" for d in semantic["dimensions"][:8]
    ]
    markdown = "\n".join([
        f"# {report_title}",
        "",
        f"Generated at: {datetime.utcnow().isoformat()}Z",
        f"Dataset: {dataset.name} ({dataset.row_count} rows, {dataset.column_count} columns)",
        "",
        "## Executive Highlights",
        *(f"- {item}" for item in highlights[:6]),
        "",
        "## Semantic Layer Used",
        *(semantic_lines or ["- No semantic definitions configured yet."]),
        "",
        "## Evidence Blocks",
        *(
            f"### {b['title']}\n\nSQL:\n```sql\n{b['sql']}\n```\n\nFinding: {b.get('finding') or b.get('error') or 'n/a'}\n"
            for b in blocks
        ),
    ])
    content = {
        "title": report_title,
        "dataset": {"id": dataset.id, "name": dataset.name, "rows": dataset.row_count, "columns": dataset.column_count},
        "highlights": highlights,
        "blocks": blocks,
        "markdown": markdown,
    }
    report = AnalysisReport(
        project_id=project_id,
        dataset_id=dataset.id,
        title=report_title,
        content=content,
        semantic_snapshot=semantic,
        memory=memory,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def serialize_report(report: AnalysisReport) -> dict:
    return {
        "id": report.id,
        "project_id": report.project_id,
        "dataset_id": report.dataset_id,
        "title": report.title,
        "content": report.content,
        "semantic_snapshot": report.semantic_snapshot,
        "memory": report.memory,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
