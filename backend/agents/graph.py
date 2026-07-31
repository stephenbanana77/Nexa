"""LangGraph Agent — dynamic data analysis pipeline."""
import asyncio
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
from agents.context import get_schema_context


def route_after_execute(state: AgentState) -> str:
    """Route after SQL execution: retry on error, analyze on success, compose on final failure."""
    return state.get("next_action", "analyze")


def build_agent_graph() -> StateGraph:
    """Build and compile the LangGraph agent."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("understand", understand_intent)
    workflow.add_node("plan", plan_steps)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("execute", execute_sql)
    workflow.add_node("analyze", analyze_result)
    workflow.add_node("visualize", visualize)
    workflow.add_node("compose", compose_answer)

    # Edges
    workflow.set_entry_point("understand")
    workflow.add_edge("understand", "plan")
    workflow.add_edge("plan", "generate_sql")
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


async def run_agent(project_id: str, question: str, history: list[dict] = None) -> AsyncGenerator[dict[str, Any], None]:
    """Run the LangGraph agent and yield streaming events."""
    schema = get_schema_context(project_id)

    initial_state: AgentState = {
        "messages": [],
        "project_id": project_id,
        "question": question,
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
        "next_action": "",
    }

    # Map of node names to SSE event names
    node_events = {
        "understand": ("understanding", "Understanding your question..."),
        "plan": ("planning", "Planning analysis steps..."),
        "generate_sql": ("sql_generating", "Generating SQL query..."),
        "execute": ("querying", "Executing query..."),
        "analyze": ("analyzing", "Analyzing results..."),
        "visualize": ("visualizing", "Generating charts..."),
        "compose": ("done", "Analysis complete"),
    }

    current_state: dict = dict(initial_state)

    async for event in _agent_graph.astream(initial_state, stream_mode="updates"):
        for node_name, node_state in event.items():
            # Update current state
            current_state.update(node_state)

            if node_name in node_events:
                event_name, message = node_events[node_name]

                # Build event data based on node
                event_data = {"event": event_name, "message": message}

                if node_name == "execute":
                    event_data["sql"] = current_state.get("sql", "")
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
                    # Final result event
                    result = current_state.get("query_result", {})
                    event_data = {
                        "event": "insight",
                        "message": (current_state.get("summary", "") or "")[:200],
                        "progress": 95,
                        "sql": current_state.get("sql", ""),
                        "columns": result.get("columns", []),
                        "rows": result.get("rows", [])[:50],
                        "row_count": result.get("row_count", 0),
                        "summary": current_state.get("summary", ""),
                        "charts": [current_state["chart_config"]] if current_state.get("chart_config") else [],
                    }

                yield event_data

    # Always send done event at the end
    yield {"event": "done", "message": "Analysis complete", "progress": 100}
