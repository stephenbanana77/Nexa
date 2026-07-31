"""Agent controller — LangGraph-based analysis pipeline."""
import asyncio
from typing import AsyncGenerator
from agents.graph import run_agent


class AgentController:
    """Orchestrates AI-powered data analysis using LangGraph.

    API-compatible with V0's hardcoded pipeline for drop-in replacement.
    """

    def __init__(self, project_id: str, user_question: str, history: list[dict] = None):
        self.project_id = project_id
        self.question = user_question
        self.history = history or []

    async def run(self) -> AsyncGenerator[dict, None]:
        """Run the LangGraph agent pipeline, yielding SSE events."""
        async for event in run_agent(self.project_id, self.question, self.history):
            yield event
