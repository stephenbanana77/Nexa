"""Agent tools — registry-based tool execution."""
from typing import Any, Callable, Protocol
from dataclasses import dataclass, field
from tools.query_engine import get_engine, engine_registry, QueryResult
from database import SessionLocal
from models.project import Dataset


@dataclass
class Tool:
    """A tool that can be invoked by the agent."""
    name: str
    description: str
    fn: Callable[..., Any]
    parameters: dict[str, str] = field(default_factory=dict)


class ToolRegistry:
    """Dynamic registry for agent tools. Supports runtime registration for Skills and MCPs."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def remove(self, name: str):
        self._tools.pop(name, None)


# Global singleton
tool_registry = ToolRegistry()


# ---- SQL safety ----
# Re-exported from services/sql_policy.py (single source of truth)
from services.sql_policy import validate_sql, MAX_ROWS, QUERY_TIMEOUT_SEC

_validate_sql = validate_sql  # backward-compat alias


# ---- Built-in tools ----

def _execute_query_tool(project_id: str, sql: str) -> QueryResult:
    """Execute SQL query (DuckDB or MySQL) with safety checks."""
    is_safe, result = _validate_sql(sql)
    if not is_safe:
        raise ValueError(result)
    sql = result
    engine = get_engine(project_id)
    # Set a timeout to prevent runaway queries
    if hasattr(engine, "conn"):
        try:
            engine.conn.execute(f"SET threads=4")
        except Exception:
            pass
    return engine.query(sql, timeout_sec=QUERY_TIMEOUT_SEC)


def _get_schema_tool(project_id: str, table_name: str = "data") -> list[dict]:
    """Get schema for a table."""
    engine = get_engine(project_id)
    schema = engine.get_schema(table_name)
    return [{"name": c.name, "type": c.type, "missing_pct": c.missing_pct} for c in schema]


def _suggest_chart_tool(query_result: QueryResult) -> dict[str, Any] | None:
    """Auto-suggest a chart configuration from query results."""
    columns = query_result.columns
    rows = query_result.rows
    if not columns or not rows:
        return None

    def as_number(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(str(value).replace(",", ""))
        except (TypeError, ValueError):
            return None

    sample = rows[:20]
    # Pick a categorical axis and include up to three numeric result columns.
    category_idx = next(
        (
            idx
            for idx in range(len(columns))
            if any(as_number(row[idx] if idx < len(row) else None) is None for row in sample)
        ),
        0,
    )
    numeric_indexes = [
        idx for idx in range(len(columns))
        if idx != category_idx
        and any(as_number(row[idx] if idx < len(row) else None) is not None for row in sample)
    ][:3]
    if not numeric_indexes:
        return None

    chart_type = "line" if any(
        token in columns[category_idx].lower()
        for token in ("date", "time", "month", "quarter", "year", "日期", "时间", "月份", "季度")
    ) else "bar"
    palette = ["#2563EB", "#16A34A", "#D97706"]
    series = [
        {
            "name": columns[idx],
            "type": chart_type,
            "data": [
                as_number(row[idx] if idx < len(row) else None) or 0
                for row in sample
            ],
            "itemStyle": {"color": palette[pos]},
        }
        for pos, idx in enumerate(numeric_indexes)
    ]
    return {
        "type": chart_type,
        "title": f"{'、'.join(columns[idx] for idx in numeric_indexes)} by {columns[category_idx]}",
        "options": {
            "tooltip": {"trigger": "axis"},
            "legend": {"data": [item["name"] for item in series]},
            "xAxis": {
                "type": "category",
                "data": [str(row[category_idx])[:20] for row in sample],
            },
            "yAxis": {"type": "value"},
            "series": series,
        },
    }


# Register built-in tools
tool_registry.register(Tool(
    name="execute_query",
    description="Execute a SQL query against the project's dataset",
    fn=_execute_query_tool,
))
tool_registry.register(Tool(
    name="get_schema",
    description="Get schema information for a table",
    fn=_get_schema_tool,
))
tool_registry.register(Tool(
    name="suggest_chart",
    description="Suggest a chart configuration based on query results",
    fn=_suggest_chart_tool,
))


# ---- Backward-compatible shortcuts ----

def execute_query(project_id: str, sql: str) -> dict[str, Any]:
    result = _execute_query_tool(project_id, sql)
    return {"columns": result.columns, "rows": result.rows, "row_count": result.row_count}


def suggest_chart(sql: str, query_result: dict[str, Any]) -> dict[str, Any] | None:
    qr = QueryResult(
        columns=query_result.get("columns", []),
        rows=query_result.get("rows", []),
        row_count=query_result.get("row_count", 0),
    )
    return _suggest_chart_tool(qr)
