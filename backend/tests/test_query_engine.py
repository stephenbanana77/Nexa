"""DuckDB relation lifecycle tests."""

from tools.query_engine import DuckDBEngine


def test_register_csv_replaces_existing_view(tmp_path):
    csv_path = tmp_path / "replacement.csv"
    csv_path.write_text("region,sales\nEast,10\nWest,20\n", encoding="utf-8")

    engine = DuckDBEngine()
    engine.conn.execute("CREATE VIEW data AS SELECT 'stale' AS region, 0 AS sales")

    engine.register_csv(str(csv_path), table_name="data")

    result = engine.query("SELECT region, sales FROM data ORDER BY sales")
    assert result.rows == [["East", 10], ["West", 20]]
