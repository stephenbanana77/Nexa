"""Agent nodes — individual analysis steps."""

from agents.state import AgentState
from agents.llm import chat
from agents.prompts import SQL_GENERATION_PROMPT, ANALYSIS_PROMPT
from agents.tools import execute_query, suggest_chart
from agents.context import get_schema_context
import re


def understand_intent(state: AgentState) -> dict:
    """Analyze the user's question to determine what kind of analysis is needed."""
    question = state["question"]
    schema = state.get("schema", "")

    prompt = f"""You are a data analyst. Given a user question and dataset schema, output a JSON object with:
- "intent": one of ["query", "analysis", "comparison", "trend", "summary"]
- "entities": list of column names or concepts referenced
- "needs_sql": true/false

Schema:
{schema}

Question: {question}

Respond with ONLY valid JSON, no markdown, no explanation."""

    response = chat([{"role": "user", "content": prompt}])
    try:
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"\{[^}]+\}", response, re.DOTALL)
        intent_data = json.loads(json_match.group(0)) if json_match else {}
    except Exception:
        intent_data = {"intent": "analysis", "entities": [], "needs_sql": True}

    return {
        "next_action": "plan" if intent_data.get("needs_sql", True) else "compose",
        "schema": schema or get_schema_context(state["project_id"]),
    }


def plan_steps(state: AgentState) -> dict:
    """Plan the analysis steps based on the question."""
    question = state["question"]
    schema = state["schema"]

    prompt = f"""Plan the SQL analysis steps for this question. Output a JSON array of step descriptions.

Dataset schema:
{schema}

Question: {question}

Respond with ONLY a JSON array of strings, e.g.: ["Step 1", "Step 2"]
Keep it to 1-3 steps. If a single query answers it, output 1 step."""

    response = chat([{"role": "user", "content": prompt}])
    try:
        json_match = re.search(r"\[.*?\]", response, re.DOTALL)
        plan = json.loads(json_match.group(0)) if json_match else ["Analyze data"]
    except Exception:
        plan = ["Analyze data"]

    return {
        "plan": plan,
        "current_step": 0,
        "next_action": "generate_sql",
    }


def generate_sql(state: AgentState) -> dict:
    """Generate SQL query for the current analysis step."""
    schema = state["schema"]
    question = state["question"]
    plan = state.get("plan", [state["question"]])
    step_idx = state.get("current_step", 0)
    current_task = plan[step_idx] if step_idx < len(plan) else question
    error = state.get("sql_error", "")
    history = state.get("conversation_history", [])

    # Build prompt with error context if retrying
    error_ctx = ""
    if error:
        error_ctx = f"\n\nPrevious SQL failed with error:\n{error}\nPlease fix the SQL and try again."

    history_ctx = ""
    if history:
        recent = history[-4:]  # last 2 exchanges
        history_ctx = "\n\nRecent conversation:\n" + "\n".join(
            f"{'User' if h['role'] == 'user' else 'Assistant'}: {h.get('content', '')[:200]}"
            for h in recent
        )

    prompt = SQL_GENERATION_PROMPT.format(
        schema=schema,
        question=f"{current_task}\n(Original question: {question}){history_ctx}{error_ctx}",
    )

    response = chat([{"role": "user", "content": prompt}])

    # Extract SQL from response
    sql_match = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    sql = sql_match.group(1).strip() if sql_match else response.strip()

    return {
        "sql": sql,
        "sql_error": "",  # clear previous error
        "next_action": "execute",
    }


def execute_sql(state: AgentState) -> dict:
    """Execute the generated SQL query."""
    sql = state["sql"]
    project_id = state["project_id"]

    try:
        result = execute_query(project_id, sql)
        return {
            "query_result": result,
            "sql_error": "",
            "retry_count": 0,
            "next_action": "analyze",
        }
    except Exception as e:
        retry = state.get("retry_count", 0)
        if retry < 2:
            return {
                "sql_error": str(e),
                "retry_count": retry + 1,
                "next_action": "generate_sql",  # retry
            }
        return {
            "sql_error": str(e),
            "next_action": "compose",  # give up, explain error
        }


def analyze_result(state: AgentState) -> dict:
    """Analyze query results and generate insights."""
    question = state["question"]
    sql = state["sql"]
    result = state.get("query_result", {})
    result_preview = str(result.get("rows", [])[:10])[:2000]

    prompt = ANALYSIS_PROMPT.format(
        question=question,
        sql=sql,
        row_count=result.get("row_count", 0),
        results=result_preview,
    )

    analysis = chat([{"role": "user", "content": prompt}])

    return {
        "analysis": analysis,
        "next_action": "visualize",
    }


def visualize(state: AgentState) -> dict:
    """Generate chart configuration from query results."""
    sql = state["sql"]
    result = state.get("query_result", {})

    chart = suggest_chart(sql, result)

    # Also let AI suggest if auto-detection fails
    if not chart and result.get("rows"):
        columns = result.get("columns", [])
        prompt = f"""Given these query results, suggest an ECharts chart configuration.
Return ONLY valid JSON with "type", "title", "options".

Columns: {columns}
Sample rows: {result['rows'][:3]}
Row count: {result['row_count']}

Respond with ONLY the JSON, no markdown."""

        response = chat([{"role": "user", "content": prompt}])
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            chart = json.loads(json_match.group(0)) if json_match else None
        except Exception:
            chart = None

    return {
        "chart_config": chart,
        "next_action": "compose",
    }


def compose_answer(state: AgentState) -> dict:
    """Compose the final answer."""
    analysis = state.get("analysis", "")
    error = state.get("sql_error", "")

    if error and not analysis:
        summary = f"Could not execute the analysis. Error: {error}"
    elif analysis:
        summary = analysis
    else:
        summary = "Analysis complete."

    return {
        "summary": summary,
        "next_action": "end",
    }


# Need json at module level
import json
