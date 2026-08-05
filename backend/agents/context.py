"""Context manager for injecting dataset schema into prompts."""
from database import SessionLocal
from models.project import Dataset
from tools import get_engine


def get_schema_context(project_id: str, dataset_id: str = None) -> str:
    db = SessionLocal()
    try:
        query = db.query(Dataset).filter(Dataset.project_id == project_id)
        if dataset_id:
            dataset = query.filter(Dataset.id == dataset_id).first()
        else:
            dataset = query.order_by(Dataset.created_at.desc()).first()
        if not dataset or not dataset.schema_info:
            return "No dataset loaded."

        schema_lines = [f"Table 'data' ({dataset.row_count} rows, {dataset.column_count} columns)"]
        schema_lines.append("")
        for col in dataset.schema_info:
            missing = f" ({col['missing_pct']}% missing)" if col["missing_pct"] > 0 else ""
            schema_lines.append(f"- {col['name']}: {col['type']}{missing}")

        return "\n".join(schema_lines)
    finally:
        db.close()


def get_preview_context(project_id: str) -> str:
    engine = get_engine(project_id)
    try:
        result = engine.preview(limit=5)
        lines = ["Sample data (first 5 rows):"]
        lines.append(" | ".join(result.columns))
        for row in result.rows[:5]:
            lines.append(" | ".join(str(v) for v in row))
        return "\n".join(lines)
    except Exception:
        return "Preview not available."
