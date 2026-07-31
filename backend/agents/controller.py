"""Agent controller - orchestrates the AI analysis pipeline."""
import asyncio
from typing import AsyncGenerator
from agents.executor import generate_sql, execute_sql, analyze_results


class AgentController:
    def __init__(self, project_id: str, user_question: str):
        self.project_id = project_id
        self.question = user_question

    async def run(self) -> AsyncGenerator[dict, None]:
        yield {"event": "understanding", "message": "Understanding your question...", "progress": 10}
        await asyncio.sleep(0.5)

        yield {"event": "planning", "message": "Planning analysis steps...", "progress": 20}
        await asyncio.sleep(0.3)

        yield {"event": "sql_generating", "message": "Generating SQL query...", "progress": 30}
        sql = generate_sql(self.project_id, self.question)

        yield {"event": "querying", "message": "Executing query...", "progress": 50, "sql": sql}
        results = execute_sql(self.project_id, sql)

        yield {"event": "analyzing", "message": f"Analyzing {results['row_count']} rows...", "progress": 70}
        summary = analyze_results(self.question, sql, results)

        yield {
            "event": "insight",
            "message": summary[:200],
            "progress": 95,
            "sql": sql,
            "columns": results["columns"],
            "rows": results["rows"][:50],
            "row_count": results["row_count"],
            "summary": summary,
        }

        yield {"event": "done", "message": "Analysis complete", "progress": 100}
