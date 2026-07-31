"""Agent tools — SQL execution and chart generation."""
from typing import Any
from tools.query_engine import get_engine, load_dataset, get_mysql_connector
from database import SessionLocal
from models.project import Dataset


def execute_query(project_id: str, sql: str) -> dict[str, Any]:
    """Execute SQL against the project's dataset (DuckDB or MySQL)."""
    # Check if this project uses MySQL
    mysql = get_mysql_connector(project_id)
    if mysql:
        return mysql.query(sql)

    # Default: DuckDB
    db = SessionLocal()
    try:
        dataset = (
            db.query(Dataset)
            .filter(Dataset.project_id == project_id)
            .order_by(Dataset.created_at.desc())
            .first()
        )
        if dataset:
            engine = get_engine(project_id)
            load_dataset(engine, dataset.file_path, dataset.source_type)
    finally:
        db.close()

    engine = get_engine(project_id)
    return engine.query(sql)


def suggest_chart(sql: str, query_result: dict[str, Any]) -> dict[str, Any] | None:
    """Suggest a chart configuration based on query results."""
    columns = query_result.get("columns", [])
    rows = query_result.get("rows", [])

    if not columns or not rows:
        return None

    # Auto-suggest: if 2 columns with the second being numeric → bar chart
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
