"""Agent controller — LangGraph-based analysis pipeline with run tracking + retry."""
import asyncio
from typing import AsyncGenerator
from agents.graph import run_agent
from services.run_tracker import RunTracker

MAX_RETRIES = 2
RETRY_BASE_DELAY = 2  # seconds: 2s then 4s


class AgentController:
    """Orchestrates AI-powered data analysis using LangGraph.

    API-compatible with V0's hardcoded pipeline for drop-in replacement.
    """

    def __init__(self, project_id: str, user_question: str, history: list[dict] = None, user_id: str = None):
        self.project_id = project_id
        self.question = user_question
        self.history = history or []
        self.tracker = RunTracker(run_type="chat", project_id=project_id, created_by=user_id)

    async def run(self) -> AsyncGenerator[dict, None]:
        """Run the LangGraph agent pipeline with auto-retry on failure."""
        last_error = None

        for attempt in range(MAX_RETRIES + 1):
            self.tracker.start()
            tracker = self.tracker
            step_ids: dict[str, str] = {}
            node_map = {
                "understanding": "understand", "planning": "plan",
                "selecting_skill": "select_skill", "running_skill": "execute_skill",
                "sql_generating": "sql", "querying": "execute",
                "analyzing": "analyze", "visualizing": "visualize",
                "insight": "compose", "done": "compose",
            }
            token_estimate = 0

            try:
                async for event in run_agent(self.project_id, self.question, self.history):
                    node_name = event.get("event", "")
                    if node_name in node_map and node_name not in step_ids:
                        step_ids[node_name] = tracker.add_step(
                            node_map[node_name],
                            input_summary=self.question[:200] if node_name == "understand" else None,
                        )
                        token_estimate += 200

                    tracked_type = node_map.get(node_name)
                    if tracked_type and node_name in step_ids:
                        sid = step_ids[node_name]
                        if node_name == "querying":
                            tracker.complete_step(sid, sql=event.get("sql"))
                        elif node_name == "visualizing":
                            tracker.complete_step(sid, chart_config=event.get("chart_config"))
                        elif node_name in ("insight", "done"):
                            tracker.complete_step(sid, output_summary=(event.get("message", "") or "")[:200])
                            if node_name == "insight":
                                token_estimate += 500
                        else:
                            tracker.complete_step(sid)
                    yield event

                tracker.complete(token_estimate=token_estimate)
                return  # success — exit retry loop

            except Exception as e:
                last_error = e
                tracker.fail(str(e))
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    yield {"event": "retry", "attempt": attempt + 1, "delay": delay, "error": str(e)[:100]}
                    await asyncio.sleep(delay)
                else:
                    raise
