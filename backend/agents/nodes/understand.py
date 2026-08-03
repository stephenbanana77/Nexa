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

    prompt = f"""你是一个数据分析师。根据用户问题和数据集 schema，输出一个 JSON 对象，包含：
- "intent": 取值为 ["query", "analysis", "comparison", "trend", "summary"] 之一
- "entities": 引用到的列名或概念列表
- "needs_sql": true/false

Schema：
{schema}

问题：{question}

只返回有效的 JSON，不要 markdown，不要解释。"""

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
