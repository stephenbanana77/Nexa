"""Abstract base class for data source engines and engine registry."""
import os
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

import duckdb
import pandas as pd
import pymysql
import chardet


@dataclass
class SchemaColumn:
    name: str
    type: str
    missing_count: int = 0
    missing_pct: float = 0.0


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int


class DataSourceEngine(ABC):
    """Abstract base for all data source engines (DuckDB, MySQL, ClickHouse, etc.)."""

    @abstractmethod
    def query(self, sql: str, timeout_sec: int | None = None) -> QueryResult:
        """Execute a SQL query and return results."""
        ...

    @abstractmethod
    def preview(self, table_name: str = "data", limit: int = 1000) -> QueryResult:
        """Preview data from a table."""
        ...

    @abstractmethod
    def get_schema(self, table_name: str = "data") -> list[SchemaColumn]:
        """Get schema information for a table."""
        ...

    @abstractmethod
    def get_tables(self) -> list[dict]:
        """List available tables."""
        ...

    def health_check(self) -> bool:
        """Check if the engine is healthy."""
        return True


class DuckDBEngine(DataSourceEngine):
    """File-backed DuckDB engine for CSV/Excel analysis. Survives restarts."""

    def __init__(self, db_path: str = None):
        import os as _os
        if db_path:
            _os.makedirs(_os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = duckdb.connect(db_path) if db_path else duckdb.connect(":memory:")
        self._tables: set[str] = set()
        self._table_row_counts: dict[str, int] = {}
        self._query_lock = threading.Lock()

    def _drop_relation(self, safe_name: str) -> None:
        """Drop a table or view without assuming which relation type exists."""
        for statement in (f"DROP TABLE IF EXISTS {safe_name}", f"DROP VIEW IF EXISTS {safe_name}"):
            try:
                self.conn.execute(statement)
                return
            except duckdb.CatalogException:
                continue

    def register_csv(self, file_path: str, table_name: str = "data") -> None:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        self._drop_relation(safe_name)
        # Use DuckDB's native CSV reader — avoids double memory with pandas
        try:
            self.conn.execute(
                f"CREATE OR REPLACE TABLE {safe_name} AS SELECT * FROM read_csv_auto('{file_path}')"
            )
        except Exception:
            # Fallback: pandas for complex encodings
            with open(file_path, "rb") as f:
                raw = f.read(200000)
            encoding = chardet.detect(raw)["encoding"] or "utf-8"
            try:
                df = pd.read_csv(file_path, encoding=encoding)
            except Exception:
                df = pd.read_csv(file_path, encoding=encoding, encoding_errors="replace")
            self.conn.register(safe_name, df)
        self._tables.add(safe_name)
        self._table_row_counts[safe_name] = int(
            self.conn.execute(f"SELECT COUNT(*) FROM {safe_name}").fetchone()[0]
        )

    def register_excel(self, file_path: str, table_name: str = "data") -> None:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        df = pd.read_excel(file_path)
        self._drop_relation(safe_name)
        self.conn.execute(f"CREATE OR REPLACE TABLE {safe_name} AS SELECT * FROM df")
        self._tables.add(safe_name)
        self._table_row_counts[safe_name] = len(df)

    def _query_sync(self, sql: str) -> QueryResult:
        result = self.conn.execute(sql).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        rows = [list(row) for row in result]
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))

    def query(self, sql: str, timeout_sec: int | None = None) -> QueryResult:
        if not timeout_sec:
            with self._query_lock:
                return self._query_sync(sql)

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._query_with_lock, sql)
        try:
            result = future.result(timeout=timeout_sec)
            executor.shutdown(wait=True)
            return result
        except FutureTimeoutError as exc:
            if hasattr(self.conn, "interrupt"):
                self.conn.interrupt()
            executor.shutdown(wait=False, cancel_futures=True)
            raise TimeoutError(f"Query timed out after {timeout_sec} seconds") from exc

    def _query_with_lock(self, sql: str) -> QueryResult:
        with self._query_lock:
            return self._query_sync(sql)

    def preview(self, table_name: str = "data", limit: int = 1000) -> QueryResult:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        return self.query(f"SELECT * FROM {safe_name} LIMIT {limit}")

    def get_schema(self, table_name: str = "data") -> list[SchemaColumn]:
        safe_name = table_name.replace("-", "_").replace(" ", "_")
        try:
            result = self.conn.execute(f"DESCRIBE {safe_name}").fetchall()
            return [SchemaColumn(name=r[0], type=r[1]) for r in result]
        except Exception:
            return []

    def get_tables(self) -> list[dict]:
        return [{"name": t, "row_count": self._table_row_counts.get(t, 0)} for t in self._tables]


