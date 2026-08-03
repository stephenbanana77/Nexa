"""PostgreSQL connector — implements DataSourceEngine for PostgreSQL databases."""
from typing import Any
from tools.query_engine import DataSourceEngine, QueryResult


class PostgreSQLConnector(DataSourceEngine):
    """Connects to PostgreSQL databases via async driver."""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self._conn = None
        self._engine = None

    def _connect(self):
        """Lazy connection to PostgreSQL."""
        if self._conn is None:
            try:
                import psycopg2
                self._conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database,
                )
                self._conn.autocommit = True
            except ImportError:
                raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")
        return self._conn

    def query(self, sql: str, params: dict = None) -> QueryResult:
        """Execute a SQL query."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params or {})
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                rows = [list(row) for row in cursor.fetchall()]
            else:
                columns = []
                rows = []
            return QueryResult(columns=columns, rows=rows, row_count=len(rows))
        except Exception:
            if self._conn:
                self._conn.rollback()
                self._conn = None
            raise

    def preview(self, table: str = None, limit: int = 5) -> QueryResult:
        """Preview a table or the first available table."""
        if table:
            return self.query(f'SELECT * FROM "{table}" LIMIT {limit}')
        tables = self.get_tables()
        if not tables:
            return QueryResult(columns=[], rows=[], row_count=0)
        return self.preview(tables[0], limit)

    def get_schema(self, table: str = None) -> list[dict]:
        """Get schema info for tables."""
        conn = self._connect()
        cursor = conn.cursor()
        if table:
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table,))
        else:
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            return [row[0] for row in cursor.fetchall()]

        return [
            {"name": row[0], "type": row[1], "nullable": row[2] == "YES"}
            for row in cursor.fetchall()
        ]

    def get_tables(self) -> list[str]:
        """Get all table names."""
        return self.get_schema()  # returns list of table names when table=None

    def health_check(self) -> bool:
        """Test the connection."""
        try:
            self._connect()
            return True
        except Exception:
            return False

    def close(self):
        """Close the connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
