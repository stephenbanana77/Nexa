"""On-demand data quality checks used before analysis and publication."""
from __future__ import annotations

from typing import Any

from models.project import Dataset
from tools import get_engine, load_dataset


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _is_numeric(dtype: str) -> bool:
    return any(token in dtype.lower() for token in ("int", "float", "double", "decimal", "number"))


def _normalize_type(dtype: str) -> str:
    lowered = dtype.lower()
    if any(token in lowered for token in ("int", "float", "double", "decimal", "number", "real")):
        return "numeric"
    if any(token in lowered for token in ("char", "text", "string", "object", "varchar")):
        return "text"
    if "bool" in lowered:
        return "boolean"
    if any(token in lowered for token in ("date", "time", "timestamp")):
        return "temporal"
    return lowered


def check_dataset_quality(project_id: str, dataset: Dataset) -> dict[str, Any]:
    """Return a fresh, explainable quality snapshot for a dataset."""
    if dataset.source_type in ("csv", "xlsx", "xls", ".csv", ".xlsx", ".xls"):
        load_dataset(project_id, dataset.file_path, dataset.source_type)
    engine = get_engine(project_id)
    checks: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    try:
        schema = engine.get_schema("data")
    except Exception:
        schema = []
    def column_value(column: Any, key: str, default: Any = "") -> Any:
        if isinstance(column, dict):
            return column.get(key, default)
        return getattr(column, key, default)

    schema_names = [str(column_value(column, "name")) for column in schema]
    schema_types = {str(column_value(column, "name")): str(column_value(column, "type")) for column in schema}

    if not schema:
        # External connectors expose their own table list rather than a single `data` table.
        return {
            "status": "warn",
            "summary": "Quality checks are limited for this external connection; inspect source tables before publishing.",
            "checks": [{"name": "schema", "status": "warn", "details": "No default data table is available."}],
            "issues": [{"severity": "warning", "name": "schema", "details": "No default data table is available."}],
            "row_count": dataset.row_count,
            "column_count": dataset.column_count,
        }

    try:
        row_count = engine.query("SELECT COUNT(*) AS row_count FROM data").rows[0][0]
        checks.append({"name": "row_count", "status": "pass" if row_count > 0 else "fail", "value": row_count})
        if not row_count:
            issues.append({"severity": "error", "name": "row_count", "details": "Dataset is empty."})
    except Exception as exc:
        row_count = dataset.row_count
        checks.append({"name": "row_count", "status": "fail", "details": str(exc)})
        issues.append({"severity": "error", "name": "row_count", "details": str(exc)})

    missing_expr = ", ".join(
        f"ROUND(SUM(CASE WHEN {_quote(name)} IS NULL THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS {_quote(name + '_missing_pct')}"
        for name in schema_names
    )
    try:
        missing_row = engine.query(f"SELECT {missing_expr} FROM data").rows[0] if missing_expr else []
        missing = []
        for index, name in enumerate(schema_names):
            pct = float(missing_row[index] or 0)
            missing.append({"column": name, "missing_pct": pct})
            if pct > 10:
                issues.append({"severity": "warning", "name": "missing_values", "column": name, "details": f"{pct:.2f}% missing"})
        checks.append({"name": "missing_values", "status": "warn" if any(item["missing_pct"] > 10 for item in missing) else "pass", "columns": missing})
    except Exception as exc:
        checks.append({"name": "missing_values", "status": "fail", "details": str(exc)})
        issues.append({"severity": "error", "name": "missing_values", "details": str(exc)})

    try:
        distinct_count = engine.query("SELECT COUNT(*) FROM (SELECT DISTINCT * FROM data)").rows[0][0]
        duplicate_count = max(int(row_count) - int(distinct_count), 0)
        checks.append({"name": "duplicate_rows", "status": "warn" if duplicate_count else "pass", "value": duplicate_count})
        if duplicate_count:
            issues.append({"severity": "warning", "name": "duplicate_rows", "details": f"{duplicate_count} duplicate rows detected."})
    except Exception as exc:
        checks.append({"name": "duplicate_rows", "status": "warn", "details": str(exc)})

    numeric_columns = [name for name, dtype in schema_types.items() if _is_numeric(dtype)]
    negative_counts: dict[str, int] = {}
    for name in numeric_columns:
        try:
            count = int(engine.query(f"SELECT COUNT(*) FROM data WHERE {_quote(name)} < 0").rows[0][0])
            negative_counts[name] = count
            if count:
                issues.append({"severity": "warning", "name": "negative_values", "column": name, "details": f"{count} negative values"})
        except Exception:
            continue
    checks.append({"name": "negative_values", "status": "warn" if negative_counts and any(negative_counts.values()) else "pass", "columns": negative_counts})

    expected_schema = {str(item.get("name")): str(item.get("type", "")) for item in (dataset.schema_info or [])}
    drift = [
        {"column": name, "expected": expected_schema[name], "actual": schema_types.get(name, "missing")}
        for name in set(expected_schema) | set(schema_types)
        if _normalize_type(expected_schema.get(name, "")) != _normalize_type(schema_types.get(name, ""))
    ]
    checks.append({"name": "schema_drift", "status": "fail" if drift else "pass", "columns": drift})
    if drift:
        issues.append({"severity": "error", "name": "schema_drift", "details": "Dataset schema changed since ingestion.", "columns": drift})

    status = "fail" if any(issue["severity"] == "error" for issue in issues) else "warn" if issues else "pass"
    return {
        "status": status,
        "summary": {
            "pass": "No blocking quality issues detected.",
            "warn": "Quality checks completed with warnings; review before publishing.",
            "fail": "Blocking quality issues detected; publishing is not allowed.",
        }[status],
        "checks": checks,
        "issues": issues,
        "row_count": int(row_count),
        "column_count": len(schema_names),
    }
