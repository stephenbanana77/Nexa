"""LangGraph Agent state definition."""
from typing import TypedDict, Annotated, Any
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Input
    messages: Annotated[list[dict], add_messages]
    project_id: str
    question: str
    dataset_id: str | None
    input_row_count: int | None
    input_column_count: int | None
    intent: str

    # Context
    schema: str
    conversation_history: list[dict]

    # Analysis plan
    plan: list[str]
    current_step: int

    # SQL execution
    sql: str
    sql_error: str
    query_result: dict[str, Any]
    retry_count: int

    # Results
    analysis: str
    chart_config: dict[str, Any] | None
    summary: str

    # Skill
    selected_skill: str
    skill_output: dict[str, Any]

    # Flow control
    next_action: str  # "generate_sql" | "execute" | "analyze" | "visualize" | "compose" | "end" | "select_skill" | "execute_skill"
    capability_denied: bool
