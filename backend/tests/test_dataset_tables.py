"""Dataset table name tests."""
from services.dataset_tables import bind_default_table, dataset_table_name


def test_dataset_table_name_is_sql_safe_and_stable():
    assert dataset_table_name("123e4567-e89b-12d3-a456-426614174000").startswith("ds_")
    assert dataset_table_name("abc-def") == "abc_def"
    assert dataset_table_name("abc-def") == dataset_table_name("abc-def")


def test_dataset_binding_uses_sql_ast_and_preserves_ctes_and_literals():
    bound = bind_default_table("SELECT 'data' AS label FROM data", "abc-def")
    assert "FROM abc_def" in bound
    assert "'data'" in bound

    cte = bind_default_table("WITH data AS (SELECT 1 AS value) SELECT * FROM data", "abc-def")
    assert "FROM data" in cte
    assert "abc_def" not in cte
