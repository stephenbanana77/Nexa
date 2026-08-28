import re
from agents.state import AgentState
from agents.llm import achat
from agents.prompts import SQL_GENERATION_PROMPT
import logging

logger = logging.getLogger(__name__)

from agents.tools import execute_query


async def generate_sql(state: AgentState) -> dict:
    schema = state["schema"]
    question = state["question"]
    plan = state.get("plan", [state["question"]])
    step_idx = state.get("current_step", 0)
    current_task = plan[step_idx] if step_idx < len(plan) else question
    error = state.get("sql_error", "")
    history = state.get("conversation_history", [])

    error_ctx = ""
    if error:
        error_ctx = f"\n\nPrevious SQL failed with error:\n{error}\nPlease fix the SQL and try again."

    history_ctx = ""
    if history:
        recent = history[-4:]
        history_ctx = "\n\nRecent conversation:\n" + "\n".join(
            f"{'User' if h['role'] == 'user' else 'Assistant'}: {h.get('content', '')[:200]}"
            for h in recent
        )

    prompt = SQL_GENERATION_PROMPT.format(
        schema=schema,
        question=f"{current_task}\n(Original question: {question}){history_ctx}{error_ctx}",
    )

    response = await achat([{"role": "user", "content": prompt}])
    sql_match = re.search(r"```sql\s*(.*?)```", response, re.DOTALL | re.IGNORECASE)
    sql = sql_match.group(1).strip() if sql_match else response.strip()

    return {
        "sql": sql,
        "sql_error": "",
        "next_action": "execute",
    }


def execute_sql(state: AgentState) -> dict:
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
        logger.warning(f"SQL execution failed (attempt {state.get('retry_count', 0)+1}): {e}")
        retry = state.get("retry_count", 0)
        if retry < 2:
            return {
                "sql_error": str(e),
                "retry_count": retry + 1,
                "next_action": "generate_sql",
            }
        return {
            "sql_error": str(e),
            "next_action": "compose",
        }
