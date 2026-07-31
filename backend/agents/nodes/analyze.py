from agents.state import AgentState
from agents.llm import chat
from agents.prompts import ANALYSIS_PROMPT


def analyze_result(state: AgentState) -> dict:
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
    return {"analysis": analysis, "next_action": "visualize"}
