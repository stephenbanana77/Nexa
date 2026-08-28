"""Run lineage tests."""
import pytest

from agents.controller import AgentController
from services.run_tracker import get_run_detail
from services.run_tracker import RunTracker


def test_run_tracker_records_lineage(client, auth_headers, project_id):
    tracker = RunTracker(run_type="chat", project_id=project_id)
    run_id = tracker.start()
    tracker.update_lineage({
        "question": "Show top products",
        "schema": {"text": "TABLE data (product TEXT, sales INT)", "sha256": "abc"},
        "sql_attempts": [{"attempt": 1, "sql": "SELECT * FROM data LIMIT 10"}],
    })
    tracker.update_lineage({
        "final_sql": "SELECT * FROM data LIMIT 10",
        "result": {"columns": ["product", "sales"], "row_count": 2, "sample_rows": [["A", 10]]},
        "answer": {"summary": "A leads sales."},
    })
    tracker.complete(token_estimate=123)

    resp = client.get(f"/api/runs/detail/{run_id}", headers=auth_headers)
    assert resp.status_code == 200
    lineage = resp.json()["lineage"]
    assert lineage["question"] == "Show top products"
    assert lineage["schema"]["sha256"] == "abc"
    assert lineage["sql_attempts"][0]["sql"] == "SELECT * FROM data LIMIT 10"
    assert lineage["final_sql"] == "SELECT * FROM data LIMIT 10"
    assert lineage["result"]["row_count"] == 2
    assert lineage["answer"]["summary"] == "A leads sales."


def test_run_history_includes_lineage_summary(client, auth_headers, project_id):
    tracker = RunTracker(run_type="chat", project_id=project_id)
    tracker.start()
    tracker.update_lineage({
        "question": "Revenue by region",
        "final_sql": "SELECT region, SUM(revenue) FROM data GROUP BY region LIMIT 10000",
        "sql_attempts": [{"attempt": 1, "sql": "SELECT region, SUM(revenue) FROM data GROUP BY region LIMIT 10000"}],
        "result": {"row_count": 3},
    })
    tracker.complete()

    resp = client.get(f"/api/runs/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    lineage = resp.json()[0]["lineage"]
    assert lineage["question"] == "Revenue by region"
    assert lineage["row_count"] == 3
    assert lineage["sql_attempt_count"] == 1
    assert lineage["error_count"] == 0


@pytest.mark.asyncio
async def test_agent_controller_persists_analysis_lineage(monkeypatch, project_id):
    async def fake_run_agent(*args, **kwargs):
        yield {"event": "understanding", "message": "Understanding"}
        yield {"event": "querying", "sql": "SELECT * FROM data LIMIT 10"}
        yield {
            "event": "insight",
            "message": "Done",
            "sql": "SELECT * FROM data LIMIT 10",
            "columns": ["name"],
            "rows": [["A"]],
            "row_count": 1,
            "summary": "A is the top item.",
        }
        yield {"event": "done", "message": "Analysis complete"}

    monkeypatch.setattr("agents.controller.run_agent", fake_run_agent)

    controller = AgentController(
        project_id=project_id,
        user_question="Top item?",
        schema_override="TABLE data (name TEXT)",
    )
    events = [event async for event in controller.run()]
    assert events[-1]["event"] == "done"

    detail = get_run_detail(controller.tracker.run_id)
    lineage = detail["lineage"]
    assert lineage["question"] == "Top item?"
    assert lineage["schema"]["source"] == "override"
    assert lineage["sql_attempts"][0]["sql"] == "SELECT * FROM data LIMIT 10"
    assert lineage["sql_attempts"][0]["policy"]["is_safe"] is True
    assert lineage["sql_attempts"][0]["policy"]["timeout_sec"] == 30
    assert lineage["final_sql"] == "SELECT * FROM data LIMIT 10"
    assert lineage["result"]["sample_rows"] == [["A"]]
    assert lineage["answer"]["summary"] == "A is the top item."


@pytest.mark.asyncio
async def test_agent_controller_records_sql_retry_without_system_retry(monkeypatch, project_id):
    async def fake_run_agent(*args, **kwargs):
        yield {
            "event": "sql_retry",
            "sql": "SELECT * FROM missing_table",
            "sql_error": "Table missing_table does not exist",
            "retry_count": 1,
        }
        yield {"event": "querying", "sql": "SELECT * FROM data LIMIT 10"}
        yield {
            "event": "insight",
            "message": "Recovered",
            "sql": "SELECT * FROM data LIMIT 10",
            "columns": ["name"],
            "rows": [["A"]],
            "row_count": 1,
            "summary": "Recovered after SQL retry.",
        }
        yield {"event": "done", "message": "Analysis complete"}

    monkeypatch.setattr("agents.controller.run_agent", fake_run_agent)

    controller = AgentController(
        project_id=project_id,
        user_question="Recover from SQL failure",
        schema_override="TABLE data (name TEXT)",
    )
    events = [event async for event in controller.run()]
    assert [event["event"] for event in events].count("sql_retry") == 1
    assert "retry" not in [event["event"] for event in events]

    lineage = get_run_detail(controller.tracker.run_id)["lineage"]
    assert len(lineage["sql_attempts"]) == 2
    assert lineage["sql_attempts"][0]["status"] == "failed"
    assert lineage["sql_attempts"][1]["status"] == "executed"
    assert lineage["sql_retries"][0]["next_action"] == "regenerate"
    assert lineage.get("system_retries") in (None, [])


@pytest.mark.asyncio
async def test_agent_controller_records_system_retry(monkeypatch, project_id):
    calls = {"count": 0}

    async def fake_run_agent(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("unexpected system failure")
        yield {"event": "querying", "sql": "SELECT * FROM data LIMIT 10"}
        yield {
            "event": "insight",
            "message": "Done",
            "sql": "SELECT * FROM data LIMIT 10",
            "columns": ["name"],
            "rows": [["A"]],
            "row_count": 1,
            "summary": "Recovered after system retry.",
        }
        yield {"event": "done", "message": "Analysis complete"}

    async def no_sleep(*args, **kwargs):
        return None

    monkeypatch.setattr("agents.controller.run_agent", fake_run_agent)
    monkeypatch.setattr("agents.controller.asyncio.sleep", no_sleep)

    controller = AgentController(
        project_id=project_id,
        user_question="Recover from provider timeout",
        schema_override="TABLE data (name TEXT)",
    )
    events = [event async for event in controller.run()]
    assert events[0]["event"] == "retry"
    assert calls["count"] == 2

    first_lineage = get_run_detail(controller.run_ids[0])["lineage"]
    assert first_lineage["system_retries"][0]["will_retry"] is True
    assert first_lineage["errors"][0]["type"] == "system"

    second_lineage = get_run_detail(controller.run_ids[1])["lineage"]
    assert second_lineage["answer"]["summary"] == "Recovered after system retry."
