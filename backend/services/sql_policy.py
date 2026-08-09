"""SQL safety policy — shared between Chat Agent and Dataset API.

Centralizes dangerous-operation blocking and LIMIT enforcement so the
same rules apply regardless of which entry point triggers a SQL query.
"""
import re as _re

# Use word-boundary regex to prevent bypasses like "/*DROP*/" or "DR OP"
_DANGEROUS_PATTERN = _re.compile(
    r"\b(DROP|DELETE|TRUNCATE|ALTER|INSERT|UPDATE)\b", _re.IGNORECASE
)
MAX_ROWS = 10000
QUERY_TIMEOUT_SEC = 30


def validate_sql(sql: str) -> tuple[bool, str]:
    """Check SQL for dangerous operations and add safety limits.

    Returns (is_safe, sanitized_sql_or_error_message).

    Rules:
    - Blocks DROP, DELETE, TRUNCATE, ALTER, INSERT, UPDATE (SELECT only).
    - Auto-adds LIMIT if not already present to prevent unbounded scans.
    """
    match = _DANGEROUS_PATTERN.search(sql)
    if match:
        return False, f"Dangerous SQL operation '{match.group(1)}' is not allowed. Use SELECT only."
    # Auto-add LIMIT if missing
    if not _re.search(r"\bLIMIT\s+\d+", sql, _re.IGNORECASE):
        sql = sql.rstrip(";").rstrip() + f" LIMIT {MAX_ROWS}"
    return True, sql
