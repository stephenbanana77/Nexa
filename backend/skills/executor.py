"""Skill step executor — runs individual steps of a Skill."""
import asyncio
from typing import Any, AsyncGenerator
from agents.llm import achat
from agents.tools import execute_query, suggest_chart
from agents.context import get_schema_context
from database import SessionLocal
from models.project import Dataset
from services.dataset_tables import dataset_table_name
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
    dataset_id = params.get("dataset_id")
    if dataset_id:
        db = SessionLocal()
        try:
            dataset = db.query(Dataset).filter(
                Dataset.id == dataset_id,
                Dataset.project_id == project_id,
            ).first()
            if not dataset:
                raise ValueError("Dataset is not available in this project")
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
    """Execute a SQL step: LLM generates SQL → execute → return results."""
    prompt_template = step.get("prompt", "SELECT * FROM data LIMIT 10")
    schema = context["schema"]

    full_prompt = f"""You are a data analyst. Given the dataset schema, write a SQL query.

Schema:
{schema}

Task: {prompt_template}

Respond with ONLY the SQL query in a markdown code block. No explanation."""

    response = await achat([{"role": "user", "content": full_prompt}])

    # Extract SQL
    import re
    sql_match = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    sql = sql_match.group(1).strip() if sql_match else response.strip()

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
