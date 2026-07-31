import json
import re
from agents.state import AgentState
from agents.llm import chat
from agents.context import get_schema_context


def understand_intent(state: AgentState) -> dict:
    question = state["question"]
    schema = state.get("schema", "")
    if not schema:
        schema = get_schema_context(state["project_id"])

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
        json_match = re.search(r"\{[^}]+\}", response, re.DOTALL)
        intent_data = json.loads(json_match.group(0)) if json_match else {}
    except Exception:
        intent_data = {"intent": "analysis", "entities": [], "needs_sql": True}

    return {
        "schema": schema,
        "next_action": "plan",
    }
