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

    if len(columns) == 2 and len(rows) > 0:
        try:
            float(str(rows[0][1]).replace(",", ""))
            return {
                "type": "bar",
                "title": f"{columns[1]} by {columns[0]}",
                "options": {
                    "tooltip": {"trigger": "axis"},
                    "xAxis": {
                        "type": "category",
                        "data": [str(r[0])[:20] for r in rows[:20]],
                    },
                    "yAxis": {"type": "value"},
                    "series": [{
                        "name": columns[1],
                        "type": "bar",
                        "data": [float(str(r[1]).replace(",", "")) if r[1] is not None else 0 for r in rows[:20]],
                        "itemStyle": {"color": "#2563EB"},
                    }],
                },
            }
        except (ValueError, IndexError):
            pass
    return None


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
