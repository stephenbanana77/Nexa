"""Semantic layer helpers for governed AI data analysis."""
from __future__ import annotations

from sqlalchemy.orm import Session

from models.project import SemanticDimension, SemanticMetric


_TECHNICAL_FIELD_TOKENS = (
    "id", "code", "key", "index", "row", "zip", "postal", "latitude", "longitude",
)

_ADDITIVE_MEASURE_TOKENS = (
    "sales", "revenue", "amount", "profit", "income", "cost", "expense",
    "quantity", "qty", "units", "count", "cnt", "orders", "volume",
)

_DIMENSION_PRIORITY_TOKENS = (
    "region", "segment", "category", "sub_category", "country", "state", "city",
    "channel", "brand", "department", "market", "date", "month", "quarter", "year",
)

_FREE_TEXT_TOKENS = ("description", "comment", "note", "remark", "address")


def _is_technical_numeric_field(name: str) -> bool:
    """Avoid treating identifiers and location codes as additive business metrics."""
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
    tokens = set(normalized.split("_"))
    return bool(tokens.intersection(_TECHNICAL_FIELD_TOKENS)) or any(
        normalized.startswith(prefix) for prefix in ("row", "index", "postal", "zip")
    )


def _is_additive_measure(name: str) -> bool:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
    tokens = set(normalized.split("_"))
    return any(token in tokens or token in normalized for token in _ADDITIVE_MEASURE_TOKENS)


def _normalized(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


def _is_dimension_candidate(name: str, dtype: str) -> bool:
    normalized = _normalized(name)
    tokens = set(normalized.split("_"))
    if _is_technical_numeric_field(name) or normalized.endswith(("id", "code", "no", "number")):
        return False
    if any(token in normalized for token in _FREE_TEXT_TOKENS):
        return False
    if any(token in dtype for token in ("int", "float", "double", "decimal", "number")):
        return any(token in tokens for token in ("year", "month", "quarter"))
    return any(token in normalized for token in _DIMENSION_PRIORITY_TOKENS) or "char" in dtype or "date" in dtype or "time" in dtype


def _matching_column(schema_info: list[dict], candidates: tuple[str, ...]) -> str | None:
    for column in schema_info:
        name = str(column.get("name", "")).strip()
        compact = "".join(ch.lower() for ch in name if ch.isalnum())
        if any(candidate in compact for candidate in candidates):
            return name
    return None


def list_semantic_layer(
    db: Session,
    project_id: str,
    dataset_id: str | None = None,
) -> dict:
    metric_query = db.query(SemanticMetric).filter(SemanticMetric.project_id == project_id)
    dimension_query = db.query(SemanticDimension).filter(SemanticDimension.project_id == project_id)
    if dataset_id:
        metric_query = metric_query.filter(
            (SemanticMetric.dataset_id == dataset_id) | (SemanticMetric.dataset_id.is_(None))
        )
        dimension_query = dimension_query.filter(
            (SemanticDimension.dataset_id == dataset_id) | (SemanticDimension.dataset_id.is_(None))
        )

    metrics = [
        {
            "id": item.id,
            "dataset_id": item.dataset_id,
            "name": item.name,
            "expression": item.expression,
            "description": item.description,
            "format": item.format,
            "status": item.status,
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in metric_query.order_by(SemanticMetric.created_at.desc()).all()
    ]
    dimensions = [
        {
            "id": item.id,
            "dataset_id": item.dataset_id,
            "name": item.name,
            "column": item.column,
            "description": item.description,
            "status": item.status,
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in dimension_query.order_by(SemanticDimension.created_at.desc()).all()
    ]
    return {"metrics": metrics, "dimensions": dimensions}


def semantic_context_text(db: Session, project_id: str, dataset_id: str | None = None) -> str:
    """Render semantic definitions as prompt/schema context."""
    layer = list_semantic_layer(db, project_id, dataset_id)
    metrics = [item for item in layer["metrics"] if item.get("status") == "approved"]
    dimensions = [item for item in layer["dimensions"] if item.get("status") == "approved"]
    lines: list[str] = []
    if metrics:
        lines.append("BUSINESS METRICS:")
        for metric in metrics:
            desc = f" -- {metric['description']}" if metric.get("description") else ""
            lines.append(f"- {metric['name']} = {metric['expression']}{desc}")
    if dimensions:
        lines.append("BUSINESS DIMENSIONS:")
        for dim in dimensions:
            desc = f" -- {dim['description']}" if dim.get("description") else ""
            lines.append(f"- {dim['name']} maps to column \"{dim['column']}\"{desc}")
    return "\n".join(lines)


def seed_semantic_layer_from_schema(
    db: Session,
    project_id: str,
    dataset_id: str,
    schema_info: list[dict] | None,
) -> dict:
    """Create lightweight metric/dimension suggestions from dataset schema."""
    schema_info = schema_info or []
    numeric_tokens = ("int", "float", "double", "decimal", "number")
    created = {"metrics": 0, "dimensions": 0}

    existing_metrics = {
        item.name.lower()
        for item in db.query(SemanticMetric).filter(
            SemanticMetric.project_id == project_id,
            SemanticMetric.dataset_id == dataset_id,
        )
    }
    existing_dimensions = {
        item.name.lower()
        for item in db.query(SemanticDimension).filter(
            SemanticDimension.project_id == project_id,
            SemanticDimension.dataset_id == dataset_id,
        )
    }

    quantity_column = _matching_column(schema_info, ("quantity", "qty", "units"))
    price_column = _matching_column(schema_info, ("unitprice", "price"))
    if quantity_column and price_column and "销售额" not in existing_metrics:
        db.add(SemanticMetric(
            project_id=project_id,
            dataset_id=dataset_id,
            name="销售额",
            expression=f'SUM("{quantity_column}" * "{price_column}")',
            description=f"数量与单价的乘积汇总，保留退货负数（{quantity_column} × {price_column}）。",
            format="currency",
        ))
        created["metrics"] += 1
        existing_metrics.add("销售额")

    for col in schema_info:
        name = str(col.get("name", "")).strip()
        dtype = str(col.get("type", "")).lower()
        if not name:
            continue
        if (
            any(token in dtype for token in numeric_tokens)
            and not _is_technical_numeric_field(name)
            and _is_additive_measure(name)
        ):
            metric_name = f"Total {name}"
            if metric_name.lower() not in existing_metrics:
                db.add(SemanticMetric(
                    project_id=project_id,
                    dataset_id=dataset_id,
                    name=metric_name,
                    expression=f'SUM("{name}")',
                    description=f"Auto-suggested aggregate for numeric column {name}.",
                    format="number",
                ))
                created["metrics"] += 1
        elif _is_dimension_candidate(name, dtype):
            if name.lower() not in existing_dimensions:
                db.add(SemanticDimension(
                    project_id=project_id,
                    dataset_id=dataset_id,
                    name=name,
                    column=name,
                    description=f"根据字段 {name} 自动建议的业务维度。",
                ))
                created["dimensions"] += 1
    db.commit()
    return created
