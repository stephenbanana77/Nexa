"""Insight Report generation with SQL evidence and analysis memory."""
from __future__ import annotations

from datetime import UTC, datetime
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


def _first_value(block: dict[str, Any]) -> Any:
    rows = block.get("rows") or []
    if not rows or not rows[0]:
        return None
    return rows[0][0]


def _named_metric(block: dict[str, Any]) -> str:
    value = _first_value(block)
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _block_by_title(blocks: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
    return next((b for b in blocks if b.get("title") == title and not b.get("error")), None)


def _value_from_row(block: dict[str, Any] | None, column: str) -> float | None:
    if not block or not block.get("rows"):
        return None
    columns = block.get("columns") or []
    if column not in columns:
        return None
    return _number(block["rows"][0][columns.index(column)])


def _pick_margin_columns(numeric: list[dict]) -> tuple[str, str] | None:
    """Return numerator and denominator columns for a margin-like metric."""
    if len(numeric) < 2:
        return None
    names = [str(c["name"]) for c in numeric]
    numerator = next((name for name in names if any(token in name.lower() for token in ("profit", "margin", "income"))), None)
    denominator = next((name for name in names if any(token in name.lower() for token in ("sales", "revenue", "amount"))), None)
    if numerator and denominator and numerator != denominator:
        return numerator, denominator
    return names[1], names[0]


def _build_sections(
    dataset: Dataset,
    blocks: list[dict[str, Any]],
    semantic: dict,
    numeric: list[dict],
    dimensions: list[dict],
) -> dict[str, Any]:
    successful = [b for b in blocks if not b.get("error")]
    errors = [b for b in blocks if b.get("error")]
    total_block = next((b for b in successful if b["title"].startswith("Total ")), None)
    avg_block = next((b for b in successful if b["title"].startswith("Average ")), None)
    breakdown_blocks = [b for b in successful if b["title"].startswith("Top ")]
    quality_block = next((b for b in successful if b["title"] == "Data quality snapshot"), None)
    concentration_block = _block_by_title(blocks, "Contribution concentration")
    margin_block = _block_by_title(blocks, "Overall margin")
    outlier_block = _block_by_title(blocks, "Numeric outlier scan")
    underperformer_block = next((b for b in successful if b["title"].startswith("Bottom ")), None)

    executive_summary = [
        f"Analyzed {dataset.row_count:,} rows across {dataset.column_count} columns from `{dataset.name}`.",
        f"Generated {len(successful)} SQL-backed evidence blocks under the current SQL safety policy.",
    ]
    if total_block:
        executive_summary.append(f"Primary total metric result: {_named_metric(total_block)}.")
    if breakdown_blocks and breakdown_blocks[0].get("rows"):
        row = breakdown_blocks[0]["rows"][0]
        executive_summary.append(f"Leading segment in `{breakdown_blocks[0]['title']}` is `{row[0]}` with value `{row[1]}`.")
    top_share = _value_from_row(concentration_block, "top_share_pct")
    if top_share is not None:
        executive_summary.append(f"The leading segment contributes {top_share:.2f}% of the primary metric, indicating {'high' if top_share >= 50 else 'moderate'} concentration.")
    margin = _value_from_row(margin_block, "margin")
    if margin is not None:
        executive_summary.append(f"Overall margin is {margin:.2%}, useful as a quality lens alongside volume metrics.")
    if errors:
        executive_summary.append(f"{len(errors)} evidence block(s) failed and should be reviewed before sharing.")

    key_metrics = []
    if total_block:
        key_metrics.append({
            "label": total_block["title"],
            "value": _named_metric(total_block),
            "evidence_title": total_block["title"],
        })
    if avg_block:
        key_metrics.append({
            "label": avg_block["title"],
            "value": _named_metric(avg_block),
            "evidence_title": avg_block["title"],
        })
    if margin_block:
        margin = _value_from_row(margin_block, "margin")
        key_metrics.append({
            "label": "Overall margin",
            "value": f"{margin:.2%}" if margin is not None else "n/a",
            "evidence_title": margin_block["title"],
        })

    segment_breakdown = [
        {
            "title": block["title"],
            "top_rows": block.get("rows", [])[:5],
            "columns": block.get("columns", []),
            "evidence_title": block["title"],
        }
        for block in breakdown_blocks
    ]

    quality_findings = []
    if quality_block and quality_block.get("rows"):
        row = quality_block["rows"][0]
        columns = quality_block.get("columns", [])
        quality_findings = [
            {"column": col.replace("_missing_pct", ""), "missing_pct": row[idx]}
            for idx, col in enumerate(columns)
        ]

    diagnostic_insights = []
    if concentration_block and concentration_block.get("rows"):
        row = concentration_block["rows"][0]
        diagnostic_insights.append({
            "type": "concentration",
            "title": "Metric concentration",
            "finding": f"Top segment `{row[0]}` contributes {row[2]}% of the selected metric.",
            "evidence_title": concentration_block["title"],
        })
    if underperformer_block and underperformer_block.get("rows"):
        row = underperformer_block["rows"][0]
        diagnostic_insights.append({
            "type": "underperformer",
            "title": "Lowest-performing segment",
            "finding": f"Lowest segment in `{underperformer_block['title']}` is `{row[0]}` with value `{row[1]}`.",
            "evidence_title": underperformer_block["title"],
        })
    if outlier_block and outlier_block.get("rows"):
        row = outlier_block["rows"][0]
        diagnostic_insights.append({
            "type": "outlier",
            "title": "Numeric outlier scan",
            "finding": f"{row[0]} has min `{row[1]}`, max `{row[2]}`, avg `{row[3]}`; investigate large spread before making decisions.",
            "evidence_title": outlier_block["title"],
        })

    semantic_summary = {
        "metric_count": len(semantic.get("metrics") or []),
        "dimension_count": len(semantic.get("dimensions") or []),
        "sample_metrics": semantic.get("metrics", [])[:5],
        "sample_dimensions": semantic.get("dimensions", [])[:5],
    }

    risks = []
    if not numeric:
        risks.append("No numeric columns were detected, so metric analysis is limited.")
    if not dimensions:
        risks.append("No categorical dimensions were detected, so segmentation analysis is limited.")
    if not semantic.get("metrics"):
        risks.append("No curated semantic metrics exist yet; report used schema-derived aggregates.")
    if errors:
        risks.append("Some evidence SQL blocks failed; inspect errors before using this report externally.")
    if top_share is not None and top_share >= 50:
        risks.append("Primary metric is concentrated in one segment, so aggregate performance may hide segment-level fragility.")
    if underperformer_block and underperformer_block.get("rows"):
        risks.append("At least one segment materially underperforms; validate whether this is expected seasonality, pricing, or data quality.")
    if not risks:
        risks.append("No critical data quality or evidence-generation risks were detected in the automated scan.")

    opportunities = []
    if breakdown_blocks:
        opportunities.append("Use the leading and trailing segments as follow-up analysis candidates.")
    if margin is not None:
        opportunities.append("Use margin as a secondary metric to avoid optimizing only for volume.")
    if semantic.get("metrics"):
        opportunities.append("Reuse curated semantic metrics for consistent future reports and chat analysis.")
    opportunities.append("Convert repeated follow-up questions into saved workflows once the analysis path stabilizes.")

    follow_up_questions = []
    if numeric and dimensions:
        follow_up_questions.extend([
            f"Why does the top {dimensions[0]['name']} lead on {numeric[0]['name']}?",
            f"Which {dimensions[0]['name']} segments are declining or underperforming?",
            f"What explains the gap between top and bottom {dimensions[0]['name']} segments?",
        ])
    if len(numeric) > 1:
        follow_up_questions.append(f"What is the relationship between {numeric[0]['name']} and {numeric[1]['name']}?")
    follow_up_questions.append("Which rows or segments should be investigated next?")

    return {
        "executive_summary": executive_summary,
        "key_metrics": key_metrics,
        "segment_breakdown": segment_breakdown,
        "data_quality": quality_findings,
        "diagnostic_insights": diagnostic_insights,
        "semantic_summary": semantic_summary,
        "risks": risks,
        "opportunities": opportunities,
        "recommended_follow_up_questions": follow_up_questions,
    }


def _build_investigation_cards(sections: dict[str, Any], blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    block_map = {block.get("title"): block for block in blocks}

    def hypotheses_for(insight: dict[str, Any], block: dict[str, Any]) -> list[dict[str, Any]]:
        insight_type = insight.get("type")
        evidence_title = insight.get("evidence_title")
        base = {
            "status": "needs_validation",
            "evidence_title": evidence_title,
            "supporting_evidence": block.get("finding") or insight.get("finding"),
        }
        if insight_type == "concentration":
            return [
                {
                    **base,
                    "hypothesis": "The leading segment may be structurally larger than the rest of the portfolio.",
                    "validation": "Compare the leading segment against the long-tail distribution and check whether the share is above an acceptable concentration threshold.",
                    "current_assessment": "Partially supported by the contribution concentration evidence; causal explanation still needs segment context.",
                    "next_question": "Break down the leading segment by the next available dimension and compare its margin.",
                },
                {
                    **base,
                    "hypothesis": "The concentration may be driven by one metric dimension rather than broad business strength.",
                    "validation": "Cross-check the leading segment on a second numeric metric, such as profit or margin, before treating it as healthy growth.",
                    "current_assessment": "Needs validation with a secondary metric.",
                    "next_question": "Does the leading segment also lead on profit or margin?",
                },
            ]
        if insight_type == "underperformer":
            return [
                {
                    **base,
                    "hypothesis": "The lowest-performing segment may have demand, pricing, or operational weakness.",
                    "validation": "Compare bottom and top segments across the primary metric and a secondary metric.",
                    "current_assessment": "Supported as a performance gap; root cause is not yet proven.",
                    "next_question": "Compare the lowest-performing segment with the top segment across all numeric metrics.",
                },
                {
                    **base,
                    "hypothesis": "The low result may be expected because the segment has fewer records or lower exposure.",
                    "validation": "Normalize by row count or order count to distinguish scale from performance quality.",
                    "current_assessment": "Needs normalization before action.",
                    "next_question": "Normalize the primary metric by row count for each segment.",
                },
            ]
        if insight_type == "outlier":
            return [
                {
                    **base,
                    "hypothesis": "Extreme records may be distorting aggregate metrics and averages.",
                    "validation": "Inspect top and bottom records for the numeric metric and compare median vs average.",
                    "current_assessment": "Supported by the spread scan; record-level drivers still need investigation.",
                    "next_question": "Show the top and bottom records driving the numeric outliers.",
                },
                {
                    **base,
                    "hypothesis": "The outlier spread may indicate data quality issues such as miscoded values or mixed units.",
                    "validation": "Check missing values, negative values, and unusually large values in the affected metric.",
                    "current_assessment": "Needs data-quality validation.",
                    "next_question": "Check whether the outlier metric has missing, negative, or unusually large values.",
                },
            ]
        return [
            {
                **base,
                "hypothesis": "This finding may point to a meaningful business pattern.",
                "validation": "Validate it with a follow-up segmentation and a second metric.",
                "current_assessment": "Needs validation.",
                "next_question": "Segment this finding further and compare it with another metric.",
            }
        ]

    for insight in sections.get("diagnostic_insights", []):
        evidence_title = insight["evidence_title"]
        block = block_map.get(evidence_title, {})
        next_question = {
            "concentration": "Why is the primary metric concentrated in the leading segment?",
            "underperformer": "What explains the lowest-performing segment and how does it compare with the top segment?",
            "outlier": "Which records or segments are driving the numeric outliers?",
        }.get(insight.get("type"), "What should we investigate next?")
        cards.append({
            "type": insight["type"],
            "severity": "high" if insight["type"] in {"concentration", "outlier"} else "medium",
            "finding": insight["finding"],
            "impact": {
                "concentration": "Aggregate results may hide dependency on one segment; validate whether growth is diversified.",
                "underperformer": "Low-performing groups are immediate candidates for pricing, operations, or data-quality review.",
                "outlier": "Large numeric spread can distort averages and should be checked before decisions are made.",
            }.get(insight["type"], "This finding is a candidate for deeper analysis."),
            "evidence_title": evidence_title,
            "evidence_preview": block.get("rows", [])[:3],
            "sql": block.get("sql"),
            "confidence": "high" if block and not block.get("error") else "low",
            "next_question": next_question,
            "hypotheses": hypotheses_for(insight, block),
        })

    if sections.get("risks"):
        cards.append({
            "type": "risk",
            "severity": "medium",
            "finding": sections["risks"][0],
            "impact": "This is the main caveat to mention before sharing the analysis externally.",
            "evidence_title": "Automated risk scan",
            "evidence_preview": [],
            "sql": None,
            "confidence": "medium",
            "next_question": "Which risks could materially change the conclusion?",
            "hypotheses": [
                {
                    "hypothesis": "The main risk could materially change the report conclusion.",
                    "validation": "Identify which evidence block or data-quality issue would change the decision if corrected.",
                    "status": "needs_validation",
                    "current_assessment": "Needs review before external sharing.",
                    "evidence_title": "Automated risk scan",
                    "supporting_evidence": sections["risks"][0],
                    "next_question": "Which evidence block is most sensitive to this risk?",
                }
            ],
        })

    if sections.get("opportunities"):
        cards.append({
            "type": "opportunity",
            "severity": "low",
            "finding": sections["opportunities"][0],
            "impact": "This turns the report from a static summary into a next-step analysis workflow.",
            "evidence_title": "Automated opportunity scan",
            "evidence_preview": [],
            "sql": None,
            "confidence": "medium",
            "next_question": "Turn this opportunity into a concrete next analysis step.",
            "hypotheses": [
                {
                    "hypothesis": "The opportunity can become a reusable analysis workflow.",
                    "validation": "Run the suggested follow-up and save the SQL-backed path if it remains useful.",
                    "status": "proposed",
                    "current_assessment": "Actionable as a next analysis step.",
                    "evidence_title": "Automated opportunity scan",
                    "supporting_evidence": sections["opportunities"][0],
                    "next_question": "Convert this opportunity into a repeatable analysis workflow.",
                }
            ],
        })

    return cards[:8]


def _build_decision_brief(
    dataset: Dataset,
    sections: dict[str, Any],
    investigation_cards: list[dict[str, Any]],
    numeric: list[dict],
    dimensions: list[dict],
) -> dict[str, Any]:
    primary_card = next(
        (card for card in investigation_cards if card.get("severity") in {"high", "medium"}),
        investigation_cards[0] if investigation_cards else None,
    )
    evidence_titles = [
        card["evidence_title"]
        for card in investigation_cards
        if card.get("evidence_title") and card.get("evidence_title") != "Automated opportunity scan"
    ][:5]
    recommended_actions = []
    if primary_card:
        recommended_actions.append(f"Validate the `{primary_card['type']}` finding before making a business decision.")
        recommended_actions.extend(
            hypothesis["next_question"]
            for hypothesis in primary_card.get("hypotheses", [])[:2]
        )
    recommended_actions.extend(sections.get("recommended_follow_up_questions", [])[:2])

    next_metrics = []
    if numeric:
        next_metrics.append(str(numeric[0]["name"]))
    if len(numeric) > 1:
        next_metrics.append(str(numeric[1]["name"]))
    if dimensions:
        next_metrics.append(f"{dimensions[0]['name']} mix")
    if not next_metrics:
        next_metrics.append("Data quality coverage")

    return {
        "audience": "Business owner / data lead",
        "situation": " ".join(sections.get("executive_summary", [])[:2])
        or f"`{dataset.name}` was analyzed for decision-ready signals.",
        "diagnosis": primary_card["finding"] if primary_card else "No material diagnostic signal was found in the automated scan.",
        "evidence": evidence_titles,
        "risk": (sections.get("risks") or ["No critical automated risk was detected."])[0],
        "recommendation": (
            primary_card["impact"]
            if primary_card
            else "Use this report as a baseline and continue with targeted follow-up questions."
        ),
        "recommended_actions": list(dict.fromkeys(recommended_actions))[:5],
        "next_metric_to_monitor": next_metrics[:4],
        "confidence": primary_card.get("confidence", "medium") if primary_card else "medium",
    }


def _build_analysis_graph(
    dataset: Dataset,
    semantic: dict,
    investigation_cards: list[dict[str, Any]],
    decision_brief: dict[str, Any],
) -> dict[str, Any]:
    nodes = [
        {
            "id": "dataset",
            "type": "dataset",
            "label": dataset.name,
            "detail": f"{dataset.row_count:,} rows / {dataset.column_count} columns",
        },
        {
            "id": "semantic_layer",
            "type": "semantic_layer",
            "label": "Semantic Layer",
            "detail": f"{len(semantic.get('metrics') or [])} metrics / {len(semantic.get('dimensions') or [])} dimensions",
        },
    ]
    edges = [
        {"source": "dataset", "target": "semantic_layer", "label": "grounds business definitions"},
    ]

    for card_idx, card in enumerate(investigation_cards[:6], start=1):
        finding_id = f"finding_{card_idx}"
        evidence_id = f"evidence_{card_idx}"
        nodes.append({
            "id": finding_id,
            "type": "finding",
            "label": card["type"],
            "detail": card["finding"],
            "severity": card.get("severity"),
            "confidence": card.get("confidence"),
        })
        nodes.append({
            "id": evidence_id,
            "type": "evidence",
            "label": card.get("evidence_title") or "Evidence",
            "detail": "SQL-backed evidence" if card.get("sql") else "Rule-based scan",
        })
        edges.extend([
            {"source": "semantic_layer", "target": finding_id, "label": "guides investigation"},
            {"source": finding_id, "target": evidence_id, "label": "validated by"},
        ])
        for hyp_idx, hypothesis in enumerate(card.get("hypotheses", [])[:2], start=1):
            hypothesis_id = f"hypothesis_{card_idx}_{hyp_idx}"
            nodes.append({
                "id": hypothesis_id,
                "type": "hypothesis",
                "label": f"H{card_idx}.{hyp_idx}",
                "detail": hypothesis["hypothesis"],
                "status": hypothesis.get("status"),
            })
            edges.extend([
                {"source": finding_id, "target": hypothesis_id, "label": "explains"},
                {"source": hypothesis_id, "target": evidence_id, "label": "needs evidence"},
            ])

    nodes.append({
        "id": "decision_brief",
        "type": "decision_brief",
        "label": "Decision Brief",
        "detail": decision_brief.get("recommendation") or "Executive-ready summary",
        "confidence": decision_brief.get("confidence"),
    })
    for card_idx, _card in enumerate(investigation_cards[:6], start=1):
        edges.append({"source": f"finding_{card_idx}", "target": "decision_brief", "label": "summarizes"})

    return {
        "nodes": nodes,
        "edges": edges,
        "entry_node": "dataset",
        "terminal_node": "decision_brief",
    }


def _render_markdown(
    report_title: str,
    dataset: Dataset,
    sections: dict[str, Any],
    blocks: list[dict[str, Any]],
    semantic_lines: list[str],
    investigation_cards: list[dict[str, Any]] | None = None,
    decision_brief: dict[str, Any] | None = None,
    analysis_graph: dict[str, Any] | None = None,
) -> str:
    generated_at = datetime.now(UTC).isoformat()
    lines = [
        f"# {report_title}",
        "",
        f"Generated at: {generated_at}",
        f"Dataset: {dataset.name} ({dataset.row_count:,} rows, {dataset.column_count} columns)",
        "",
        "## Executive Summary",
        *(f"- {item}" for item in sections["executive_summary"]),
        "",
        "## Key Metrics",
        *(f"- **{item['label']}**: {item['value']} (evidence: `{item['evidence_title']}`)" for item in sections["key_metrics"]),
        "",
        "## Decision Brief",
    ]
    if decision_brief:
        lines.extend([
            f"- **Audience**: {decision_brief['audience']}",
            f"- **Situation**: {decision_brief['situation']}",
            f"- **Diagnosis**: {decision_brief['diagnosis']}",
            f"- **Risk**: {decision_brief['risk']}",
            f"- **Recommendation**: {decision_brief['recommendation']}",
            f"- **Confidence**: {decision_brief['confidence']}",
            "- **Evidence**: " + ", ".join(f"`{item}`" for item in decision_brief.get("evidence", [])),
            "- **Next metrics to monitor**: " + ", ".join(decision_brief.get("next_metric_to_monitor", [])),
        ])
    else:
        lines.append("- No decision brief was generated.")

    lines.extend([
        "",
        "## Segment Breakdown",
    ]
    )
    if sections["segment_breakdown"]:
        for item in sections["segment_breakdown"]:
            lines.append(f"- **{item['title']}**: evidence block `{item['evidence_title']}`")
    else:
        lines.append("- No segment breakdown was generated.")

    lines.extend(["", "## Data Quality"])
    if sections["data_quality"]:
        lines.extend(f"- {item['column']}: {item['missing_pct']}% missing" for item in sections["data_quality"])
    else:
        lines.append("- No data quality snapshot was generated.")

    lines.extend(["", "## Diagnostic Insights"])
    if sections["diagnostic_insights"]:
        lines.extend(
            f"- **{item['title']}**: {item['finding']} (evidence: `{item['evidence_title']}`)"
            for item in sections["diagnostic_insights"]
        )
    else:
        lines.append("- No diagnostic insight was generated.")

    lines.extend(["", "## Hypothesis Engine"])
    if investigation_cards:
        for card in investigation_cards:
            lines.append(f"- **{card['type']}**: {card['finding']}")
            for hypothesis in card.get("hypotheses", [])[:3]:
                lines.append(f"  - Hypothesis: {hypothesis['hypothesis']}")
                lines.append(f"    - Current assessment: {hypothesis['current_assessment']}")
                lines.append(f"    - Validation: {hypothesis['validation']}")
    else:
        lines.append("- No hypotheses were generated.")

    lines.extend(["", "## Analysis Graph"])
    if analysis_graph:
        lines.append(f"- Nodes: {len(analysis_graph.get('nodes', []))}")
        lines.append(f"- Edges: {len(analysis_graph.get('edges', []))}")
        for edge in analysis_graph.get("edges", [])[:12]:
            lines.append(f"- `{edge['source']}` → `{edge['target']}`: {edge['label']}")
    else:
        lines.append("- No analysis graph was generated.")

    lines.extend([
        "",
        "## Risks",
        *(f"- {item}" for item in sections["risks"]),
        "",
        "## Opportunities",
        *(f"- {item}" for item in sections["opportunities"]),
        "",
        "## Recommended Follow-up Questions",
        *(f"- {item}" for item in sections["recommended_follow_up_questions"]),
        "",
        "## Semantic Layer Used",
        *(semantic_lines or ["- No semantic definitions configured yet."]),
        "",
        "## Evidence Blocks",
    ])
    for block in blocks:
        lines.extend([
            f"### {block['title']}",
            "",
            "SQL:",
            "```sql",
            block["sql"],
            "```",
            "",
            f"Finding: {block.get('finding') or block.get('error') or 'n/a'}",
            "",
        ])
    return "\n".join(lines)


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
        blocks.append(_run_block(
            project_id,
            f"Bottom {dim} by {metric}",
            (
                f"SELECT {_quote(dim)} AS dimension, ROUND(SUM({_quote(metric)}), 2) AS metric "
                f"FROM data GROUP BY {_quote(dim)} ORDER BY metric ASC LIMIT 10"
            ),
        ))
        blocks.append(_run_block(
            project_id,
            "Contribution concentration",
            (
                "WITH segment AS ("
                f"SELECT {_quote(dim)} AS dimension, SUM({_quote(metric)}) AS metric "
                f"FROM data GROUP BY {_quote(dim)}"
                ") "
                "SELECT dimension, ROUND(metric, 2) AS metric, "
                "ROUND(metric * 100.0 / NULLIF((SELECT SUM(metric) FROM segment), 0), 2) AS top_share_pct "
                "FROM segment ORDER BY metric DESC LIMIT 1"
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

    margin_columns = _pick_margin_columns(numeric)
    if margin_columns:
        numerator, denominator = margin_columns
        blocks.append(_run_block(
            project_id,
            "Overall margin",
            f"SELECT ROUND(SUM({_quote(numerator)}) / NULLIF(SUM({_quote(denominator)}), 0), 4) AS margin FROM data",
        ))

    if numeric:
        metric = numeric[0]["name"]
        metric_literal = metric.replace("'", "''")
        blocks.append(_run_block(
            project_id,
            "Numeric outlier scan",
            (
                f"SELECT '{metric_literal}' AS metric_name, "
                f"MIN({_quote(metric)}) AS min_value, "
                f"MAX({_quote(metric)}) AS max_value, "
                f"ROUND(AVG({_quote(metric)}), 2) AS avg_value, "
                f"ROUND(STDDEV_POP({_quote(metric)}), 2) AS stddev_value "
                "FROM data"
            ),
        ))

    missing_exprs = [
        f"ROUND(SUM(CASE WHEN {_quote(c['name'])} IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS {c['name'].replace(' ', '_').lower()}_missing_pct"
        for c in schema[:8]
    ]
    if missing_exprs:
        blocks.append(_run_block(project_id, "Data quality snapshot", "SELECT " + ", ".join(missing_exprs) + " FROM data"))

    sections = _build_sections(dataset, blocks, semantic, numeric, dimensions)
    highlights = sections["executive_summary"][:2] + [
        b["finding"] for b in blocks if b.get("finding") and not b.get("error")
    ][:4]
    semantic_lines = [
        f"- Metric `{m['name']}` = `{m['expression']}`" for m in semantic["metrics"][:8]
    ] + [
        f"- Dimension `{d['name']}` -> `{d['column']}`" for d in semantic["dimensions"][:8]
    ]
    investigation_cards = _build_investigation_cards(sections, blocks)
    decision_brief = _build_decision_brief(dataset, sections, investigation_cards, numeric, dimensions)
    analysis_graph = _build_analysis_graph(dataset, semantic, investigation_cards, decision_brief)
    markdown = _render_markdown(report_title, dataset, sections, blocks, semantic_lines, investigation_cards, decision_brief, analysis_graph)
    content = {
        "title": report_title,
        "dataset": {"id": dataset.id, "name": dataset.name, "rows": dataset.row_count, "columns": dataset.column_count},
        "highlights": highlights,
        "sections": sections,
        "investigation_cards": investigation_cards,
        "decision_brief": decision_brief,
        "analysis_graph": analysis_graph,
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
