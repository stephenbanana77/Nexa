"""Skill selection and execution nodes for LangGraph agent."""
import json
import re
from agents.state import AgentState
from agents.llm import chat
from skills import skill_registry
from skills.executor import execute_skill


def select_skill(state: AgentState) -> dict:
    """AI decides which skill (if any) matches the user's question."""
    question = state["question"]
    available_skills = skill_registry.list_all()

    if not available_skills:
        return {"selected_skill": "", "next_action": "generate_sql"}

    skill_list = "\n".join(
        f"- {s['name']}: {s['title']} — {s.get('description', '')}"
        for s in available_skills
    )

    prompt = f"""You are a data analysis router. Given a user question and available skills, decide:

1. Should this question use a skill? (Skills are pre-built analysis pipelines)
2. Which skill is the best match?

Available skills:
{skill_list}

User question: {question}

Rules:
- If the question asks for overview/summary/correlation/trend/rankings, select the matching skill
- If the question is a simple query (e.g., "show me X", "filter by Y"), respond with "none"
- Respond with ONLY a JSON: {{"use_skill": true/false, "skill_name": "xxx"}} or {{"use_skill": false}}

Respond with ONLY valid JSON, no markdown."""

    response = chat([{"role": "user", "content": prompt}])
    try:
        json_match = re.search(r"\{[^}]+\}", response, re.DOTALL)
        decision = json.loads(json_match.group(0)) if json_match else {}
    except Exception:
        decision = {}

    if decision.get("use_skill") and decision.get("skill_name"):
        skill = skill_registry.get(decision["skill_name"])
        if skill:
            return {"selected_skill": decision["skill_name"], "next_action": "execute_skill"}

    return {"selected_skill": "", "next_action": "generate_sql"}


async def execute_skill_node(state: AgentState) -> dict:
    """Execute the selected skill and stream results."""
    skill_name = state["selected_skill"]
    project_id = state["project_id"]

    skill = skill_registry.get(skill_name)
    if not skill:
        return {"summary": f"Skill '{skill_name}' not found.", "next_action": "compose"}

    # Run the skill and accumulate results
    steps_output = []
    sql = ""
    chart_config = None
    summary = ""

    async for event in execute_skill(skill, project_id):
        if event.get("event") == "step_done":
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

    return {
        "query_result": query_result,
        "sql": sql,
        "chart_config": chart_config,
        "summary": summary,
        "analysis": summary,
        "next_action": "compose",
    }
