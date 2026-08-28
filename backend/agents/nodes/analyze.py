from agents.state import AgentState
from agents.llm import achat
from agents.prompts import ANALYSIS_PROMPT, CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW


def _get_confidence(result: dict, input_row_count: int | None = None) -> dict:
    """Build confidence metadata from query results."""
    result_row_count = result.get("row_count", 0)
    source_row_count = input_row_count if input_row_count is not None else result_row_count
    columns = result.get("columns", [])
    rows = result.get("rows", [])

    # Check for missing values
    missing_count = 0
    if rows:
        for row in rows[:100]:  # sample first 100 rows
            for val in row:
                if val is None or val == "":
                    missing_count += 1

    if result_row_count == 0:
        return {
            "completeness_note": "查询返回 0 行",
            "confidence_label": CONFIDENCE_LOW,
            "confidence_note": "无数据",
        }
    elif source_row_count < 10:
        return {
            "completeness_note": f"原始数据 {source_row_count} 行，查询结果 {result_row_count} 行",
            "confidence_label": CONFIDENCE_LOW,
            "confidence_note": "样本量过小，结论仅供参考",
        }
    elif missing_count > 0:
        return {
            "completeness_note": f"原始数据 {source_row_count} 行，查询结果 {result_row_count} 行（检测到缺失值）",
            "confidence_label": CONFIDENCE_MEDIUM,
            "confidence_note": "部分字段存在缺失值，结论有一定参考价值",
        }
    else:
        return {
            "completeness_note": f"原始数据 {source_row_count} 行，查询结果 {result_row_count} 行，{len(columns)} 列",
            "confidence_label": CONFIDENCE_HIGH,
            "confidence_note": f"基于原始数据 {source_row_count} 行的聚合结果，结果可靠",
        }


async def analyze_result(state: AgentState) -> dict:
    question = state["question"]
    sql = state["sql"]
    result = state.get("query_result", {})
    result_preview = str(result.get("rows", [])[:10])[:2000]

    confidence = _get_confidence(result, state.get("input_row_count"))

    prompt = ANALYSIS_PROMPT.format(
        question=question,
        sql=sql,
        row_count=result.get("row_count", 0),
        col_count=len(result.get("columns", [])),
        results=result_preview,
        completeness_note=confidence["completeness_note"],
        confidence_label=confidence["confidence_label"],
        confidence_note=confidence["confidence_note"],
    )

    analysis = await achat([{"role": "user", "content": prompt}])
    return {"analysis": analysis, "next_action": "visualize"}
