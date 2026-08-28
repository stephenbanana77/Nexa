"""Regression tests for Agent latency and Skill runtime guards."""
import asyncio

import pytest

from agents.nodes.analyze import _get_confidence
from agents.nodes.skill import select_skill
from agents.controller import AgentController
from services.run_tracker import get_run_detail
from skills import skill_registry
from skills.executor import execute_skill
from utils.config import settings


def test_confidence_uses_source_rows_for_aggregated_results():
    confidence = _get_confidence(
        {
            "columns": ["region", "sales"],
            "rows": [["West", 100]],
            "row_count": 4,
        },
        input_row_count=9994,
    )

    assert confidence["confidence_label"].startswith("✅")
    assert "9994" in confidence["completeness_note"]
    assert "4" in confidence["completeness_note"]


def test_skill_selection_is_local_and_deterministic(monkeypatch):
    monkeypatch.setattr(
        skill_registry,
        "list_all",
        lambda: [{"name": "trend_analysis"}, {"name": "data_summary"}],
    )

    decision = select_skill({
        "question": "请按月分析销售额趋势",
        "project_id": "project",
    })

    assert decision == {"selected_skill": "trend_analysis", "next_action": "execute_skill"}


@pytest.mark.asyncio
async def test_skill_step_timeout_emits_failure(monkeypatch):
    async def slow_step(step, context):
        await asyncio.sleep(0.05)

    monkeypatch.setattr("skills.executor._execute_sql_step", slow_step)
    monkeypatch.setattr(settings, "SKILL_STEP_TIMEOUT_SEC", 0.01)

    events = [
        event async for event in execute_skill(
            {
                "name": "slow_skill",
                "title": "Slow Skill",
                "definition": {"steps": [{"type": "sql"}]},
            },
            "project-without-dataset",
        )
    ]

    names = [event["event"] for event in events]
    assert "step_error" in names
    assert "skill_failed" in names
    assert "skill_done" not in names


@pytest.mark.asyncio
async def test_agent_timeout_does_not_start_system_retries(monkeypatch, project_id):
    async def timed_out_agent(*args, **kwargs):
        yield {"event": "timeout", "message": "deadline exceeded"}

    monkeypatch.setattr("agents.controller.run_agent", timed_out_agent)

    controller = AgentController(project_id, "slow analysis")
    events = [event async for event in controller.run()]

    assert events == [{"event": "timeout", "message": "deadline exceeded"}]
    assert len(controller.run_ids) == 1
    assert get_run_detail(controller.run_ids[0])["status"] == "failed"
