import json
import re
from agents.state import AgentState
from agents.llm import achat
from agents.tools import suggest_chart


async def visualize(state: AgentState) -> dict:
    sql = state["sql"]
    result = state.get("query_result", {})

    chart = suggest_chart(sql, result)

    if not chart and result.get("rows"):
        columns = result.get("columns", [])
        prompt = f"""根据以下查询结果，推荐一个 ECharts 图表配置。
只返回有效 JSON，包含 "type"（图表类型）、"title"（中文标题）、"options"（ECharts 配置项）。

列名：{columns}
示例数据：{result['rows'][:3]}
行数：{result['row_count']}

只返回 JSON，不要 markdown。"""

        response = await achat([{"role": "user", "content": prompt}])
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            chart = json.loads(json_match.group(0)) if json_match else None
        except Exception:
            chart = None

    return {"chart_config": chart, "next_action": "compose"}
