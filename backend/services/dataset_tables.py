"""Stable SQL table names for uploaded datasets."""
from __future__ import annotations

import re


def dataset_table_name(dataset_id: str, prefix: str = "ds") -> str:
    """Return a stable DuckDB-safe table name for a dataset id."""
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", dataset_id).strip("_").lower()
    if not normalized:
        normalized = "data"
    if normalized[0].isdigit():
        normalized = f"{prefix}_{normalized}"
    return normalized[:48]
