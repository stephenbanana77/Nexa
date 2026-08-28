"""LangGraph-based analysis controller with run tracking and lineage."""
import asyncio
import hashlib
from typing import AsyncGenerator

from agents.context import get_schema_context
from agents.graph import run_agent
from agents.sanitizer import sanitize_schema, sanitize_user_input
from services.run_tracker import RunTracker
from services.sql_policy import inspect_sql_policy

MAX_RETRIES = 2
RETRY_BASE_DELAY = 2  # seconds: 2s then 4s


class AgentController:
    """Orchestrates AI-powered data analysis using LangGraph."""

    def __init__(
        self,
        project_id: str,
        user_question: str,
        history: list[dict] = None,
        user_id: str = None,
        dataset_id: str = None,
        schema_override: str = None,
        input_row_count: int | None = None,
        input_column_count: int | None = None,
    ):
        self.project_id = project_id
        self.question = user_question
        self.history = history or []
        self._user_id = user_id
        self._dataset_id = dataset_id
        self._schema_override = schema_override
        self._input_row_count = input_row_count
        self._input_column_count = input_column_count
        self.run_ids: list[str] = []

    async def run(self) -> AsyncGenerator[dict, None]:
        """Run the LangGraph agent pipeline with auto-retry on failure."""
        for attempt in range(MAX_RETRIES + 1):
            self.tracker = RunTracker(
                run_type="chat",
                project_id=self.project_id,
                created_by=self._user_id,
            )
            self.run_ids.append(self.tracker.start())
            tracker = self.tracker
            tracker.update_lineage(self._initial_lineage(attempt))

            step_ids: dict[str, str] = {}
            sql_attempt_count = 0
            node_map = {
                "understanding": "understand",
                "planning": "plan",
                "selecting_skill": "select_skill",
                "running_skill": "execute_skill",
                "sql_generating": "sql",
                "querying": "execute",
                "sql_retry": "execute",
                "sql_failed": "execute",
                "analyzing": "analyze",
                "visualizing": "visualize",
                "insight": "compose",
                "done": "compose",
            }
            token_estimate = 0
            run_failed = False

            try:
                async for event in run_agent(
                    self.project_id,
                    self.question,
                    self.history,
                    self._dataset_id,
                    schema_override=self._schema_override,
                    input_row_count=self._input_row_count,
                    input_column_count=self._input_column_count,
                ):
                    node_name = event.get("event", "")
                    if node_name == "timeout":
                        tracker.fail(event.get("message"))
                        yield event
                        return
                    step_key = node_name
                    if node_name in ("querying", "sql_retry", "sql_failed"):
                        step_key = f"{node_name}:{len(step_ids)}"

                    if node_name in node_map and step_key not in step_ids:
                        step_ids[step_key] = tracker.add_step(
                            node_map[node_name],
                            input_summary=self.question[:200] if node_name == "understanding" else None,
                        )
                        token_estimate += 200

                    tracked_type = node_map.get(node_name)
                    if tracked_type and step_key in step_ids:
                        sid = step_ids[step_key]
                        if node_name in ("querying", "sql_retry", "sql_failed"):
                            sql_attempt_count += 1
                            sql = event.get("sql")
                            policy_decision = inspect_sql_policy(sql)
                            if node_name == "sql_failed":
                                tracker.fail_step(sid, event.get("sql_error") or event.get("message") or "SQL execution failed")
                            else:
                                tracker.complete_step(sid, sql=sql)
                            tracker.update_lineage({
                                "sql_attempts": [{
                                    "attempt": sql_attempt_count,
                                    "sql": sql,
                                    "status": "failed" if node_name in ("sql_retry", "sql_failed") else "executed",
                                    "error": event.get("sql_error"),
                                    "retry_count": event.get("retry_count", 0),
                                    "policy": policy_decision.to_dict(),
                                }],
                                "latest_sql": policy_decision.final_sql or sql,
                                "policy_decision": policy_decision.to_dict(),
                                "sql_retries": [{
                                    "attempt": sql_attempt_count,
                                    "error": event.get("sql_error"),
                                    "next_action": "regenerate" if node_name == "sql_retry" else "compose",
                                }] if node_name in ("sql_retry", "sql_failed") else [],
                            })
                        elif node_name == "visualizing":
                            chart_config = event.get("chart_config")
                            tracker.complete_step(sid, chart_config=chart_config)
                            if chart_config:
                                tracker.update_lineage({"chart_config": chart_config})
                        elif node_name in ("insight", "done"):
                            tracker.complete_step(sid, output_summary=(event.get("message", "") or "")[:200])
                            if node_name == "insight":
                                token_estimate += 500
                                if str(event.get("summary", "")).startswith("Skill execution failed:"):
                                    run_failed = True
                                    tracker.fail(event.get("summary"))
                                tracker.update_lineage({
                                    "final_sql": event.get("sql"),
                                    "result": {
                                        "columns": event.get("columns", []),
                                        "row_count": event.get("row_count", 0),
                                        "source_row_count": event.get("total_rows"),
                                        "source_column_count": event.get("total_columns"),
                                        "sample_rows": event.get("rows", [])[:10],
                                    },
                                    "answer": {
                                        "summary": event.get("summary", ""),
                                        "preview": (event.get("message", "") or "")[:200],
                                    },
                                })
                        else:
                            tracker.complete_step(sid)

                    yield event

                if run_failed:
                    return
                tracker.complete(token_estimate=token_estimate)
                return

            except asyncio.CancelledError:
                tracker.fail("Analysis cancelled")
                raise
            except Exception as exc:
                # Retrying the whole Agent after a provider timeout multiplies
                # latency and can create several long-running model calls.
                if "timed out" in str(exc).lower() or "timeout" in str(exc).lower():
                    message = "LLM provider timed out; analysis was stopped without a full-pipeline retry."
                    tracker.fail(message)
                    yield {"event": "timeout", "message": message, "progress": 100}
                    return
                tracker.update_lineage({
                    "system_retries": [{
                        "attempt": attempt + 1,
                        "message": str(exc),
                        "will_retry": attempt < MAX_RETRIES,
                    }],
                    "errors": [{"type": "system", "attempt": attempt + 1, "message": str(exc)}],
                })
                tracker.fail(str(exc))
                if attempt < MAX_RETRIES:
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    yield {"event": "retry", "attempt": attempt + 1, "delay": delay, "error": str(exc)[:100]}
                    await asyncio.sleep(delay)
                else:
                    raise

    def _initial_lineage(self, attempt: int) -> dict:
        clean_question, question_sanitized = sanitize_user_input(self.question)
        raw_schema = self._schema_override or get_schema_context(self.project_id, self._dataset_id)
        schema = sanitize_schema(raw_schema)
        return {
            "question": clean_question,
            "question_sanitized": question_sanitized,
            "project_id": self.project_id,
            "dataset_id": self._dataset_id,
            "input_row_count": self._input_row_count,
            "input_column_count": self._input_column_count,
            "attempt": attempt + 1,
            "schema": {
                "text": schema,
                "sha256": hashlib.sha256(schema.encode("utf-8")).hexdigest(),
                "length": len(schema),
                "source": "override" if self._schema_override else "project",
            },
            "sql_attempts": [],
            "errors": [],
        }
