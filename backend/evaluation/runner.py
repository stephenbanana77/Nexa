"""Run offline evaluation for SQL-generating data analysis agents."""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from services.sql_policy import validate_sql


@dataclass
class EvalCase:
    id: str
    question: str
    expected_sql: str
    candidate_sql: str | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_suite(path: Path) -> tuple[dict[str, Any], list[EvalCase]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["dataset"], [EvalCase(**case) for case in payload["cases"]]


def _load_predictions(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return {str(k): str(v) for k, v in payload.items()}
    return {str(item["id"]): str(item["sql"]) for item in payload}


def _connect_dataset(dataset: dict[str, Any]) -> duckdb.DuckDBPyConnection:
    csv_path = Path(dataset["path"])
    if not csv_path.is_absolute():
        csv_path = _repo_root() / csv_path
    table = dataset.get("table", "data")
    conn = duckdb.connect(":memory:")
    try:
        conn.execute(
            f'CREATE TABLE "{table}" AS SELECT * FROM read_csv_auto(?)',
            [str(csv_path)],
        )
    except Exception:
        df = pd.read_csv(csv_path, encoding="latin1")
        conn.register("_eval_df", df)
        conn.execute(f'CREATE TABLE "{table}" AS SELECT * FROM _eval_df')
    return conn


def _execute(conn: duckdb.DuckDBPyConnection, sql: str) -> tuple[list[str], list[list[Any]]]:
    result = conn.execute(sql)
    columns = [desc[0] for desc in result.description]
    rows = [list(row) for row in result.fetchall()]
    return columns, rows


def _normalize(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    return value


def _same_result(left: tuple[list[str], list[list[Any]]], right: tuple[list[str], list[list[Any]]]) -> bool:
    left_cols, left_rows = left
    right_cols, right_rows = right
    if left_cols != right_cols or len(left_rows) != len(right_rows):
        return False
    return [
        [_normalize(value) for value in row]
        for row in left_rows
    ] == [
        [_normalize(value) for value in row]
        for row in right_rows
    ]


def run_suite(suite_path: Path, predictions_path: Path | None = None) -> dict[str, Any]:
    dataset, cases = _load_suite(suite_path)
    predictions = _load_predictions(predictions_path)
    conn = _connect_dataset(dataset)
    results = []

    started = time.perf_counter()
    for case in cases:
        case_started = time.perf_counter()
        candidate_sql = predictions.get(case.id) or case.candidate_sql or case.expected_sql
        expected = _execute(conn, case.expected_sql)

        policy_ok, policy_result = validate_sql(candidate_sql)
        executed = False
        correct = False
        error = None
        actual_rows = 0

        if policy_ok:
            try:
                actual = _execute(conn, policy_result)
                actual_rows = len(actual[1])
                executed = True
                correct = _same_result(actual, expected)
            except Exception as exc:
                error = str(exc)
        else:
            error = policy_result

        results.append({
            "id": case.id,
            "question": case.question,
            "policy_passed": policy_ok,
            "executed": executed,
            "correct": correct,
            "latency_ms": round((time.perf_counter() - case_started) * 1000, 2),
            "expected_sql": case.expected_sql,
            "candidate_sql": candidate_sql,
            "final_sql": policy_result if policy_ok else None,
            "actual_row_count": actual_rows,
            "error": error,
        })

    total = len(results)
    metrics = {
        "case_count": total,
        "sql_policy_pass_rate": _rate(results, "policy_passed"),
        "execution_success_rate": _rate(results, "executed"),
        "semantic_accuracy": _rate(results, "correct"),
        "avg_latency_ms": round(sum(item["latency_ms"] for item in results) / total, 2) if total else 0,
        "retry_repair_rate": None,
        "token_cost_estimate": None,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
    }
    return {"dataset": dataset, "metrics": metrics, "results": results}


def _rate(results: list[dict[str, Any]], key: str) -> float:
    if not results:
        return 0.0
    return round(sum(1 for item in results if item[key]) / len(results), 4)


def _print_markdown(report: dict[str, Any]) -> None:
    metrics = report["metrics"]
    print(f"# Evaluation Report: {report['dataset']['name']}")
    print()
    print("| Metric | Value |")
    print("|---|---:|")
    for key, value in metrics.items():
        print(f"| {key} | {value} |")
    print()
    print("| Case | Policy | Execute | Correct | Latency ms |")
    print("|---|---:|---:|---:|---:|")
    for item in report["results"]:
        print(
            f"| {item['id']} | {item['policy_passed']} | {item['executed']} | "
            f"{item['correct']} | {item['latency_ms']} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Nexa offline evaluation.")
    parser.add_argument(
        "--suite",
        default="backend/evaluation/cases/superstore_core.json",
        help="Path to evaluation suite JSON.",
    )
    parser.add_argument("--predictions", help="Optional JSON file mapping case id to generated SQL.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    suite_path = Path(args.suite)
    if not suite_path.is_absolute():
        suite_path = _repo_root() / suite_path
    predictions_path = Path(args.predictions) if args.predictions else None
    if predictions_path and not predictions_path.is_absolute():
        predictions_path = _repo_root() / predictions_path

    report = run_suite(suite_path, predictions_path)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    else:
        _print_markdown(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
