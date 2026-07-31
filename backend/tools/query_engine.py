"""DuckDB query engine for CSV analysis and MySQL connector."""
import duckdb
import pandas as pd
import pymysql
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


class MySQLConnector:
    """MySQL query engine for connected databases."""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.config = {"host": host, "port": port, "user": user, "password": password, "database": database}
        self.connection = None

    def connect(self):
        self.connection = pymysql.connect(**self.config, cursorclass=pymysql.cursors.Cursor)

    def query(self, sql: str) -> dict:
        if not self.connection:
            self.connect()
        with self.connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return {
                "columns": columns,
                "rows": [list(row) for row in rows],
                "row_count": len(rows),
            }

    def get_tables(self) -> list[dict]:
        if not self.connection:
            self.connect()
        with self.connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            result = []
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                (count,) = cursor.fetchone()
                result.append({"name": table_name, "row_count": count})
            return result

    def get_schema(self, table_name: str) -> list[dict]:
        if not self.connection:
            self.connect()
        with self.connection.cursor() as cursor:
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            return [{"name": col[0], "type": col[1]} for col in columns]

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None


_engines: dict[str, DuckDBEngine] = {}
_mysql_connectors: dict[str, MySQLConnector] = {}


def get_engine(project_id: str) -> DuckDBEngine:
    if project_id not in _engines:
        _engines[project_id] = DuckDBEngine()
    return _engines[project_id]


def get_mysql_connector(project_id: str) -> MySQLConnector | None:
    return _mysql_connectors.get(project_id)


def register_mysql(project_id: str, host: str, port: int, user: str, password: str, database: str):
    connector = MySQLConnector(host, port, user, password, database)
    connector.connect()  # Test connection
    _mysql_connectors[project_id] = connector


def load_dataset(engine: DuckDBEngine, file_path: str, source_type: str) -> None:
    if source_type in ("csv", ".csv"):
        engine.register_csv(file_path)
    elif source_type in ("xlsx", "xls", ".xlsx", ".xls"):
        engine.register_excel(file_path)
