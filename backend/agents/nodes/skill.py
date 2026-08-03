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

    prompt = f"""你是一个数据分析路由器。根据用户问题和可用技能，决定：

1. 这个问题是否应该使用技能？（技能是预置的分析流水线）
2. 哪个技能最匹配？

可用技能：
{skill_list}

用户问题：{question}

规则：
- 如果问题涉及概览/摘要/相关性/趋势/排行榜，选择匹配的技能
- 如果是简单查询（如"显示X"、"过滤Y"），回复 "none"
- 只返回 JSON：{{"use_skill": true/false, "skill_name": "xxx"}} 或 {{"use_skill": false}}

只返回有效 JSON，不要 markdown。"""

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
