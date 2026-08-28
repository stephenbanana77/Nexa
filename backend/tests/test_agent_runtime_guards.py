"""Regression tests for Agent latency and Skill runtime guards."""
import asyncio

import pytest

from agents.nodes.analyze import _get_confidence
from agents.nodes.skill import select_skill
from agents.tools import suggest_chart
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


def test_lowest_word_does_not_force_ranking_skill(monkeypatch):
    monkeypatch.setattr(
        skill_registry,
        "list_all",
        lambda: [{"name": "top_bottom_finder"}],
    )

    decision = select_skill({
        "question": "请指出利润率最低的区域",
        "project_id": "project",
    })

    assert decision == {"selected_skill": "", "next_action": "generate_sql"}


def test_chart_suggestion_handles_multiple_numeric_columns_without_llm():
    chart = suggest_chart("", {
        "columns": ["region", "sales", "profit", "margin", "status"],
        "rows": [
            ["East", 100, 20, 0.2, "positive"],
            ["West", 200, 50, 0.25, "positive"],
        ],
        "row_count": 2,
    })

    assert chart["type"] == "bar"
    assert [series["name"] for series in chart["options"]["series"]] == ["sales", "profit", "margin"]


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


@pytest.mark.asyncio
async def test_provider_timeout_does_not_retry_full_pipeline(monkeypatch, project_id):
    async def provider_timeout(*args, **kwargs):
        raise RuntimeError("Request timed out.")
        yield  # pragma: no cover

    monkeypatch.setattr("agents.controller.run_agent", provider_timeout)

    controller = AgentController(project_id, "provider timeout")
    events = [event async for event in controller.run()]

    assert events[0]["event"] == "timeout"
    assert len(controller.run_ids) == 1
    assert get_run_detail(controller.run_ids[0])["status"] == "failed"
