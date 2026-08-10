"""Small SQLite schema guard for local development.

Alembic remains the source of truth for migrations. This guard exists because
the local demo app uses ``Base.metadata.create_all`` on an existing SQLite file,
and SQLAlchemy does not add newly introduced columns/tables to existing tables.
"""
from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def ensure_sqlite_dev_schema(engine: Engine) -> None:
    """Patch additive local SQLite schema gaps in an idempotent way."""
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "runs" in tables:
            run_columns = {col["name"] for col in inspector.get_columns("runs")}
            if "lineage" not in run_columns:
                conn.execute(text("ALTER TABLE runs ADD COLUMN lineage JSON"))

        if "semantic_metrics" not in tables:
            conn.execute(text("""
                CREATE TABLE semantic_metrics (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    project_id CHAR(32) NOT NULL,
                    dataset_id CHAR(32),
                    name VARCHAR(255) NOT NULL,
                    expression TEXT NOT NULL,
                    description TEXT NOT NULL,
                    format VARCHAR(50) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects (id),
                    FOREIGN KEY(dataset_id) REFERENCES datasets (id)
                )
            """))

        if "semantic_dimensions" not in tables:
            conn.execute(text("""
                CREATE TABLE semantic_dimensions (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    project_id CHAR(32) NOT NULL,
                    dataset_id CHAR(32),
                    name VARCHAR(255) NOT NULL,
                    "column" VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects (id),
                    FOREIGN KEY(dataset_id) REFERENCES datasets (id)
                )
            """))

        if "analysis_reports" not in tables:
            conn.execute(text("""
                CREATE TABLE analysis_reports (
                    id CHAR(32) NOT NULL PRIMARY KEY,
                    project_id CHAR(32) NOT NULL,
                    dataset_id CHAR(32),
                    title VARCHAR(255) NOT NULL,
                    content JSON NOT NULL,
                    semantic_snapshot JSON,
                    memory JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects (id),
                    FOREIGN KEY(dataset_id) REFERENCES datasets (id)
                )
            """))
