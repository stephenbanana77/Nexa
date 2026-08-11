"""Dataset table name tests."""
from services.dataset_tables import dataset_table_name


def test_dataset_table_name_is_sql_safe_and_stable():
    assert dataset_table_name("123e4567-e89b-12d3-a456-426614174000").startswith("ds_")
    assert dataset_table_name("abc-def") == "abc_def"
    assert dataset_table_name("abc-def") == dataset_table_name("abc-def")
