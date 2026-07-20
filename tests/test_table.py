# test_table.py

import pytest
from datetime import date
from csv_app.row import Row, Column, Date_column
from csv_app.table import load_rows, Tables, Database, Table_unique, Table_by_date


# Define clear Mock Rows for testing table layout behaviors
class UserRow(Row):
    primary_key = "user_id"
    columns = (
        Column("user_id", required=True),
        Column("username", default="guest"),
    )

class LogRow(Row):
    columns = (
        Date_column("date", required=True),
        Column("message", required=True),
    )


@pytest.fixture(autouse=True)
def clean_global_tables():
    """Wipes the global Tables dictionary before and after every test

    to prevent cross-test contamination in the pytest process memory.
    """
    Tables.clear()
    for key in list(Database.__dict__.keys()):
        delattr(Database, key)
    yield
    Tables.clear()
    for key in list(Database.__dict__.keys()):
        delattr(Database, key)


def test_table_routing():
    """Verifies load_rows assigns Table_unique for primary keys and Table_by_date otherwise."""
    load_rows([UserRow, LogRow])
    
    assert isinstance(Tables["UserRow"], Table_unique)
    assert isinstance(Tables["LogRow"], Table_by_date)
    assert hasattr(Database, "UserRow")


def test_table_unique_duplicate_error():
    """Verifies Table_unique enforces primary key uniqueness constraints."""
    load_rows([UserRow])
    table = Tables["UserRow"]
    
    table.insert(user_id="101", username="bruce")

    with pytest.raises(ValueError):
        # duplicate key -> ValueError (so the create path can catch it and show a message)
        table.insert(user_id="101", username="clark")


def test_table_by_date_sorting():
    """Verifies Table_by_date automatically sorts incoming rows chronologically."""
    load_rows([LogRow])
    table = Tables["LogRow"]
    
    # Insert rows deliberately out of order
    table.insert(date=date(2026, 6, 1), message="Middle log")
    table.insert(date=date(2026, 12, 25), message="Late log")
    table.insert(date=date(2026, 1, 1), message="Early log")
    table.insert(date=date(2026, 1, 1), message="Early log 2")
    table.insert(date=date(2026, 12, 25), message="Late log 2")
    table.insert(date=date(2026, 6, 1), message="Middle log 2")
    
    # Verify binary search forced chronological sequence layout
    assert table[0].message == "Early log"
    assert table[1].message == "Early log 2"
    assert table[2].message == "Middle log"
    assert table[3].message == "Middle log 2"
    assert table[4].message == "Late log"
    assert table[5].message == "Late log 2"

    selected = list(table.get_rows(None, date__ge=date(2026, 6, 1), date__lt=date(2026, 12, 31)))
    assert selected[0].message == "Middle log"
    assert selected[1].message == "Middle log 2"
    assert selected[2].message == "Late log"
    assert selected[3].message == "Late log 2"
