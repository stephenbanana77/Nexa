"""Skill step executor — runs individual steps of a Skill."""
import asyncio
from typing import Any, AsyncGenerator
from agents.llm import chat
from agents.tools import execute_query, suggest_chart
from agents.context import get_schema_context


async def execute_skill(skill: dict, project_id: str, params: dict = None) -> AsyncGenerator[dict[str, Any], None]:
    """Execute a skill step by step, yielding progress events."""
    params = params or {}
    definition = skill.get("definition", {})
    steps = definition.get("steps", [])
    schema = get_schema_context(project_id)
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
                result = await _execute_sql_step(step, context)
                context["previous_results"].append(result)
                yield {"event": "step_done", "step": i + 1, "type": "sql", "result": result}

            elif step_type == "visualize":
                prev = context["previous_results"][-1] if context["previous_results"] else {}
                chart = await _execute_visualize_step(step, prev)
                context["previous_results"].append(chart)
                yield {"event": "step_done", "step": i + 1, "type": "visualize", "chart": chart}

            elif step_type == "insight":
                prev = context["previous_results"]
                insight = await _execute_insight_step(step, prev, context)
                yield {"event": "step_done", "step": i + 1, "type": "insight", "insight": insight}

            elif step_type == "python":
                # Deferred: Python sandbox execution
                yield {"event": "step_done", "step": i + 1, "type": "python", "message": "Python execution not yet supported"}

            else:
                yield {"event": "step_skip", "step": i + 1, "message": f"Unknown step type: {step_type}"}

            await asyncio.sleep(0.3)

        except Exception as e:
            yield {"event": "step_error", "step": i + 1, "message": str(e)}

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

    response = chat([{"role": "user", "content": full_prompt}])

    # Extract SQL
    import re
    sql_match = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    sql = sql_match.group(1).strip() if sql_match else response.strip()

    result = execute_query(context["project_id"], sql)
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

    return chat([{"role": "user", "content": full_prompt}])
