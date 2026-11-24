"""生成带 SQL 证据和分析记忆的中文洞察报告。"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
import math
import re

from sqlalchemy.orm import Session

from models.project import AnalysisReport, Conversation, Dataset, Message
from services.semantic_layer import list_semantic_layer
from services.sql_policy import inspect_sql_policy
from tools import get_engine, load_dataset


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _is_numeric(dtype: str) -> bool:
    return any(token in dtype.lower() for token in ("int", "float", "double", "decimal", "number"))


def _is_technical_field(name: str) -> bool:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
    tokens = set(normalized.split("_"))
    return bool(tokens.intersection({"id", "code", "key", "index", "row", "zip", "postal"}))


def _is_temporal_field(name: str) -> bool:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
    tokens = set(normalized.split("_"))
    return bool(tokens.intersection({"date", "time", "timestamp", "month", "quarter", "year"}))


def _is_additive_business_field(name: str) -> bool:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
    tokens = set(normalized.split("_"))
    additive = {
        "sales", "revenue", "amount", "profit", "income", "cost", "expense",
        "quantity", "qty", "units", "count", "cnt", "orders", "volume",
    }
    return any(token in tokens or token in normalized for token in additive)


def _business_numeric_columns(schema: list[dict]) -> list[dict]:
    numeric = [c for c in schema if _is_numeric(str(c.get("type", "")))]
    usable = [
        c for c in numeric
        if not _is_technical_field(str(c.get("name", "")))
        and _is_additive_business_field(str(c.get("name", "")))
    ]
    # Prefer common business measures when several candidates remain.
    priority = ("sales", "revenue", "amount", "profit", "income", "quantity", "count")
    return sorted(usable, key=lambda c: next(
        (i for i, token in enumerate(priority) if token in str(c.get("name", "")).lower()),
        len(priority),
    ))


def _business_dimensions(schema: list[dict]) -> list[dict]:
    dimensions = [c for c in schema if not _is_numeric(str(c.get("type", "")))]
    priority = ("region", "segment", "category", "sub-category", "sub_category", "ship mode", "country", "state", "city")

    def sort_key(column: dict) -> tuple[int, int, int, str]:
        name = str(column.get("name", ""))
        lowered = name.lower()
        priority_rank = next((i for i, token in enumerate(priority) if token in lowered), len(priority))
        return (
            1 if _is_temporal_field(name) else 0,
            1 if _is_technical_field(name) else 0,
            priority_rank,
            lowered,
        )

    return sorted(dimensions, key=sort_key)


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
        lines.append("近期分析上下文：")
        for item in memory["recent_questions"][-6:]:
            lines.append(f"- {item['role']}: {item['content']}")
    if memory["recent_reports"]:
        lines.append("近期报告发现：")
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
            block["finding"] = f"{title}：首条结果为 " + "，".join(str(v) for v in top[:3])
        else:
            block["finding"] = f"{title}：未返回数据。"
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
        return "暂无"
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
    return None


def _metric_priority(metric: dict[str, Any]) -> tuple[int, str]:
    text = f"{metric.get('name', '')} {metric.get('expression', '')}".lower()
    priority = ("sales", "revenue", "销售额", "amount", "profit", "income", "quantity", "qty", "units", "count")
    return next((index for index, token in enumerate(priority) if token in text), len(priority)), text


def _aggregate_inner(expression: str) -> str | None:
    match = re.fullmatch(r"\s*SUM\s*\((.+)\)\s*", expression, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def _json_safe(value: Any) -> Any:
    """Recursively convert query values to JSON-safe native types."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except (TypeError, ValueError):
            pass
    return str(value)


def _build_metric_contracts(dataset: Dataset, semantic: dict, schema: list[dict]) -> dict[str, Any]:
    schema_by_name = {str(col.get("name")): col for col in schema}
    missing_by_column = {
        str(col.get("name")): _number(col.get("missing_pct")) or 0.0
        for col in schema
    }
    contracts = []

    for metric in semantic.get("metrics", []):
        expression = str(metric.get("expression") or "")
        referenced_columns = re.findall(r'"([^"]+)"', expression)
        missing_columns = [name for name in referenced_columns if name not in schema_by_name]
        policy = inspect_sql_policy(f"SELECT {expression} AS metric_value FROM data")
        max_missing_pct = max((missing_by_column.get(name, 0.0) for name in referenced_columns), default=0.0)
        issues = []
        if metric.get("status") != "approved":
            issues.append("指标尚未审批通过。")
        if missing_columns:
            issues.append(f"缺少引用字段：{', '.join(missing_columns)}")
        if not policy.is_safe:
            issues.append(f"指标表达式未通过 SQL 安全策略：{policy.reason}")
        if not referenced_columns:
            issues.append("指标表达式未引用任何数据集字段，血缘信息不足。")
        if max_missing_pct > 10:
            issues.append(f"引用字段的最高缺失率为 {max_missing_pct:.2f}%。")
        contracts.append({
            "type": "metric",
            "name": metric.get("name"),
            "definition": expression,
            "referenced_columns": referenced_columns,
            "status": "pass" if not issues else "warn",
            "issues": issues,
            "evidence": {
                "dataset": dataset.name,
                "row_count": dataset.row_count,
                "max_missing_pct": max_missing_pct,
                "sql_policy": policy.to_dict(),
            },
        })

    for dimension in semantic.get("dimensions", []):
        column = str(dimension.get("column") or "")
        issues = []
        if column not in schema_by_name:
            issues.append(f"数据集中缺少维度字段 `{column}`。")
        missing_pct = missing_by_column.get(column, 0.0)
        if missing_pct > 10:
            issues.append(f"维度字段缺失率为 {missing_pct:.2f}%。")
        contracts.append({
            "type": "dimension",
            "name": dimension.get("name"),
            "definition": column,
            "referenced_columns": [column] if column else [],
            "status": "pass" if not issues else "warn",
            "issues": issues,
            "evidence": {
                "dataset": dataset.name,
                "row_count": dataset.row_count,
                "max_missing_pct": missing_pct,
                "sql_policy": {"is_safe": True, "reason": "维度字段映射"},
            },
        })

    failed = [contract for contract in contracts if contract["status"] != "pass"]
    return {
        "status": "pass" if not failed else "warn",
        "summary": (
            f"{len(contracts) - len(failed)}/{len(contracts)} 个语义契约检查通过。"
            if contracts
            else "该数据集尚未配置语义契约。"
        ),
        "contracts": contracts,
        "release_gate": {
            "can_answer": not any("缺少引用字段" in issue for contract in contracts for issue in contract["issues"]),
            "requires_review": bool(failed),
            "reason": "所有指标和维度契约均已通过。" if not failed else "部分指标或维度契约需要复核。",
        },
    }


