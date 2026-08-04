from agents.state import AgentState


def compose_answer(state: AgentState) -> dict:
    # Check if a summary was already set (e.g. capability denial)
    existing = state.get("summary", "")
    if existing:
        return {"summary": existing, "next_action": "end"}

    analysis = state.get("analysis", "")
    error = state.get("sql_error", "")

    if error and not analysis:
        summary = f"Could not execute the analysis. Error: {error}"
    elif analysis:
        summary = analysis
    else:
        summary = "Analysis complete."

    return {"summary": summary, "next_action": "end"}
