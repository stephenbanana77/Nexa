import json
import re
from agents.state import AgentState
from agents.llm import chat
from agents.tools import suggest_chart


def visualize(state: AgentState) -> dict:
    sql = state["sql"]
    result = state.get("query_result", {})

    chart = suggest_chart(sql, result)

    if not chart and result.get("rows"):
        columns = result.get("columns", [])
        prompt = f"""Given these query results, suggest an ECharts chart configuration.
Return ONLY valid JSON with "type", "title", "options".

Columns: {columns}
Sample rows: {result['rows'][:3]}
Row count: {result['row_count']}

Respond with ONLY the JSON, no markdown."""

        response = chat([{"role": "user", "content": prompt}])
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            chart = json.loads(json_match.group(0)) if json_match else None
        except Exception:
            chart = None

    return {"chart_config": chart, "next_action": "compose"}
