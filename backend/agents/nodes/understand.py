from agents.state import AgentState
from agents.context import get_schema_context


def understand_intent(state: AgentState) -> dict:
    """Classify obvious intent locally; routing does not need an LLM round-trip."""
    question = state["question"].lower()
    schema = state.get("schema", "")
    if not schema:
        schema = get_schema_context(state["project_id"])

    intent = "query"
    if any(token in question for token in ("趋势", "按月", "按季度", "环比", "同比", "trend")):
        intent = "trend"
    elif any(token in question for token in ("对比", "比较", "差异", "comparison")):
        intent = "comparison"
    elif any(token in question for token in ("概览", "摘要", "总结", "summary")):
        intent = "summary"
    elif any(token in question for token in ("分析", "为什么", "异常", "analysis")):
        intent = "analysis"

    return {
        "schema": schema,
        "intent": intent,
        "next_action": "plan",
    }
