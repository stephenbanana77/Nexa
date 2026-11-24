"""Skill step executor — runs individual steps of a Skill."""
import asyncio
import re
from typing import Any, AsyncGenerator
from agents.llm import achat
from agents.tools import execute_query, suggest_chart
from agents.context import get_schema_context
from database import SessionLocal
from models.project import Dataset
from services.dataset_tables import bind_default_table, dataset_table_name
from tools import load_dataset
from utils.config import settings


async def execute_skill(
    skill: dict,
    project_id: str,
    params: dict = None,
    schema_override: str | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Execute a skill step by step, yielding progress events."""
    params = params or {}
    definition = skill.get("definition", {})
    steps = definition.get("steps", [])
    if not steps:
        yield {"event": "skill_failed", "message": "Skill has no executable steps"}
        return
    dataset_id = params.get("dataset_id")
    dataset_schema: list[dict[str, Any]] = []
    if dataset_id:
        db = SessionLocal()
        try:
            dataset = db.query(Dataset).filter(
                Dataset.id == dataset_id,
                Dataset.project_id == project_id,
            ).first()
            if not dataset:
                raise ValueError("Dataset is not available in this project")
            dataset_schema = list(dataset.schema_info or [])
            load_dataset(
                project_id,
                dataset.file_path,
                dataset.source_type,
                table_name=dataset_table_name(dataset.id),
            )
        finally:
            db.close()
    schema = schema_override or get_schema_context(project_id, dataset_id)
    title = skill.get("title", skill.get("name", "Skill"))

    context = {
        "schema": schema,
        "project_id": project_id,
        "params": params,
        "dataset_schema": dataset_schema,
        "previous_results": [],
    }

    yield {"event": "skill_start", "message": f"Running: {title}", "total_steps": len(steps)}

    for i, step in enumerate(steps):
        step_type = step.get("type", "sql")
        yield {"event": "step_start", "message": f"Step {i+1}/{len(steps)}: {step_type}", "step": i + 1, "type": step_type}

        try:
            if step_type == "sql":
                result = await asyncio.wait_for(
                    _execute_sql_step(step, context),
                    timeout=settings.SKILL_STEP_TIMEOUT_SEC,
                )
                context["previous_results"].append(result)
                yield {"event": "step_done", "step": i + 1, "type": "sql", "result": result}

            elif step_type == "visualize":
                prev = context["previous_results"][-1] if context["previous_results"] else {}
                chart = await asyncio.wait_for(
                    _execute_visualize_step(step, prev),
                    timeout=settings.SKILL_STEP_TIMEOUT_SEC,
                )
                context["previous_results"].append(chart)
                yield {"event": "step_done", "step": i + 1, "type": "visualize", "chart": chart}

            elif step_type == "insight":
                prev = context["previous_results"]
                insight = await asyncio.wait_for(
                    _execute_insight_step(step, prev, context),
                    timeout=settings.SKILL_STEP_TIMEOUT_SEC,
                )
                yield {"event": "step_done", "step": i + 1, "type": "insight", "insight": insight}

            elif step_type == "python":
                # Deferred: Python sandbox execution
                yield {"event": "step_done", "step": i + 1, "type": "python", "message": "Python execution not yet supported"}

            else:
                yield {"event": "step_skip", "step": i + 1, "message": f"Unknown step type: {step_type}"}

            await asyncio.sleep(0.3)

        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            message = f"Step {i + 1} timed out after {settings.SKILL_STEP_TIMEOUT_SEC}s"
            yield {"event": "step_error", "step": i + 1, "message": message, "timeout": True}
            yield {"event": "skill_failed", "message": message}
            return
        except Exception as e:
            yield {"event": "step_error", "step": i + 1, "message": str(e)}
            yield {"event": "skill_failed", "message": str(e)}
            return

    yield {"event": "skill_done", "message": f"{title} complete"}


async def _execute_sql_step(step: dict, context: dict) -> dict:
    """Execute deterministic built-in SQL or generate SQL for custom skills."""
    prompt_template = step.get("prompt", "SELECT * FROM data LIMIT 10")
    schema = context["schema"]
    strategy = step.get("strategy")
    sql = _deterministic_sql(strategy, context.get("dataset_schema") or []) if strategy else None

    if not sql:
        full_prompt = f"""You are a data analyst. Given the dataset schema, write a SQL query.

Schema:
{schema}

Task: {prompt_template}

Respond with ONLY the SQL query in a markdown code block. No explanation."""
        response = await achat([{"role": "user", "content": full_prompt}])
        sql_match = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
        sql = sql_match.group(1).strip() if sql_match else response.strip()
    dataset_id = context.get("params", {}).get("dataset_id")
    if dataset_id:
        sql = bind_default_table(sql, dataset_id)

    result = await asyncio.to_thread(execute_query, context["project_id"], sql)
    return {"sql": sql, "columns": result["columns"], "rows": result["rows"], "row_count": result["row_count"]}


async def _execute_visualize_step(step: dict, previous_result: dict) -> dict | None:
    """Generate a chart from the previous step's results."""
    chart_type = step.get("chart", "bar")
    sql = previous_result.get("sql", "")
    chart = suggest_chart(sql, {
        "columns": previous_result.get("columns", []),
        "rows": previous_result.get("rows", []),
        "row_count": previous_result.get("row_count", 0),
    })

    if chart and chart_type != "bar":
        chart["type"] = chart_type
        if chart.get("options", {}).get("series"):
            for s in chart["options"]["series"]:
                s["type"] = chart_type

    return chart


async def _execute_insight_step(step: dict, previous_results: list, context: dict) -> str:
    """Generate AI insight from accumulated results."""
    if step.get("strategy") == "evidence_summary":
        return _deterministic_insight(previous_results)

    prompt_template = step.get("prompt", "Summarize the results.")
    schema = context["schema"]

    # Build context from previous steps
    results_text = ""
    for i, r in enumerate(previous_results):
        if isinstance(r, dict) and "sql" in r:
            results_text += f"\nStep {i+1} SQL: {r['sql']}\n"
            results_text += f"Columns: {r.get('columns', [])}\n"
            results_text += f"Rows ({r.get('row_count', 0)}): {str(r.get('rows', [])[:5])[:1000]}\n"
        elif isinstance(r, dict) and "type" in r:
            results_text += f"\nStep {i+1}: Generated a {r.get('type', 'chart')} chart\n"

    full_prompt = f"""You are a data analyst. Analyze the following results and provide insights.

Dataset schema:
{schema}

Analysis results:
{results_text}

Task: {prompt_template}

Respond in Markdown format with a clear structure."""

    return await achat([{"role": "user", "content": full_prompt}])


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _is_numeric(dtype: str) -> bool:
    return any(token in dtype.lower() for token in ("int", "float", "double", "decimal", "number"))


def _is_temporal(name: str, dtype: str) -> bool:
    lowered = f"{name} {dtype}".lower()
    return any(token in lowered for token in ("date", "time", "timestamp", "month", "quarter", "year"))


def _is_technical(name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    tokens = set(normalized.split("_"))
    return bool(tokens.intersection({"id", "code", "key", "index", "row", "zip", "postal"})) or normalized.endswith(("id", "code"))


def _find_column(schema: list[dict[str, Any]], candidates: tuple[str, ...]) -> str | None:
    for column in schema:
        name = str(column.get("name") or "")
        normalized = re.sub(r"[^a-z0-9]+", "", name.lower())
        if any(candidate in normalized for candidate in candidates):
            return name
    return None


def _numeric_columns(schema: list[dict[str, Any]]) -> list[str]:
    return [
        str(column.get("name"))
        for column in schema
        if _is_numeric(str(column.get("type") or "")) and not _is_technical(str(column.get("name") or ""))
    ]


def _business_dimension(schema: list[dict[str, Any]]) -> str | None:
    priority = ("country", "region", "segment", "category", "state", "city", "channel", "brand")
    candidates = [
        str(column.get("name"))
        for column in schema
        if not _is_numeric(str(column.get("type") or ""))
        and not _is_temporal(str(column.get("name") or ""), str(column.get("type") or ""))
        and not _is_technical(str(column.get("name") or ""))
        and not any(token in str(column.get("name") or "").lower() for token in ("description", "comment", "note"))
    ]
    return next((name for token in priority for name in candidates if token in name.lower()), candidates[0] if candidates else None)


def _measure_expression(schema: list[dict[str, Any]]) -> tuple[str, str] | None:
    quantity = _find_column(schema, ("quantity", "qty", "units"))
    price = _find_column(schema, ("unitprice", "price"))
    if quantity and price:
        return "net_sales", f"SUM({_quote(quantity)} * {_quote(price)})"

    numeric = _numeric_columns(schema)
    if not numeric:
        return None
    priority = ("sales", "revenue", "amount", "profit", "quantity", "qty", "units", "orders", "volume")
    selected = next((name for token in priority for name in numeric if token in name.lower()), numeric[0])
    return selected, f"SUM({_quote(selected)})"


def _summary_sql(schema: list[dict[str, Any]]) -> str:
    expressions = ["COUNT(*) AS row_count", f"{len(schema)} AS column_count"]
    for column in schema[:6]:
        name = str(column.get("name") or "")
        alias = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "column"
        expressions.append(
            f"ROUND(SUM(CASE WHEN {_quote(name)} IS NULL THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS {alias}_missing_pct"
        )
    for name in _numeric_columns(schema)[:2]:
        alias = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        expressions.extend([
            f"MIN({_quote(name)}) AS {alias}_min",
            f"MAX({_quote(name)}) AS {alias}_max",
            f"ROUND(AVG({_quote(name)}), 2) AS {alias}_avg",
        ])
    return "SELECT " + ", ".join(expressions) + " FROM data"


def _deterministic_sql(strategy: str | None, schema: list[dict[str, Any]]) -> str | None:
    if not strategy:
        return None
    if strategy == "data_summary":
        return _summary_sql(schema)

    if strategy == "correlation":
        numeric = _numeric_columns(schema)[:5]
        pairs = [(numeric[i], numeric[j]) for i in range(len(numeric)) for j in range(i + 1, len(numeric))]
        if not pairs:
            return _summary_sql(schema)
        queries = [
            (
                f"SELECT '{left.replace(chr(39), chr(39) * 2)}' AS field_a, "
                f"'{right.replace(chr(39), chr(39) * 2)}' AS field_b, "
                f"ROUND(CORR(CAST({_quote(left)} AS DOUBLE), CAST({_quote(right)} AS DOUBLE)), 4) AS correlation FROM data"
            )
            for left, right in pairs
        ]
        return "SELECT * FROM (" + " UNION ALL ".join(queries) + ") pairs ORDER BY ABS(correlation) DESC LIMIT 10"

    measure = _measure_expression(schema)
    dimension = _business_dimension(schema)
    if strategy == "ranking" and measure and dimension:
        label, expression = measure
        return (
            f"WITH ranked AS (SELECT {_quote(dimension)} AS dimension, ROUND({expression}, 2) AS {label} "
            f"FROM data GROUP BY {_quote(dimension)}) "
            "SELECT * FROM ((SELECT 'top' AS rank_group, * FROM ranked ORDER BY " + label + " DESC LIMIT 10) "
            "UNION ALL (SELECT 'bottom' AS rank_group, * FROM ranked ORDER BY " + label + " ASC LIMIT 10)) combined"
        )

    if strategy == "trend" and measure:
        temporal = next((
            str(column.get("name")) for column in schema
            if _is_temporal(str(column.get("name") or ""), str(column.get("type") or ""))
        ), None)
        if temporal:
            label, expression = measure
            return (
                f"SELECT DATE_TRUNC('month', {_quote(temporal)}) AS month, ROUND({expression}, 2) AS {label} "
                f"FROM data GROUP BY month ORDER BY month"
            )

    return _summary_sql(schema)


def _deterministic_insight(previous_results: list[Any]) -> str:
    result = next((item for item in previous_results if isinstance(item, dict) and "rows" in item), None)
    if not result:
        return "### 结果摘要\n\n本次规则分析没有返回可展示的数据。"
    columns = result.get("columns") or []
    rows = result.get("rows") or []
    lines = ["### 结果摘要", "", f"- 查询返回 {result.get('row_count', len(rows))} 行结果。"]
    if rows:
        preview = "；".join(f"{column}：{rows[0][index]}" for index, column in enumerate(columns[:5]))
        lines.append(f"- 首行结果：{preview}。")
    lines.append("- 以上结论来自确定性 SQL，仅描述数据现象，不推断因果关系。")
    return "\n".join(lines)
