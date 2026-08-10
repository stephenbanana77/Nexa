"""Evaluation runner tests."""
from pathlib import Path

from evaluation.runner import run_suite


def test_superstore_eval_suite_runs():
    report = run_suite(Path("backend/evaluation/cases/superstore_core.json"))
    metrics = report["metrics"]
    assert metrics["case_count"] == 12
    assert metrics["sql_policy_pass_rate"] == 1.0
    assert metrics["execution_success_rate"] == 1.0
    assert metrics["semantic_accuracy"] == 1.0


def test_eval_predictions_capture_sql_failures(tmp_path):
    predictions = tmp_path / "predictions.json"
    predictions.write_text('{"sales_by_region": "DROP TABLE data"}', encoding="utf-8")

    report = run_suite(Path("backend/evaluation/cases/superstore_core.json"), predictions)
    first = next(item for item in report["results"] if item["id"] == "sales_by_region")
    assert not first["policy_passed"]
    assert not first["executed"]
    assert not first["correct"]
    assert "not allowed" in first["error"]
