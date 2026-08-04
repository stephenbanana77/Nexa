"""Google Sheets connector — loads a published Google Sheet as a data source."""
from typing import Any
from tools.query_engine import DataSourceEngine, QueryResult
import pandas as pd


class GoogleSheetsConnector(DataSourceEngine):
    """Reads a published Google Sheet via CSV export URL and queries it via DuckDB."""

    def __init__(self, sheet_url: str, sheet_name: str = None):
        self.sheet_url = sheet_url
        self.sheet_name = sheet_name or "Sheet1"
        self._df = None
        self._table_name = "sheet_data"

    def _load(self):
        """Lazy load sheet data into DuckDB-backed DataFrame."""
        if self._df is None:
            # Google Sheets published CSV URL format:
            # https://docs.google.com/spreadsheets/d/{id}/export?format=csv&gid={gid}
            url = self.sheet_url
            if "/export?" not in url:
                # Convert standard sheet URL to CSV export URL
                if "/edit" in url:
                    url = url.replace("/edit", "/export?format=csv")
                else:
                    url = f"{url.rstrip('/')}/export?format=csv"
            self._df = pd.read_csv(url)
        return self._df

    def query(self, sql: str, params: dict = None) -> QueryResult:
        df = self._load()
        import duckdb
        conn = duckdb.connect(":memory:")
        conn.register(self._table_name, df)
        try:
            result = conn.execute(sql, params or {}).fetchdf()
            return QueryResult(
                columns=list(result.columns),
                rows=result.values.tolist(),
                row_count=len(result),
            )
        finally:
            conn.close()

    def preview(self, table: str = None, limit: int = 5) -> QueryResult:
        df = self._load()
        return QueryResult(
            columns=list(df.columns),
            rows=df.head(limit).values.tolist(),
            row_count=min(limit, len(df)),
        )

    def get_schema(self, table: str = None) -> list[dict]:
        df = self._load()
        return [
            {"name": col, "type": str(df[col].dtype), "nullable": bool(df[col].isna().any())}
            for col in df.columns
        ]

    def get_tables(self) -> list[str]:
        return [self._table_name]

    def health_check(self) -> bool:
        try:
            self._load()
            return len(self._df) > 0
        except Exception:
            return False

    def close(self):
        self._df = None
