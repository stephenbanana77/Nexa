import json
import re
from agents.state import AgentState
from agents.llm import chat
from agents.prompts import CAPABILITY_DENIAL


PREDICTIVE_KEYWORDS = [
    "预测", "预计", "预估", "将来", "未来", "下周", "下个月", "明年",
    "forecast", "predict", "prescribe", "recommend", "建议策略",
    "会怎么样", "会怎样", "将会", "趋势预测",
    "因果", "导致", "原因是什么", "为什么下降", "影响因素",
]


def _is_predictive(question: str) -> bool:
    lower = question.lower()
    return any(kw in lower for kw in PREDICTIVE_KEYWORDS)


def plan_steps(state: AgentState) -> dict:
    question = state["question"]
    schema = state.get("schema", "")

    # Capability boundary check: redirect predictive/causal questions
    if _is_predictive(question):
        return {
            "plan": [question],
            "current_step": 0,
            "next_action": "compose",
            "summary": CAPABILITY_DENIAL,
            "capability_denied": True,
        }

    prompt = f"""为以下问题规划 SQL 分析步骤。输出一个 JSON 字符串数组。

数据集 schema：
{schema}

问题：{question}

只返回 JSON 字符串数组，如：["步骤1", "步骤2"]
保持 1-3 步。如果单条 SQL 能回答，只输出 1 步。"""

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
