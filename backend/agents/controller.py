"""Agent controller — LangGraph-based analysis pipeline with run tracking."""
from typing import AsyncGenerator
from agents.graph import run_agent
from services.run_tracker import RunTracker


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
        """Run the LangGraph agent pipeline with run tracking, yielding SSE events."""
        self.tracker.start()
        tracker = self.tracker

        step_ids: dict[str, str] = {}
        node_map = {
            "understanding": "understand",
            "planning": "plan",
            "selecting_skill": "select_skill",
            "running_skill": "execute_skill",
            "sql_generating": "sql",
            "querying": "execute",
            "analyzing": "analyze",
            "visualizing": "visualize",
            "insight": "compose",
            "done": "compose",
        }

        token_estimate = 0

        try:
            async for event in run_agent(self.project_id, self.question, self.history):
                node_name = event.get("event", "")

                # Create step on first occurrence
                if node_name in node_map and node_name not in step_ids:
                    step_ids[node_name] = tracker.add_step(
                        node_map[node_name],
                        input_summary=self.question[:200] if node_name == "understand" else None,
                    )
                    token_estimate += 200  # rough per-node estimate

                # Track outputs — use node_name as the step_ids key
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

        except Exception as e:
            tracker.fail(str(e))
            raise
