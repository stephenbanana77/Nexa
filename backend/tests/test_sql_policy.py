"""SQL safety policy tests."""
import time

import pytest

from services.sql_policy import MAX_ROWS, inspect_sql_policy, validate_sql
from tools.query_engine import DuckDBEngine


def assert_safe(sql: str) -> str:
    is_safe, result = validate_sql(sql)
    assert is_safe, result
    return result


def assert_blocked(sql: str) -> str:
    is_safe, result = validate_sql(sql)
    assert not is_safe
    return result


def test_select_gets_limit():
    result = assert_safe("SELECT * FROM data")
    assert result == f"SELECT * FROM data LIMIT {MAX_ROWS}"


def test_existing_top_level_limit_is_preserved():
    result = assert_safe("SELECT * FROM data LIMIT 25")
    assert result == "SELECT * FROM data LIMIT 25"


def test_with_query_is_allowed_and_limited():
    result = assert_safe("WITH x AS (SELECT 1 AS n) SELECT * FROM x")
    assert result.endswith(f"LIMIT {MAX_ROWS}")


def test_union_query_is_allowed_and_limited():
    result = assert_safe("SELECT a FROM t1 UNION SELECT a FROM t2")
    assert "UNION" in result
    assert result.endswith(f"LIMIT {MAX_ROWS}")


def test_multi_statement_payload_is_blocked():
    message = assert_blocked("SELECT * FROM data; DROP TABLE data")
    assert "Only one SQL statement" in message


def test_write_operations_are_blocked_by_ast():
    for sql in [
        "DROP TABLE data",
        "DELETE FROM data WHERE id = 1",
        "INSERT INTO data VALUES (1)",
        "UPDATE data SET name = 'x'",
        "CREATE TABLE copy AS SELECT * FROM data",
        "MERGE INTO data USING other ON data.id = other.id WHEN MATCHED THEN UPDATE SET name = other.name",
    ]:
        assert "not allowed" in assert_blocked(sql)


def test_non_query_commands_are_blocked():
    assert "Only read-only SELECT" in assert_blocked("SHOW TABLES")
    assert "Only read-only SELECT" in assert_blocked("DESCRIBE data")


def test_dangerous_words_inside_comments_do_not_trigger_false_positive():
    result = assert_safe("SELECT * FROM data /* DROP TABLE data */")
    assert result == f"SELECT * FROM data LIMIT {MAX_ROWS}"


def test_invalid_sql_is_blocked():
    assert "Invalid SQL" in assert_blocked("SELECT FROM")


def test_policy_decision_records_limit_and_risk_flags():
    decision = inspect_sql_policy("SELECT * FROM data")
    assert decision.is_safe
    assert decision.final_sql == f"SELECT * FROM data LIMIT {MAX_ROWS}"
    assert decision.auto_limit_added
    assert "select_star" in decision.risk_flags
    assert "auto_limit_added" in decision.risk_flags
    assert decision.timeout_sec == 30


def test_policy_decision_records_block_reason():
    decision = inspect_sql_policy("DROP TABLE data")
    assert not decision.is_safe
    assert decision.operation == "DROP"
    assert "not allowed" in decision.reason


def test_duckdb_query_timeout(monkeypatch):
    engine = DuckDBEngine()

    def slow_query(sql):
        time.sleep(0.2)
        return None

    monkeypatch.setattr(engine, "_query_sync", slow_query)
    with pytest.raises(TimeoutError):
        engine.query("SELECT 1", timeout_sec=0.01)
