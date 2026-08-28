"""Skill selection and execution nodes for LangGraph agent."""
from agents.state import AgentState
from skills import skill_registry
from skills.executor import execute_skill


SKILL_KEYWORDS = {
    "data_summary": ("概览", "摘要", "整体情况", "数据总结", "summary"),
    "correlation_analysis": ("相关性", "相关系数", "correlation"),
    "trend_analysis": ("趋势", "按月", "按季度", "环比", "同比", "trend"),
    "top_bottom_finder": ("排行", "排名", "最高", "最低", "top", "bottom", "前十", "后十"),
}


def select_skill(state: AgentState) -> dict:
    """Select an explicit analysis skill locally to avoid a routing LLM call."""
    question = state["question"].lower()
    available_skills = skill_registry.list_all()

    if not available_skills:
        return {"selected_skill": "", "next_action": "generate_sql"}

    available_names = {s["name"] for s in available_skills}
    for skill_name, keywords in SKILL_KEYWORDS.items():
        if skill_name in available_names and any(keyword in question for keyword in keywords):
            return {"selected_skill": skill_name, "next_action": "execute_skill"}

    return {"selected_skill": "", "next_action": "generate_sql"}


async def execute_skill_node(state: AgentState) -> dict:
    """Execute the selected skill and stream results."""
    skill_name = state["selected_skill"]
    project_id = state["project_id"]

    skill = skill_registry.get(skill_name)
    if not skill:
        return {"summary": f"Skill '{skill_name}' not found.", "next_action": "compose"}

    # Enforce permissions
    allowed, reason = skill_registry.check_permissions(skill_name, {
        "available_resources": ["schema", "data"],
        "allowed_writes": ["insight", "chart"],
        "llm_available": True,
    })
    if not allowed:
        return {"summary": reason, "next_action": "compose"}

    # Run the skill and accumulate results
    steps_output = []
    sql = ""
    chart_config = None
    summary = ""
    failure_message = ""

    async for event in execute_skill(
        skill,
        project_id,
        params={
            "dataset_id": state.get("dataset_id"),
            "input_row_count": state.get("input_row_count"),
            "input_column_count": state.get("input_column_count"),
        },
        schema_override=state.get("schema"),
    ):
        if event.get("event") in {"step_error", "skill_failed", "timeout"}:
            failure_message = event.get("message", "Skill execution failed")
        elif event.get("event") == "step_done":
            if event.get("type") == "sql":
                result = event.get("result", {})
                sql = result.get("sql", "")
                steps_output.append(result)
            elif event.get("type") == "visualize":
                chart_config = event.get("chart")
            elif event.get("type") == "insight":
                summary = event.get("insight", "")
                steps_output.append({"insight": summary})

    # Build query_result from the SQL step
    query_result = {}
    for s in steps_output:
        if "sql" in s:
            query_result = {
                "columns": s.get("columns", []),
                "rows": s.get("rows", []),
                "row_count": s.get("row_count", 0),
            }
            break

    if failure_message:
        return {
            "summary": f"Skill execution failed: {failure_message}",
            "analysis": "",
            "input_row_count": state.get("input_row_count"),
            "input_column_count": state.get("input_column_count"),
            "next_action": "compose",
        }

    return {
        "query_result": query_result,
        "sql": sql,
        "chart_config": chart_config,
        "summary": summary,
        "analysis": summary,
        "input_row_count": state.get("input_row_count"),
        "input_column_count": state.get("input_column_count"),
        "next_action": "compose",
    }
