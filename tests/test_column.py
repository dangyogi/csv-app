# test_column.py

import pytest
from csv_app.row import date, Decimal, Column, Date_column, Set_column, Bool_column


@pytest.mark.parametrize("calculated, required, default, can_edit, set_default, set_can_edit", [
    (False, False, None, None, None, None),
    (False, False, 0, False, 0, False),
    (False, False, 0, True, 0, True),
    (True, False, None, None, "not set", False),
    (True, False, None, False, "not set", False),
    (False, True, None, True, "not set", True),
    (False, True, None, None, "not set", None),
    (False, True, None, False, "not set", False),
])
def test_init(calculated, required, default, can_edit, set_default, set_can_edit):
    c = Column('name', calculated=calculated, required=required, default=default, can_edit=can_edit)
    if set_default == "not set":
        assert not hasattr(c, "default")
    else:
        assert c.default == set_default
    assert c.can_edit == set_can_edit


@pytest.mark.parametrize("calculated, required, default, can_edit", [
    (True, True, None, None),
    (True, False, False, False),
    (True, False, 0, None),
    (True, False, None, True),
    (False, True, 0, None),
])
def test_init_errors(calculated, required, default, can_edit):
    with pytest.raises(AssertionError):
        Column('name', calculated=calculated, required=required, default=default, can_edit=can_edit)


@pytest.mark.parametrize("column, csv_value, python_value", [
    (Column('a_str'), "", None),
    (Column('a_str'), "foo  ", "foo"),
    (Column('a_str', choices=('foo', 'bar')), "", None),
    (Column('a_str', choices=('foo', 'bar')), "foo ", "foo"),
    (Column('a_str', choices=('foo', 'bar')), "bar   ", "bar"),
    (Column('an_int', parse=int), "", None),
    (Column('an_int', parse=int), "12", 12),
    (Column('a_float', parse=float), "", None),
    (Column('a_float', parse=float), "1.2", 1.2),
    (Column('a_float', parse=Decimal), "", None),
    (Column('a_float', parse=Decimal), "1.2", Decimal("1.2")),
    (Date_column('a_date'), "", None),
    (Date_column('a_date'), "Nov 2, 26", date(2026, 11, 2)),
    (Set_column('a_set'), "", None),
    (Set_column('a_set'), "a b , cd", {"a b", "cd"}),
    (Bool_column('a_bool'), "", None),
    (Bool_column('a_bool'), "True", True),
])
def test_to_python(column, csv_value, python_value):
    #assert column.to_csv(column.to_python(csv_value)) == python_value
    assert column.to_python(csv_value) == python_value


@pytest.mark.parametrize("column, csv_value", [
    (Column('a_str', choices=('foo', 'bar')), "baz"),
    (Column('an_int', parse=int), "1.2"),
    (Column('an_int', parse=int), "12a"),
    (Column('a_float', parse=float), "1.2.3"),
    (Column('a_float', parse=float), "1.2a"),
    (Column('a_float', parse=Decimal), "12a"),
    (Column('a_float', parse=Decimal), "1.2.3"),
    (Date_column('a_date'), "Nav 2, 26"),
    (Date_column('a_date'), "Apr 31, 26"),
    (Date_column('a_date'), "Apr 1 26"),
    (Bool_column('a_bool'), "no"),
    (Bool_column('a_bool'), "true"),   # Must be True
    (Bool_column('a_bool'), "0"),
])
def test_to_python_ValueError(column, csv_value):
    with pytest.raises(ValueError):
        column.to_python(csv_value)


@pytest.mark.parametrize("column, python_value, csv_value", [
    (Column('a_str', choices=('foo', 'bar')), None, ""),
    (Column('a_str', choices=('foo', 'bar')), "bar", "bar"),
    (Column('an_int', parse=int), None, ""),
    (Column('an_int', parse=int), 12, "12"),
    (Column('a_float', parse=float), None, ""),
    (Column('a_float', parse=float), 1.2, "1.2"),
    (Column('a_float', parse=Decimal), None, ""),
    (Column('a_float', parse=Decimal), Decimal("1.2"), "1.2"),
    (Date_column('a_date'), None, ""),
    (Date_column('a_date'), date(2026, 11, 2), "Nov 2, 26"),
    (Set_column('a_set'), None, ""),
    (Set_column('a_set'), {"a b", "cd"}, "a b , cd"),
    (Bool_column('a_bool'), None, ""),
    (Bool_column('a_bool'), True, "True"),
])
def test_to_csv(column, python_value, csv_value):
    #assert column.to_csv(column.to_python(csv_value)) == python_value
    assert column.to_python(csv_value) == python_value
