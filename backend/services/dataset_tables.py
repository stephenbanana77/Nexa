"""Stable SQL table names for uploaded datasets."""
from __future__ import annotations

import re

from sqlglot import exp, parse_one


def dataset_table_name(dataset_id: str, prefix: str = "ds") -> str:
    """Return a stable DuckDB-safe table name for a dataset id."""
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", dataset_id).strip("_").lower()
    if not normalized:
        normalized = "data"
    if normalized[0].isdigit():
        normalized = f"{prefix}_{normalized}"
    return normalized[:48]


def dataset_engine_key(project_id: str, dataset_id: str, source_type: str) -> str:
    """Return the runtime engine key for a dataset source."""
    return f"mysql:{dataset_id}" if source_type == "mysql" else project_id


def bind_default_table(sql: str, dataset_id: str, dialect: str = "duckdb") -> str:
    """Bind compatibility references to ``data`` to one immutable dataset table."""
    return bind_table(sql, dataset_table_name(dataset_id), dialect=dialect)


def bind_table(sql: str, target: str, dialect: str = "duckdb") -> str:
    """Bind compatibility references to ``data`` to a validated table name."""
    statement = parse_one(sql, read=dialect)
    cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}

    def replace(node: exp.Expression) -> exp.Expression:
        if (
            isinstance(node, exp.Table)
            and node.name.lower() == "data"
            and "data" not in cte_names
        ):
            return exp.to_table(target)
        return node

    return statement.transform(replace).sql(dialect=dialect, comments=False)
