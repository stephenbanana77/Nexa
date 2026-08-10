"""SQL safety policy shared between Chat Agent and Dataset API."""
from dataclasses import asdict, dataclass

from sqlglot import errors as sqlglot_errors
from sqlglot import exp, parse

_BLOCKED_EXPRESSIONS = (
    exp.Alter,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Merge,
    exp.Update,
)
_BLOCKED_NAMES = (
    "ALTER",
    "CREATE",
    "DELETE",
    "DROP",
    "INSERT",
    "MERGE",
    "TRUNCATE",
    "UPDATE",
)

MAX_ROWS = 10000
QUERY_TIMEOUT_SEC = 30


@dataclass
class SQLPolicyDecision:
    is_safe: bool
    original_sql: str
    final_sql: str | None = None
    reason: str | None = None
    operation: str | None = None
    auto_limit_added: bool = False
    max_rows: int = MAX_ROWS
    timeout_sec: int = QUERY_TIMEOUT_SEC
    risk_flags: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _blocked_operation_name(expression: exp.Expression) -> str | None:
    for node in expression.walk():
        if isinstance(node, _BLOCKED_EXPRESSIONS):
            return node.key.upper()
        if node.key.upper() in _BLOCKED_NAMES:
            return node.key.upper()
    return None


def _has_top_level_limit(expression: exp.Expression) -> bool:
    return expression.args.get("limit") is not None


def _risk_flags(expression: exp.Expression, had_limit: bool) -> list[str]:
    flags = []
    if not had_limit:
        flags.append("auto_limit_added")
    if any(isinstance(node, exp.Star) for node in expression.walk()):
        flags.append("select_star")
    for node in expression.find_all(exp.Join):
        if not node.args.get("on") and not node.args.get("using"):
            flags.append("join_without_condition")
            break
    return flags


def inspect_sql_policy(sql: str) -> SQLPolicyDecision:
    """Return a structured SQL policy decision for auditability."""
    original_sql = sql or ""
    if not sql or not sql.strip():
        return SQLPolicyDecision(
            is_safe=False,
            original_sql=original_sql,
            reason="SQL query is empty.",
        )

    try:
        statements = [stmt for stmt in parse(sql, read="duckdb") if stmt is not None]
    except sqlglot_errors.ParseError as exc:
        return SQLPolicyDecision(
            is_safe=False,
            original_sql=original_sql,
            reason=f"Invalid SQL: {str(exc).splitlines()[0]}",
        )

    if len(statements) != 1:
        return SQLPolicyDecision(
            is_safe=False,
            original_sql=original_sql,
            reason="Only one SQL statement is allowed.",
        )

    statement = statements[0]
    blocked = _blocked_operation_name(statement)
    if blocked:
        return SQLPolicyDecision(
            is_safe=False,
            original_sql=original_sql,
            reason=f"Dangerous SQL operation '{blocked}' is not allowed. Use SELECT only.",
            operation=blocked,
        )

    operation = statement.key.upper()
    if not isinstance(statement, exp.Query):
        return SQLPolicyDecision(
            is_safe=False,
            original_sql=original_sql,
            reason=f"Only read-only SELECT queries are allowed, got '{operation}'.",
            operation=operation,
        )

    had_limit = _has_top_level_limit(statement)
    if not had_limit:
        statement = statement.copy().limit(MAX_ROWS)

    return SQLPolicyDecision(
        is_safe=True,
        original_sql=original_sql,
        final_sql=statement.sql(dialect="duckdb", comments=False),
        operation=operation,
        auto_limit_added=not had_limit,
        risk_flags=_risk_flags(statement, had_limit),
    )


def validate_sql(sql: str) -> tuple[bool, str]:
    """Parse SQL with an AST policy and add a safety limit.

    Rules:
    - Allows exactly one read-only query expression (SELECT, WITH, UNION, etc.).
    - Blocks DDL/DML nodes anywhere in the AST.
    - Blocks multi-statement payloads.
    - Auto-adds a top-level LIMIT when missing.
    """
    decision = inspect_sql_policy(sql)
    if not decision.is_safe:
        return False, decision.reason or "SQL query is not allowed."
    return True, decision.final_sql or sql
