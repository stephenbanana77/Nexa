"""LangGraph Agent — dynamic data analysis pipeline with Skill support."""
from typing import Any, AsyncGenerator
from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.nodes import (
    understand_intent,
    plan_steps,
    generate_sql,
    execute_sql,
    analyze_result,
    visualize,
    compose_answer,
)
from agents.nodes.skill import select_skill, execute_skill_node
from agents.context import get_schema_context


def route_after_plan(state: AgentState) -> str:
    """After planning: go to compose if capability denied, otherwise select_skill."""
    if state.get("capability_denied"):
        return "compose"
    return "select_skill"


def route_after_select(state: AgentState) -> str:
    """After skill selection, route to skill execution or normal SQL flow."""
    return state.get("next_action", "generate_sql")


def route_after_execute(state: AgentState) -> str:
    """Route after SQL execution: retry on error, analyze on success, compose on final failure."""
    return state.get("next_action", "analyze")


def build_agent_graph() -> StateGraph:
    """Build and compile the LangGraph agent."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("understand", understand_intent)
    workflow.add_node("plan", plan_steps)
    workflow.add_node("select_skill", select_skill)
    workflow.add_node("execute_skill", execute_skill_node)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("execute", execute_sql)
    workflow.add_node("analyze", analyze_result)
    workflow.add_node("visualize", visualize)
    workflow.add_node("compose", compose_answer)

    # Edges
    workflow.set_entry_point("understand")
    workflow.add_edge("understand", "plan")

    # plan → select_skill (AI decides if skill matches) or compose (capability denied)
    workflow.add_conditional_edges(
        "plan",
        route_after_plan,
        {"select_skill": "select_skill", "compose": "compose"}
    )

    # select_skill → execute_skill (if matched) or generate_sql (fallback)
    workflow.add_conditional_edges(
        "select_skill",
        route_after_select,
        {"execute_skill": "execute_skill", "generate_sql": "generate_sql"}
    )

    # execute_skill → compose (skill handles its own analysis internally)
    workflow.add_edge("execute_skill", "compose")

    workflow.add_edge("generate_sql", "execute")

    # execute → retry if error, or proceed to analyze
    workflow.add_conditional_edges(
        "execute",
        route_after_execute,
        {"generate_sql": "generate_sql", "analyze": "analyze", "compose": "compose"}
    )

    workflow.add_edge("analyze", "visualize")
    workflow.add_edge("visualize", "compose")
    workflow.add_edge("compose", END)

    return workflow.compile()


# Singleton
_agent_graph = build_agent_graph()


async def run_agent(
    project_id: str,
    question: str,
    history: list[dict] = None,
    dataset_id: str = None,
    schema_override: str = None,
    input_row_count: int | None = None,
    input_column_count: int | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Run the LangGraph agent and yield streaming events."""
    import asyncio
    from utils.config import settings
    from agents.sanitizer import sanitize_user_input, sanitize_schema

    clean_question, was_flagged = sanitize_user_input(question)
    if schema_override:
        schema = sanitize_schema(schema_override)
    else:
        schema = get_schema_context(project_id, dataset_id)
        schema = sanitize_schema(schema)

    initial_state: AgentState = {
        "messages": [],
        "project_id": project_id,
        "question": clean_question,
        "dataset_id": dataset_id,
        "input_row_count": input_row_count,
        "input_column_count": input_column_count,
        "intent": "query",
        "schema": schema,
        "conversation_history": history or [],
        "plan": [],
        "current_step": 0,
        "sql": "",
        "sql_error": "",
        "query_result": {},
        "retry_count": 0,
        "analysis": "",
        "chart_config": None,
        "summary": "",
        "selected_skill": "",
        "skill_output": {},
        "next_action": "",
    }

    node_events = {
        "understand": ("understanding", "Understanding your question..."),
        "plan": ("planning", "Planning analysis steps..."),
        "select_skill": ("selecting_skill", "Selecting best analysis skill..."),
        "execute_skill": ("running_skill", "Running skill analysis..."),
        "generate_sql": ("sql_generating", "Generating SQL query..."),
        "execute": ("querying", "Executing query..."),
        "analyze": ("analyzing", "Analyzing results..."),
        "visualize": ("visualizing", "Generating charts..."),
        "compose": ("done", "Analysis complete"),
    }

    current_state: dict = dict(initial_state)

    try:
        async with asyncio.timeout(settings.AGENT_TIMEOUT_SEC):
            async for event in _agent_graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_state in event.items():
                    current_state.update(node_state)

                    if node_name in node_events:
                        event_name, message = node_events[node_name]

                        event_data = {"event": event_name, "message": message}

                        if node_name == "execute_skill":
                            event_data["progress"] = 40
                            event_data["skill"] = current_state.get("selected_skill", "")

                        elif node_name == "execute":
                            event_data["sql"] = current_state.get("sql", "")
                            if current_state.get("sql_error"):
                                event_data["sql_error"] = current_state.get("sql_error", "")
                                event_data["retry_count"] = current_state.get("retry_count", 0)
                                if current_state.get("next_action") == "generate_sql":
                                    event_data["event"] = "sql_retry"
                                    event_data["message"] = "SQL failed; regenerating query..."
                                elif current_state.get("next_action") == "compose":
                                    event_data["event"] = "sql_failed"
                                    event_data["message"] = current_state.get("sql_error", "")
                            event_data["progress"] = 50

                        elif node_name == "analyze":
                            err = current_state.get("sql_error", "")
                            if err:
                                event_data["event"] = "error"
                                event_data["message"] = err
                            event_data["progress"] = 70

                        elif node_name == "visualize":
                            event_data["chart_config"] = current_state.get("chart_config")
                            event_data["progress"] = 85

                        elif node_name == "compose":
                            result = current_state.get("query_result", {})
                            event_data = {
                                "event": "insight",
                                "message": (current_state.get("summary", "") or "")[:200],
                                "progress": 95,
                                "sql": current_state.get("sql", ""),
                                "columns": result.get("columns", []),
                                "rows": result.get("rows", [])[:50],
                                "row_count": result.get("row_count", 0),
                                "total_rows": current_state.get("input_row_count"),
                                "total_columns": current_state.get("input_column_count"),
                                "summary": current_state.get("summary", ""),
                                "charts": [current_state["chart_config"]] if current_state.get("chart_config") else [],
                            }

                        yield event_data

        yield {"event": "done", "message": "Analysis complete", "progress": 100}
    except TimeoutError:
        yield {
            "event": "timeout",
            "message": f"Analysis exceeded the {settings.AGENT_TIMEOUT_SEC}s deadline.",
            "progress": 100,
        }
