"""Tool executor for SQL generation and data analysis."""
import re
from tools import get_engine
from agents.llm import chat
from agents.prompts import SQL_GENERATION_PROMPT, ANALYSIS_PROMPT
from agents.context import get_schema_context


def extract_sql(text: str) -> str | None:
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def generate_sql(project_id: str, question: str) -> str:
    schema = get_schema_context(project_id)
    prompt = SQL_GENERATION_PROMPT.format(schema=schema, question=question)
    response = chat([{"role": "user", "content": prompt}])
    sql = extract_sql(response)
    if not sql:
        raise ValueError(f"Failed to extract SQL from LLM response: {response[:200]}")
    return sql


def execute_sql(project_id: str, sql: str) -> dict:
    engine = get_engine(project_id)
    return engine.query(sql)


def analyze_results(question: str, sql: str, results: dict) -> str:
    result_preview = str(results["rows"][:10])[:2000]
    prompt = ANALYSIS_PROMPT.format(
        question=question,
        sql=sql,
        row_count=results["row_count"],
        results=result_preview,
    )
    return chat([{"role": "user", "content": prompt}])
