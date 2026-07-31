"""DuckDB query engine for CSV analysis."""
import duckdb
import pandas as pd
import chardet
from pathlib import Path
from utils.config import settings


class DuckDBEngine:
    def __init__(self):
        self.conn = duckdb.connect(":memory:")

    def register_csv(self, file_path: str, table_name: str = "data") -> None:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        self.conn.execute(f"DROP TABLE IF EXISTS {safe_name}")
        # Use pandas to handle encoding, then register with DuckDB
        with open(file_path, "rb") as f:
            raw = f.read(200000)
        encoding = chardet.detect(raw)["encoding"] or "utf-8"
        try:
            df = pd.read_csv(file_path, encoding=encoding)
        except Exception:
            df = pd.read_csv(file_path, encoding=encoding, encoding_errors="replace")
        self.conn.register(safe_name, df)

    def register_excel(self, file_path: str, table_name: str = "data") -> None:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        df = pd.read_excel(file_path)
        self.conn.execute(f"DROP TABLE IF EXISTS {safe_name}")
        self.conn.register(safe_name, df)

    def query(self, sql: str) -> dict:
        result = self.conn.execute(sql).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        rows = [list(row) for row in result]
        return {"columns": columns, "rows": rows, "row_count": len(rows)}

    def preview(self, table_name: str = "data", limit: int = 1000) -> dict:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        return self.query(f"SELECT * FROM {safe_name} LIMIT {limit}")

    def get_schema(self, table_name: str = "data") -> list[dict]:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        result = self.conn.execute(f"DESCRIBE {safe_name}").fetchall()
        return [{"name": r[0], "type": r[1]} for r in result]

    def get_row_count(self, table_name: str = "data") -> int:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        result = self.conn.execute(f"SELECT COUNT(*) FROM {safe_name}").fetchone()
        return result[0] if result else 0


_engines: dict[str, DuckDBEngine] = {}


def get_engine(project_id: str) -> DuckDBEngine:
    if project_id not in _engines:
        _engines[project_id] = DuckDBEngine()
    return _engines[project_id]


def load_dataset(engine: DuckDBEngine, file_path: str, source_type: str) -> None:
    if source_type in ("csv", ".csv"):
        engine.register_csv(file_path)
    elif source_type in ("xlsx", "xls", ".xlsx", ".xls"):
        engine.register_excel(file_path)
