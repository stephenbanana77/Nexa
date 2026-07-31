import json
import re
from agents.state import AgentState
from agents.llm import chat


def plan_steps(state: AgentState) -> dict:
    question = state["question"]
    schema = state.get("schema", "")

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