def _build_sections(
    dataset: Dataset,
    blocks: list[dict[str, Any]],
    semantic: dict,
    numeric: list[dict],
    dimensions: list[dict],
) -> dict[str, Any]:
    successful = [b for b in blocks if not b.get("error")]
    errors = [b for b in blocks if b.get("error")]
    total_block = next((b for b in successful if b["title"].startswith("总计：")), None)
    avg_block = next((b for b in successful if b["title"].startswith("平均值：")), None)
    breakdown_blocks = [b for b in successful if b["title"].startswith("排名靠前：")]
    quality_block = next((b for b in successful if b["title"] == "数据质量快照"), None)
    concentration_block = _block_by_title(blocks, "贡献集中度")
    margin_block = _block_by_title(blocks, "整体利润率")
    outlier_block = _block_by_title(blocks, "数值异常扫描")
    underperformer_block = next((b for b in successful if b["title"].startswith("排名靠后：")), None)

    executive_summary = [
        f"已分析 `{dataset.name}` 的 {dataset.row_count:,} 行、{dataset.column_count} 个字段。",
        f"在当前 SQL 安全策略下生成了 {len(successful)} 个有 SQL 支撑的证据块。",
    ]
    if total_block:
        executive_summary.append(f"主要汇总指标结果为 {_named_metric(total_block)}。")
    if breakdown_blocks and breakdown_blocks[0].get("rows"):
        row = breakdown_blocks[0]["rows"][0]
        executive_summary.append(f"`{breakdown_blocks[0]['title']}` 中表现最好的分组是 `{row[0]}`，指标值为 `{row[1]}`。")
    top_share = _value_from_row(concentration_block, "top_share_pct")
    if top_share is not None:
        level = "较高" if top_share >= 50 else "中等"
        executive_summary.append(f"领先分组贡献了主要指标的 {top_share:.2f}%，集中度{level}。")
    margin = _value_from_row(margin_block, "margin")
    if margin is not None:
        executive_summary.append(f"整体利润率为 {margin:.2%}，可与规模指标结合判断业务质量。")
    if errors:
        executive_summary.append(f"有 {len(errors)} 个证据块执行失败，对外分享前需要复核。")

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
            "label": "整体利润率",
            "value": f"{margin:.2%}" if margin is not None else "暂无",
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
            "title": "指标集中度",
            "finding": f"领先分组 `{row[0]}` 贡献了所选指标的 {row[2]}%。",
            "evidence_title": concentration_block["title"],
        })
    if underperformer_block and underperformer_block.get("rows"):
        row = underperformer_block["rows"][0]
        diagnostic_insights.append({
            "type": "underperformer",
            "title": "低表现分组",
            "finding": f"`{underperformer_block['title']}` 中表现最低的分组是 `{row[0]}`，指标值为 `{row[1]}`。",
            "evidence_title": underperformer_block["title"],
        })
    if outlier_block and outlier_block.get("rows"):
        row = outlier_block["rows"][0]
        diagnostic_insights.append({
            "type": "outlier",
            "title": "数值异常扫描",
            "finding": f"{row[0]} 的最小值为 `{row[1]}`、最大值为 `{row[2]}`、平均值为 `{row[3]}`；决策前应先调查数值跨度过大的原因。",
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
        risks.append("未检测到可用的数值字段，指标分析能力受限。")
    if not dimensions:
        risks.append("未检测到可用的分类维度，细分分析能力受限。")
    if not semantic.get("metrics"):
        risks.append("尚无经过治理的语义指标，本报告使用了从数据结构推导的聚合结果。")
    if errors:
        risks.append("部分证据 SQL 执行失败，对外使用报告前请先检查错误。")
    if top_share is not None and top_share >= 50:
        risks.append("主要指标集中在单一分组，汇总结果可能掩盖分组层面的脆弱性。")
    if underperformer_block and underperformer_block.get("rows"):
        risks.append("至少有一个分组表现明显偏低，需要确认是季节性、定价问题还是数据质量问题。")
    if not risks:
        risks.append("自动扫描未发现严重的数据质量或证据生成风险。")

    opportunities = []
    if breakdown_blocks:
        opportunities.append("可将领先和落后分组作为后续重点分析对象。")
    if margin is not None:
        opportunities.append("可将利润率作为辅助指标，避免只优化业务规模。")
    if semantic.get("metrics"):
        opportunities.append("后续报告和对话分析可复用已治理的语义指标，保持口径一致。")
    opportunities.append("分析路径稳定后，可将反复出现的追问沉淀为自动化流程。")

    follow_up_questions = []
    if numeric and dimensions:
        follow_up_questions.extend([
            f"为什么排名第一的 {dimensions[0]['name']} 在 {numeric[0]['name']} 上领先？",
            f"哪些 {dimensions[0]['name']} 分组正在下降或表现不佳？",
            f"排名最高和最低的 {dimensions[0]['name']} 分组之间，差距由什么造成？",
        ])
    if len(numeric) > 1:
        follow_up_questions.append(f"{numeric[0]['name']} 和 {numeric[1]['name']} 之间有什么关系？")
    follow_up_questions.append("下一步应该重点调查哪些记录或分组？")

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
                    "hypothesis": "领先分组的业务规模可能在结构上明显大于其他分组。",
                    "validation": "将领先分组与长尾分布进行比较，并检查其占比是否超过可接受的集中度阈值。",
                    "current_assessment": "贡献集中度证据提供了部分支持，但因果解释仍需结合分组背景。",
                    "next_question": "按下一个可用维度拆分领先分组，并用另一个已审批指标交叉验证。",
                },
                {
                    **base,
                    "hypothesis": "集中度可能由单一指标维度驱动，并不代表业务整体强劲。",
                    "validation": "在将其视为健康增长前，使用数据集中已定义且审批的第二个数值指标交叉验证。",
                    "current_assessment": "需要使用辅助指标验证。",
                    "next_question": "领先分组在另一个已审批指标上是否同样领先？",
                },
            ]
        if insight_type == "underperformer":
            return [
                {
                    **base,
                    "hypothesis": "表现最低的分组可能存在需求、定价或运营方面的问题。",
                    "validation": "使用主要指标和一个辅助指标，对比排名最低和最高的分组。",
                    "current_assessment": "已确认存在表现差距，但根因尚未得到证明。",
                    "next_question": "在所有数值指标上比较表现最低和最高的分组。",
                },
                {
                    **base,
                    "hypothesis": "该分组记录数或曝光量较少，因此低结果可能符合预期。",
                    "validation": "按记录数或订单数进行标准化，以区分规模差异和表现质量。",
                    "current_assessment": "采取行动前需要先做标准化。",
                    "next_question": "按每个分组的记录数对主要指标进行标准化。",
                },
            ]
        if insight_type == "outlier":
            return [
                {
                    **base,
                    "hypothesis": "极端记录可能扭曲了汇总指标和平均值。",
                    "validation": "检查该数值指标排名最高和最低的记录，并比较中位数与平均值。",
                    "current_assessment": "数值跨度扫描提供了支持，但仍需调查记录层面的驱动因素。",
                    "next_question": "展示造成数值异常的最高和最低记录。",
                },
                {
                    **base,
                    "hypothesis": "异常跨度可能意味着编码错误、单位混用等数据质量问题。",
                    "validation": "检查相关指标中的缺失值、负值和异常大值。",
                    "current_assessment": "需要进行数据质量验证。",
                    "next_question": "检查异常指标中是否存在缺失值、负值或异常大值。",
                },
            ]
        return [
            {
                **base,
                "hypothesis": "这一发现可能反映了有意义的业务规律。",
                "validation": "通过进一步细分和第二个指标进行验证。",
                "current_assessment": "需要验证。",
                "next_question": "进一步细分这一发现，并与另一个指标进行比较。",
            }
        ]

    for insight in sections.get("diagnostic_insights", []):
        evidence_title = insight["evidence_title"]
        block = block_map.get(evidence_title, {})
        next_question = {
            "concentration": "为什么主要指标集中在领先分组？",
            "underperformer": "表现最低的分组由什么造成，与领先分组相比有何差异？",
            "outlier": "哪些记录或分组造成了数值异常？",
        }.get(insight.get("type"), "下一步应该调查什么？")
        cards.append({
            "type": insight["type"],
            "severity": "high" if insight["type"] in {"concentration", "outlier"} else "medium",
            "finding": insight["finding"],
            "impact": {
                "concentration": "汇总结果可能掩盖对单一分组的依赖，需要确认增长是否足够多元。",
                "underperformer": "低表现分组应优先接受定价、运营或数据质量复核。",
                "outlier": "过大的数值跨度可能扭曲平均值，决策前需要检查。",
            }.get(insight["type"], "这一发现值得进一步分析。"),
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
            "impact": "这是对外分享分析结果前需要明确说明的主要限制。",
            "evidence_title": "自动风险扫描",
            "evidence_preview": [],
            "sql": None,
            "confidence": "medium",
            "next_question": "哪些风险可能实质性改变当前结论？",
            "hypotheses": [
                {
                    "hypothesis": "主要风险可能实质性改变报告结论。",
                    "validation": "识别哪些证据块或数据质量问题在修正后会改变决策。",
                    "status": "needs_validation",
                    "current_assessment": "对外分享前需要复核。",
                    "evidence_title": "自动风险扫描",
                    "supporting_evidence": sections["risks"][0],
                    "next_question": "哪个证据块对这一风险最敏感？",
                }
            ],
        })

    if sections.get("opportunities"):
        cards.append({
            "type": "opportunity",
            "severity": "low",
            "finding": sections["opportunities"][0],
            "impact": "这可以把静态报告转化为可继续执行的分析流程。",
            "evidence_title": "自动机会扫描",
            "evidence_preview": [],
            "sql": None,
            "confidence": "medium",
            "next_question": "把这个机会转化为具体的下一步分析。",
            "hypotheses": [
                {
                    "hypothesis": "这个机会可以沉淀为可复用的分析流程。",
                    "validation": "执行建议的后续分析，如果持续有价值，就保存这条由 SQL 支撑的路径。",
                    "status": "proposed",
                    "current_assessment": "可作为下一步分析直接执行。",
                    "evidence_title": "自动机会扫描",
                    "supporting_evidence": sections["opportunities"][0],
                    "next_question": "将这个机会转化为可重复执行的分析流程。",
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
        if card.get("evidence_title") and card.get("evidence_title") != "自动机会扫描"
    ][:5]
    recommended_actions = []
    if primary_card:
        type_label = {
            "risk": "风险",
            "opportunity": "机会",
            "concentration": "集中度",
            "underperformer": "低表现分组",
            "outlier": "异常值",
        }.get(primary_card["type"], primary_card["type"])
        recommended_actions.append(f"在做出业务决策前，先验证“{type_label}”这一发现。")
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
        next_metrics.append(f"{dimensions[0]['name']} 分布")
    if not next_metrics:
        next_metrics.append("数据质量覆盖率")

    return {
        "audience": "业务负责人 / 数据负责人",
        "situation": " ".join(sections.get("executive_summary", [])[:2])
        or f"已分析 `{dataset.name}` 中可支持决策的信号。",
        "diagnosis": primary_card["finding"] if primary_card else "自动扫描未发现需要重点关注的诊断信号。",
        "evidence": evidence_titles,
        "risk": (sections.get("risks") or ["自动扫描未发现严重风险。"])[0],
        "recommendation": (
            primary_card["impact"]
            if primary_card
            else "将本报告作为分析基线，并通过有针对性的追问继续深入。"
        ),
        "recommended_actions": list(dict.fromkeys(recommended_actions))[:5],
        "next_metric_to_monitor": next_metrics[:4],
        "confidence": primary_card.get("confidence", "medium") if primary_card else "medium",
    }


def _build_analysis_graph(
    dataset: Dataset,
    semantic: dict,
    metric_contracts: dict[str, Any],
    investigation_cards: list[dict[str, Any]],
    decision_brief: dict[str, Any],
) -> dict[str, Any]:
    nodes = [
        {
            "id": "dataset",
            "type": "dataset",
            "label": dataset.name,
            "detail": f"{dataset.row_count:,} 行 / {dataset.column_count} 个字段",
        },
        {
            "id": "semantic_layer",
            "type": "semantic_layer",
            "label": "语义层",
            "detail": f"{len(semantic.get('metrics') or [])} 个指标 / {len(semantic.get('dimensions') or [])} 个维度",
        },
        {
            "id": "metric_contracts",
            "type": "metric_contracts",
            "label": "指标契约检查",
            "detail": metric_contracts.get("summary") or "语义契约审计",
            "status": metric_contracts.get("status"),
        },
    ]
    edges = [
        {"source": "dataset", "target": "semantic_layer", "label": "支撑业务定义"},
        {"source": "semantic_layer", "target": "metric_contracts", "label": "审计指标契约"},
    ]

    for card_idx, card in enumerate(investigation_cards[:6], start=1):
        finding_id = f"finding_{card_idx}"
        evidence_id = f"evidence_{card_idx}"
        nodes.append({
            "id": finding_id,
            "type": "finding",
            "label": {
                "risk": "风险",
                "opportunity": "机会",
                "concentration": "集中度",
                "underperformer": "低表现分组",
                "outlier": "异常值",
            }.get(card["type"], card["type"]),
            "detail": card["finding"],
            "severity": card.get("severity"),
            "confidence": card.get("confidence"),
        })
        nodes.append({
            "id": evidence_id,
            "type": "evidence",
            "label": card.get("evidence_title") or "证据",
            "detail": "SQL 支撑的证据" if card.get("sql") else "规则扫描",
        })
        edges.extend([
            {"source": "metric_contracts", "target": finding_id, "label": "控制调查准入"},
            {"source": finding_id, "target": evidence_id, "label": "由此验证"},
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
                {"source": finding_id, "target": hypothesis_id, "label": "尝试解释"},
                {"source": hypothesis_id, "target": evidence_id, "label": "需要证据"},
            ])

    nodes.append({
        "id": "decision_brief",
        "type": "decision_brief",
        "label": "决策摘要",
        "detail": decision_brief.get("recommendation") or "面向管理者的摘要",
        "confidence": decision_brief.get("confidence"),
    })
    for card_idx, _card in enumerate(investigation_cards[:6], start=1):
        edges.append({"source": f"finding_{card_idx}", "target": "decision_brief", "label": "汇总为"})

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
    metric_contracts: dict[str, Any] | None = None,
) -> str:
    generated_at = datetime.now(UTC).isoformat()
    lines = [
        f"# {report_title}",
        "",
        f"生成时间：{generated_at}",
        f"数据集：{dataset.name}（{dataset.row_count:,} 行，{dataset.column_count} 个字段）",
        "",
        "## 执行摘要",
        *(f"- {item}" for item in sections["executive_summary"]),
        "",
        "## 关键指标",
        *(f"- **{item['label']}**：{item['value']}（证据：`{item['evidence_title']}`）" for item in sections["key_metrics"]),
        "",
        "## 决策摘要",
    ]
    if decision_brief:
        lines.extend([
            f"- **面向对象**：{decision_brief['audience']}",
            f"- **现状**：{decision_brief['situation']}",
            f"- **诊断**：{decision_brief['diagnosis']}",
            f"- **风险**：{decision_brief['risk']}",
            f"- **建议**：{decision_brief['recommendation']}",
            f"- **置信度**：{decision_brief['confidence']}",
            "- **证据**：" + "，".join(f"`{item}`" for item in decision_brief.get("evidence", [])),
            "- **下一步关注指标**：" + "，".join(decision_brief.get("next_metric_to_monitor", [])),
        ])
    else:
        lines.append("- 未生成决策摘要。")

    lines.extend(["", "## 指标契约检查"])
    if metric_contracts:
        lines.append(f"- **状态**：{metric_contracts['status']}")
        lines.append(f"- **摘要**：{metric_contracts['summary']}")
        lines.append(f"- **允许回答**：{metric_contracts['release_gate']['can_answer']}")
        lines.append(f"- **需要复核**：{metric_contracts['release_gate']['requires_review']}")
        for contract in metric_contracts.get("contracts", [])[:8]:
            issue_text = "；".join(contract.get("issues") or ["无问题"])
            lines.append(f"- `{contract['name']}`（{contract['type']}）：{contract['status']}，{issue_text}")
    else:
        lines.append("- 未生成指标契约检查。")

    lines.extend([
        "",
        "## 细分分析",
    ]
    )
    if sections["segment_breakdown"]:
        for item in sections["segment_breakdown"]:
            lines.append(f"- **{item['title']}**：证据块 `{item['evidence_title']}`")
    else:
        lines.append("- 未生成细分分析。")

    lines.extend(["", "## 数据质量"])
    if sections["data_quality"]:
        lines.extend(f"- {item['column']}：缺失率 {item['missing_pct']}%" for item in sections["data_quality"])
    else:
        lines.append("- 未生成数据质量快照。")

    lines.extend(["", "## 诊断洞察"])
    if sections["diagnostic_insights"]:
        lines.extend(
            f"- **{item['title']}**：{item['finding']}（证据：`{item['evidence_title']}`）"
            for item in sections["diagnostic_insights"]
        )
    else:
        lines.append("- 未生成诊断洞察。")

    lines.extend(["", "## 假设验证"])
    if investigation_cards:
        for card in investigation_cards:
            lines.append(f"- **{card['type']}**: {card['finding']}")
            for hypothesis in card.get("hypotheses", [])[:3]:
                lines.append(f"  - 假设：{hypothesis['hypothesis']}")
                lines.append(f"    - 当前判断：{hypothesis['current_assessment']}")
                lines.append(f"    - 验证方法：{hypothesis['validation']}")
    else:
        lines.append("- 未生成分析假设。")

    lines.extend(["", "## 分析图谱"])
    if analysis_graph:
        lines.append(f"- 节点：{len(analysis_graph.get('nodes', []))}")
        lines.append(f"- 关系：{len(analysis_graph.get('edges', []))}")
        for edge in analysis_graph.get("edges", [])[:12]:
            lines.append(f"- `{edge['source']}` → `{edge['target']}`: {edge['label']}")
    else:
        lines.append("- 未生成分析图谱。")

    lines.extend([
        "",
        "## 风险",
        *(f"- {item}" for item in sections["risks"]),
        "",
        "## 机会",
        *(f"- {item}" for item in sections["opportunities"]),
        "",
        "## 建议追问",
        *(f"- {item}" for item in sections["recommended_follow_up_questions"]),
        "",
        "## 使用的语义层",
        *(semantic_lines or ["- 尚未配置语义定义。"]),
        "",
        "## 证据块",
    ])
    for block in blocks:
        lines.extend([
            f"### {block['title']}",
            "",
            "SQL：",
            "```sql",
            block["sql"],
            "```",
            "",
            f"发现：{block.get('finding') or block.get('error') or '暂无'}",
            "",
        ])
    return "\n".join(lines)


def generate_report(db: Session, project_id: str, dataset: Dataset, title: str | None = None) -> AnalysisReport:
    load_dataset(project_id, dataset.file_path, dataset.source_type)
    schema = _schema(dataset)
    full_semantic = list_semantic_layer(db, project_id, dataset.id)
    semantic = {
        "metrics": [item for item in full_semantic["metrics"] if item.get("status") == "approved"],
        "dimensions": [item for item in full_semantic["dimensions"] if item.get("status") == "approved"],
    }
    approved_metric_columns = {
        column
        for metric in semantic["metrics"]
        for column in re.findall(r'"([^"]+)"', str(metric.get("expression") or ""))
    }
    approved_dimension_columns = {str(item.get("column")) for item in semantic["dimensions"]}
    numeric_columns = [
        column for column in schema
        if str(column.get("name")) in approved_metric_columns
        and _is_numeric(str(column.get("type", "")))
    ]
    dimensions = [
        column for column in schema
        if str(column.get("name")) in approved_dimension_columns
    ]
    analysis_metrics = sorted(semantic["metrics"], key=_metric_priority)
    memory = _recent_memory(db, project_id)

    report_title = title or f"{dataset.name} 洞察报告"
    blocks: list[dict[str, Any]] = []

    if analysis_metrics:
        metric = analysis_metrics[0]
        metric_name = str(metric.get("name") or "主要指标")
        metric_expression = str(metric.get("expression") or "")
        blocks.append(_run_block(
            project_id,
            f"总计：{metric_name}",
            f"SELECT ROUND(({metric_expression}), 2) AS metric_value FROM data",
        ))
        row_expression = _aggregate_inner(metric_expression)
        if row_expression:
            blocks.append(_run_block(
                project_id,
                f"平均值：{metric_name}",
                f"SELECT ROUND(AVG({row_expression}), 2) AS metric_average FROM data",
            ))

    if analysis_metrics and dimensions:
        metric = analysis_metrics[0]
        metric_name = str(metric.get("name") or "主要指标")
        metric_expression = str(metric.get("expression") or "")
        dim = dimensions[0]["name"]
        blocks.append(_run_block(
            project_id,
            f"排名靠前：按 {metric_name} 查看 {dim}",
            (
                f"SELECT {_quote(dim)} AS dimension, ROUND(({metric_expression}), 2) AS metric "
                f"FROM data GROUP BY {_quote(dim)} ORDER BY metric DESC LIMIT 10"
            ),
        ))
        blocks.append(_run_block(
            project_id,
            f"排名靠后：按 {metric_name} 查看 {dim}",
            (
                f"SELECT {_quote(dim)} AS dimension, ROUND(({metric_expression}), 2) AS metric "
                f"FROM data GROUP BY {_quote(dim)} ORDER BY metric ASC LIMIT 10"
            ),
        ))
        blocks.append(_run_block(
            project_id,
            "贡献集中度",
            (
                "WITH segment AS ("
                f"SELECT {_quote(dim)} AS dimension, ({metric_expression}) AS metric "
                f"FROM data GROUP BY {_quote(dim)}"
                ") "
                "SELECT dimension, ROUND(metric, 2) AS metric, "
                "ROUND(metric * 100.0 / NULLIF((SELECT SUM(metric) FROM segment), 0), 2) AS top_share_pct "
                "FROM segment ORDER BY metric DESC LIMIT 1"
            ),
        ))

    if len(analysis_metrics) > 1 and dimensions:
        metric = analysis_metrics[1]
        metric_name = str(metric.get("name") or "辅助指标")
        metric_expression = str(metric.get("expression") or "")
        dim = dimensions[0]["name"]
        blocks.append(_run_block(
            project_id,
            f"排名靠前：按 {metric_name} 查看 {dim}",
            (
                f"SELECT {_quote(dim)} AS dimension, ROUND(({metric_expression}), 2) AS metric "
                f"FROM data GROUP BY {_quote(dim)} ORDER BY metric DESC LIMIT 10"
            ),
        ))

    margin_columns = _pick_margin_columns(numeric_columns)
    if margin_columns:
        numerator, denominator = margin_columns
        blocks.append(_run_block(
            project_id,
            "整体利润率",
            f"SELECT ROUND(SUM({_quote(numerator)}) / NULLIF(SUM({_quote(denominator)}), 0), 4) AS margin FROM data",
        ))

    if numeric_columns:
        metric = numeric_columns[0]["name"]
        metric_literal = metric.replace("'", "''")
        blocks.append(_run_block(
            project_id,
            "数值异常扫描",
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
        blocks.append(_run_block(project_id, "数据质量快照", "SELECT " + ", ".join(missing_exprs) + " FROM data"))

    sections = _build_sections(dataset, blocks, semantic, analysis_metrics, dimensions)
    highlights = sections["executive_summary"][:2] + [
        b["finding"] for b in blocks if b.get("finding") and not b.get("error")
    ][:4]
    semantic_lines = [
        f"- 指标 `{m['name']}` = `{m['expression']}`" for m in semantic["metrics"][:8]
    ] + [
        f"- 维度 `{d['name']}` -> `{d['column']}`" for d in semantic["dimensions"][:8]
    ]
    investigation_cards = _build_investigation_cards(sections, blocks)
    decision_brief = _build_decision_brief(dataset, sections, investigation_cards, analysis_metrics, dimensions)
    metric_contracts = _build_metric_contracts(dataset, semantic, schema)
    analysis_graph = _build_analysis_graph(dataset, semantic, metric_contracts, investigation_cards, decision_brief)
    markdown = _render_markdown(report_title, dataset, sections, blocks, semantic_lines, investigation_cards, decision_brief, analysis_graph, metric_contracts)
    content = {
        "title": report_title,
        "dataset": {"id": dataset.id, "name": dataset.name, "rows": dataset.row_count, "columns": dataset.column_count},
        "highlights": highlights,
        "sections": sections,
        "investigation_cards": investigation_cards,
        "decision_brief": decision_brief,
        "analysis_graph": analysis_graph,
        "metric_contracts": metric_contracts,
        "blocks": blocks,
        "markdown": markdown,
        "governance": {
            "status": "governed" if semantic["metrics"] else "needs_metric_approval",
            "message": "本报告快照仅包含已审批通过的语义定义。",
        },
    }
    content = _json_safe(content)
    semantic = _json_safe(semantic)
    memory = _json_safe(memory)
    report = AnalysisReport(
        project_id=project_id,
        dataset_id=dataset.id,
        title=report_title,
        content=content,
        semantic_snapshot=semantic,
        memory=memory,
        status="draft",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


_LEGACY_TEXT_REPLACEMENTS = (
    ("按下一个可用维度拆分领先分组，并比较其利润率。", "按下一个可用维度拆分领先分组，并用另一个已审批指标交叉验证。"),
    ("在将其视为健康增长前，使用利润或利润率等第二个数值指标交叉验证领先分组。", "在将其视为健康增长前，使用数据集中已定义且审批的第二个数值指标交叉验证。"),
    ("领先分组在利润或利润率上是否同样领先？", "领先分组在另一个已审批指标上是否同样领先？"),
    ("Business owner / data lead", "业务负责人 / 数据负责人"),
    ("Auto Investigation", "自动调查"),
    ("Insight Report", "洞察报告"),
    ("No numeric columns were detected, so metric analysis is limited.", "未检测到可用的数值字段，指标分析能力受限。"),
    ("No categorical dimensions were detected, so segmentation analysis is limited.", "未检测到可用的分类维度，细分分析能力受限。"),
    ("No curated semantic metrics exist yet; report used schema-derived aggregates.", "尚无经过治理的语义指标，本报告使用了从数据结构推导的聚合结果。"),
    ("This is the main caveat to mention before sharing the analysis externally.", "这是对外分享分析结果前需要明确说明的主要限制。"),
    ("Automated risk scan", "自动风险扫描"),
    ("Automated opportunity scan", "自动机会扫描"),
    ("Validate the `risk` finding before making a business decision.", "在做出业务决策前，先验证“风险”这一发现。"),
    ("Which evidence block is most sensitive to this risk?", "哪个证据块对这一风险最敏感？"),
    ("Which risks could materially change the conclusion?", "哪些风险可能实质性改变当前结论？"),
    ("Which rows or segments should be investigated next?", "下一步应该重点调查哪些记录或分组？"),
    ("Data quality coverage", "数据质量覆盖率"),
    ("The main risk could materially change the report conclusion.", "主要风险可能实质性改变报告结论。"),
    ("Identify which evidence block or data-quality issue would change the decision if corrected.", "识别哪些证据块或数据质量问题在修正后会改变决策。"),
    ("Needs review before external sharing.", "对外分享前需要复核。"),
    ("Use the leading and trailing segments as follow-up analysis candidates.", "可将领先和落后分组作为后续重点分析对象。"),
    ("Convert repeated follow-up questions into saved workflows once the analysis path stabilizes.", "分析路径稳定后，可将反复出现的追问沉淀为自动化流程。"),
    ("This turns the report from a static summary into a next-step analysis workflow.", "这可以把静态报告转化为可继续执行的分析流程。"),
    ("The opportunity can become a reusable analysis workflow.", "这个机会可以沉淀为可复用的分析流程。"),
    ("Run the suggested follow-up and save the SQL-backed path if it remains useful.", "执行建议的后续分析，如果持续有价值，就保存这条由 SQL 支撑的路径。"),
    ("Actionable as a next analysis step.", "可作为下一步分析直接执行。"),
    ("Convert this opportunity into a repeatable analysis workflow.", "将这个机会转化为可重复执行的分析流程。"),
    ("Turn this opportunity into a concrete next analysis step.", "把这个机会转化为具体的下一步分析。"),
    ("Semantic Layer", "语义层"),
    ("Metric Contract Check", "指标契约检查"),
    ("Semantic contract audit", "语义契约审计"),
    ("Decision Brief", "决策摘要"),
    ("Executive-ready summary", "面向管理者的摘要"),
    ("grounds business definitions", "支撑业务定义"),
    ("audits metric contracts", "审计指标契约"),
    ("gates investigation", "控制调查准入"),
    ("validated by", "由此验证"),
    ("needs evidence", "需要证据"),
    ("explains", "尝试解释"),
    ("summarizes", "汇总为"),
    ("SQL-backed evidence", "SQL 支撑的证据"),
    ("Rule-based scan", "规则扫描"),
    ("Data quality snapshot", "数据质量快照"),
    ("No semantic contracts are configured for this dataset.", "该数据集尚未配置语义契约。"),
    ("All metric and dimension contracts passed.", "所有指标和维度契约均已通过。"),
    ("Some metric or dimension contracts require review.", "部分指标或维度契约需要复核。"),
    ("Only approved semantic definitions are included in this report snapshot.", "本报告快照仅包含已审批通过的语义定义。"),
    ("## Executive Summary", "## 执行摘要"),
    ("## Key Metrics", "## 关键指标"),
    ("## Decision Brief", "## 决策摘要"),
    ("## Metric Contract Check", "## 指标契约检查"),
    ("## Segment Breakdown", "## 细分分析"),
    ("## Data Quality", "## 数据质量"),
    ("## Diagnostic Insights", "## 诊断洞察"),
    ("## Hypothesis Engine", "## 假设验证"),
    ("## Analysis Graph", "## 分析图谱"),
    ("## Risks", "## 风险"),
    ("## Opportunities", "## 机会"),
    ("## Recommended Follow-up Questions", "## 建议追问"),
    ("## Semantic Layer Used", "## 使用的语义层"),
    ("## Evidence Blocks", "## 证据块"),
    ("语义层 Used", "使用的语义层"),
    ("Generated at:", "生成时间："),
    ("Dataset:", "数据集："),
    ("Finding:", "发现："),
    ("SQL:", "SQL："),
    ("- **Audience**:", "- **面向对象**："),
    ("- **Situation**:", "- **现状**："),
    ("- **Diagnosis**:", "- **诊断**："),
    ("- **Risk**:", "- **风险**："),
    ("- **Recommendation**:", "- **建议**："),
    ("- **Confidence**:", "- **置信度**："),
    ("- **Evidence**:", "- **证据**："),
    ("- **Next metrics to monitor**:", "- **下一步关注指标**："),
    ("- **Status**:", "- **状态**："),
    ("- **Summary**:", "- **摘要**："),
    ("- **Can answer**:", "- **允许回答**："),
    ("- **Requires review**:", "- **需要复核**："),
    ("No segment breakdown was generated.", "未生成细分分析。"),
    ("No diagnostic insight was generated.", "未生成诊断洞察。"),
    ("No semantic definitions configured yet.", "尚未配置语义定义。"),
    ("Hypothesis:", "假设："),
    ("Current assessment:", "当前判断："),
    ("Validation:", "验证方法："),
    ("Nodes:", "节点："),
    ("Edges:", "关系："),
    ("**risk**", "**风险**"),
    ("**opportunity**", "**机会**"),
    ("**置信度**： medium", "**置信度**：中"),
    ("**置信度**： high", "**置信度**：高"),
    ("**置信度**： low", "**置信度**：低"),
    ("**状态**： pass", "**状态**：通过"),
    ("**状态**： warn", "**状态**：有警告"),
    ("**允许回答**： True", "**允许回答**：是"),
    ("**允许回答**： False", "**允许回答**：否"),
    ("**需要复核**： True", "**需要复核**：是"),
    ("**需要复核**： False", "**需要复核**：否"),
)


def _localize_legacy_text(value: str) -> str:
    text = value
    text = re.sub(r"^(.*?) Auto Investigation$", r"\1 自动调查", text)
    text = re.sub(r"^(.*?) Insight Report$", r"\1 洞察报告", text)
    text = re.sub(
        r"Analyzed ([\d,]+) rows across (\d+) columns from `([^`]+)`\.",
        r"已分析 `\3` 的 \1 行、\2 个字段。",
        text,
    )
    text = re.sub(
        r"Generated (\d+) SQL-backed evidence blocks under the current SQL safety policy\.",
        r"在当前 SQL 安全策略下生成了 \1 个有 SQL 支撑的证据块。",
        text,
    )
    text = re.sub(r"^(\d+)/(\d+) semantic contracts passed\.$", r"\1/\2 个语义契约检查通过。", text)
    text = re.sub(r"^(.*?) rows / (.*?) columns$", r"\1 行 / \2 个字段", text)
    text = re.sub(r"^(\d+) metrics / (\d+) dimensions$", r"\1 个指标 / \2 个维度", text)
    text = re.sub(
        r"Dataset: ([^\n]+?) \(([\d,]+) rows, (\d+) columns\)",
        r"数据集：\1（\2 行，\3 个字段）",
        text,
    )
    text = re.sub(r"([\w.-]+): ([\d.]+)% missing", r"\1：缺失率 \2%", text)
    text = re.sub(r"Data quality snapshot: top result is ", "数据质量快照：首条结果为 ", text)
    for source, target in _LEGACY_TEXT_REPLACEMENTS:
        text = text.replace(source, target)
    return text


def _localize_legacy_content(value: Any, key: str | None = None) -> Any:
    untouched_keys = {
        "sql", "columns", "rows", "type", "status", "severity", "confidence",
        "source", "target", "entry_node", "terminal_node", "id", "project_id",
        "dataset_id", "created_at", "published_at", "published_by",
    }
    if isinstance(value, dict):
        return {item_key: _localize_legacy_content(item, item_key) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_localize_legacy_content(item, key) for item in value]
    if isinstance(value, str) and key not in untouched_keys:
        return _localize_legacy_text(value)
    return value


def serialize_report(report: AnalysisReport) -> dict:
    return {
        "id": report.id,
        "project_id": report.project_id,
        "dataset_id": report.dataset_id,
        "title": _localize_legacy_text(report.title),
        "content": _localize_legacy_content(report.content),
        "semantic_snapshot": report.semantic_snapshot,
        "memory": report.memory,
        "status": report.status,
        "published_at": report.published_at.isoformat() if report.published_at else None,
        "published_by": report.published_by,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }
