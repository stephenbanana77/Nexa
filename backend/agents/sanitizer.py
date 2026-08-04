"""Prompt injection protection — sanitize user inputs before feeding to LLM."""
import re

# Patterns commonly used in prompt injection attacks
DANGEROUS_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"forget\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"override\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)",
    r"system\s*:\s*",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[system\]",
    r"\[/system\]",
    r"you\s+are\s+now\s+",
    r"new\s+instructions?\s*:",
    r"your\s+new\s+identity\s+is",
    r"act\s+as\s+",
    r"pretend\s+you\s+are",
    r"from\s+now\s+on\s+you\s+are",
]

COLUMN_NAME_DANGEROUS = [
    r"```",
    r"<\|",
    r"\|>",
    r"\[system\]",
    r"\[/system\]",
    r"<script",
]


def sanitize_user_input(text: str) -> tuple[str, bool]:
    """Sanitize user input. Returns (cleaned_text, was_modified)."""
    cleaned = text
    modified = False

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            modified = True
        cleaned = re.sub(pattern, "[REDACTED]", cleaned, flags=re.IGNORECASE)

    # Truncate extremely long prompts
    if len(cleaned) > 4000:
        cleaned = cleaned[:4000]
        modified = True

    return cleaned, modified


def sanitize_column_name(name: str) -> str:
    """Sanitize a column name for prompt injection risks."""
    for pattern in COLUMN_NAME_DANGEROUS:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    # Remove special chars that could break markdown/prompt parsing
    name = name.replace("`", "'").replace("{", "(").replace("}", ")")
    return name.strip()[:100]


def sanitize_schema(schema_text: str) -> str:
    """Sanitize schema text before injecting into prompts."""
    if not schema_text:
        return ""
    # Truncate extremely large schemas
    if len(schema_text) > 8000:
        schema_text = schema_text[:8000] + "\n... (truncated)"
    return schema_text