class MySQLConnector(DataSourceEngine):
    """MySQL query engine for connected databases."""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self._config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "connect_timeout": 10,
            "read_timeout": 30,
            "write_timeout": 30,
        }
        self.connection = None

    def connect(self):
        if self.connection:
            try:
                self.connection.ping(reconnect=True)
                return
            except Exception:
                self.connection = None
        self.connection = pymysql.connect(**self._config, cursorclass=pymysql.cursors.Cursor)

    def query(self, sql: str, timeout_sec: int | None = None) -> QueryResult:
        self.connect()
        with self.connection.cursor() as cursor:
            if timeout_sec:
                try:
                    cursor.execute(f"SET SESSION MAX_EXECUTION_TIME={int(timeout_sec * 1000)}")
                except Exception:
                    pass
            cursor.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return QueryResult(columns=columns, rows=[list(r) for r in rows], row_count=len(rows))

    def preview(self, table_name: str = "data", limit: int = 1000) -> QueryResult:
        return self.query(f"SELECT * FROM `{table_name}` LIMIT {limit}")

    def get_schema(self, table_name: str = "data") -> list[SchemaColumn]:
        self.connect()
        with self.connection.cursor() as cursor:
            cursor.execute(f"DESCRIBE `{table_name}`")
            return [SchemaColumn(name=col[0], type=col[1]) for col in cursor.fetchall()]

    def get_tables(self) -> list[dict]:
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

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None


class EngineRegistry:
    """Registry for managing multiple data source engines per project."""

    def __init__(self):
        import threading
        self._engines: dict[str, DataSourceEngine] = {}
        self._lock = threading.Lock()

    def register(self, project_id: str, engine: DataSourceEngine):
        with self._lock:
            self._engines[project_id] = engine

    def get(self, project_id: str) -> DataSourceEngine:
        with self._lock:
            if project_id not in self._engines:
                import os as _os
                db_path = _os.path.join(_os.getenv("STORAGE_PATH", "./storage"), f"{project_id}.duckdb")
                self._engines[project_id] = DuckDBEngine(db_path)
            return self._engines[project_id]

    def remove(self, project_id: str):
        with self._lock:
            engine = self._engines.pop(project_id, None)
        if isinstance(engine, MySQLConnector):
            engine.close()

    def clear(self):
        with self._lock:
            engines = dict(self._engines)
            self._engines.clear()
        for engine in engines.values():
            if isinstance(engine, MySQLConnector):
                engine.close()


# Singleton registry
engine_registry = EngineRegistry()


def get_engine(project_id: str) -> DataSourceEngine:
    return engine_registry.get(project_id)


def register_mysql(project_id: str, host: str, port: int, user: str, password: str, database: str):
    connector = MySQLConnector(host, port, user, password, database)
    connector.connect()  # Test connection
    engine_registry.register(project_id, connector)


def load_dataset(project_id: str, file_path: str, source_type: str, table_name: str = "data") -> None:
    engine = engine_registry.get(project_id)
    if not isinstance(engine, DuckDBEngine):
        engine = DuckDBEngine()
        engine_registry.register(project_id, engine)

    if source_type in ("csv", ".csv"):
        engine.register_csv(file_path, table_name=table_name)
    elif source_type in ("xlsx", "xls", ".xlsx", ".xls"):
        engine.register_excel(file_path, table_name=table_name)
