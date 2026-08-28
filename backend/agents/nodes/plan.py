from agents.state import AgentState
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

    # Keep the plan shape for lineage; SQL generation is the only model call on
    # the normal one-question path.
    plan = [question]
    return {
        "plan": plan,
        "current_step": 0,
        "next_action": "generate_sql",
    }
