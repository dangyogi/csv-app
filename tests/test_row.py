# test_row.py

import pytest
from unittest.mock import Mock

from csv_app.row import Column, Row


@pytest.mark.parametrize("pkey, pkeys", [
    (None, ()),
    ('req', ()),
    (None, ('req', 'with_default')),
])
def test_create(pkey, pkeys):
    calc = Column('calc', calculated=True) # default, required, can_edit not allowed by Column
    req = Column('req', required=True)
    with_default = Column('with_default', default=0)  # can't be primary_key, but primary_keys ok
    no_default = Column('no_default')
    can_edit_t = Column('can_edit_t', can_edit=True)
    can_edit_f = Column('can_edit_f', can_edit=False)

    class Test_row(Row):
        columns = (calc, req, with_default, no_default, can_edit_t, can_edit_f)
        primary_key = pkey
        primary_keys = pkeys

    assert tuple(Test_row.column_map.keys()) == ('calc', 'req', 'with_default', 'no_default',
                                                 'can_edit_t', 'can_edit_f')
    assert Test_row.stored_names == ['req', 'with_default', 'no_default', 'can_edit_t', 'can_edit_f']
    assert Test_row.required == frozenset(['req'])
    if pkey == 'req' or 'req' in pkeys:
        assert not req.can_edit
    else:
        assert req.can_edit
    assert can_edit_t.can_edit
    assert not can_edit_f.can_edit

    # check defaults in Test_row
    # no default set for calculated or required
    assert not hasattr(Test_row, 'calc')
    assert not hasattr(Test_row, 'req')
    for default_none in ('no_default', 'can_edit_t', 'can_edit_f'):
        # default defaults to None if not calculated or required
        assert getattr(Test_row, default_none) is None
    # default set in Column copied to Row class
    assert Test_row.with_default == 0


@pytest.mark.parametrize("pkey, pkeys, msg", [
    ('calc', (), "Row Test_row, primary key calc can't be calculated"),
    (None, ('req', 'calc',), "Row Test_row, primary key calc can't be calculated"),
    ('with_default', (), "Row Test_row, primary key with_default must be required"),
    ('no_default', (), "Row Test_row, primary key no_default must be required"),
    (None, ('req', 'no_default'), "Row Test_row, no_default in primary_keys must be required or have default"),
    ('bogus', (), "Row Test_row, primary key bogus: not a column"),
    (None, ('req', 'bogus'), "Row Test_row, bogus in primary_keys: not a column"),
])
def test_create_error(pkey, pkeys, msg):
    calc = Column('calc', calculated=True) # default, required, can_edit not allowed by Column
    req = Column('req', required=True)
    with_default = Column('with_default', default=0)  # can't be primary_key, but primary_keys ok
    no_default = Column('no_default')

    with pytest.raises(AssertionError) as exc:
        class Test_row(Row):
            columns = (calc, req, with_default, no_default)
            primary_key = pkey
            primary_keys = pkeys

    assert str(exc.value) == msg


def test_create_error2():
    calc = Column('calc', calculated=True) # default, required, can_edit not allowed by Column
    req = Column('req', required=True)
    with_default = Column('with_default', default=0)  # can't be primary_key, but primary_keys ok
    no_default = Column('no_default')

    with pytest.raises(AssertionError) as exc:
        class Test_row(Row):
            columns = (calc, req, with_default)
            primary_key = 'req'
            primary_keys = ('with_default',)

    assert str(exc.value) == "Row Test_row can't have both primary_key and primary_keys"


@pytest.fixture
def Test_row():
    calc = Column('calc', calculated=True) # default, required, can_edit not allowed by Column
    req1 = Column('req1', required=True)
    req2 = Column('req2', required=True)
    with_default = Column('with_default', default=0)  # can't be primary_key, but primary_keys ok
    no_default = Column('no_default')
    can_edit_f = Column('can_edit_f', can_edit=False)

    class Test_row(Row):
        columns = (calc, req1, req2, with_default, no_default, can_edit_f)

    return Test_row


@pytest.mark.parametrize("with_default, no_default", [
    (None, None),
    ("bb", "cc"),
])
def test_init(Test_row, with_default, no_default):
    attrs = dict(req1="aa", req2="zz", can_edit_f="ww")
    if with_default is not None:
        attrs['with_default'] = with_default
    if no_default is not None:
        attrs['no_default'] = no_default
    r = Test_row(**attrs)
    assert r.table_name == "Test_row"
    assert r.req1 == "aa"
    assert r.req2 == "zz"
    assert r.can_edit_f == "ww"
    assert r.with_default == (with_default or 0)
    assert r.no_default == (no_default or None)


def test_init_unknown(Test_row):
    with pytest.raises(AssertionError) as exc:
        Test_row(req1="aa", req2="zz", bogus="bb", fungus="cc")
    assert str(exc.value) == "Test_row.__init__: unknown attrs=['bogus', 'fungus']"


def test_init_missing(Test_row):
    with pytest.raises(AssertionError) as exc:
        Test_row(no_default="bb")
    assert str(exc.value) == "Test_row.__init__: missing attrs=['req1', 'req2']"


@pytest.fixture
def test_row(Test_row):
    return Test_row(req1="aa", req2="zz", no_default="bb", can_edit_f="ww")


@pytest.mark.parametrize("attr", ('req1', 'with_default', 'no_default'))
def test_setattr(test_row, attr):
    setattr(test_row, attr, "xx")
    assert getattr(test_row, attr) == "xx"


@pytest.mark.parametrize("attr", ('calc', 'bogus', 'can_edit_f'))
def test_setattr_error1(test_row, attr):
    with pytest.raises(AssertionError):
        setattr(test_row, attr, "xx")


@pytest.mark.parametrize("attr", ('req1',))
def test_setattr_error_none(test_row, attr):
    with pytest.raises(ValueError):
        setattr(test_row, attr, None)


@pytest.mark.parametrize("attr", ('with_default', 'no_default'))
def test_setattr_none_ok(test_row, attr):
    setattr(test_row, attr, None)


@pytest.mark.parametrize("attr", ('no_default',))
def test_delattr(test_row, attr):
    delattr(test_row, attr)


@pytest.mark.parametrize("attr", ('calc', 'req1', 'req2', 'bogus', 'can_edit_f'))
def test_delattr_error(test_row, attr):
    with pytest.raises(AssertionError):
        delattr(test_row, attr)


@pytest.mark.parametrize("key, t, f", [
    ('col1__lt', 11, 10),
    ('col1__le', 10, 9),
    ('col1__eq', 10, 9),
    ('col1', 10, 9),
    ('col1__ne', 9, 10),
    ('col1__ge', 10, 11),
    ('col1__gt', 9, 10),
])
def test_selected(key, t, f):
    class Test_row(Row):
        columns = Column("col1", parse=int),
    row = Test_row(col1=10)
    assert row.selected(None, **{key: t})
    assert not row.selected(None, **{key: f})


def row_class(*keys):
    if len(keys) == 1:
        return Mock(primary_key=keys[0], primary_keys=None)
    return Mock(primary_key=None, primary_keys=keys)

def table(**key_values):
    key_value = tuple(key_values.values())
    if len(key_values) == 1:
        key_value = key_value[0]
    return Mock(row_class=row_class(*key_values.keys()), __contains__=lambda self, key: key == key_value)

@pytest.fixture
def tables():
    return dict(table1=table(key="value"), table2=table(key1="value1", key2="value2"))


@pytest.fixture
def row_with_fks():
    class Test_row(Row):
        columns = (
            Column("key", required=True),
            Column("key1", required=True),
            Column("key2"),
        )
        foreign_keys = ('table1', 'table2')
    return Test_row


@pytest.mark.parametrize("key_to_none", (None, 'key2'))
def test_check_foreign_keys(tables, row_with_fks, key_to_none):
    attrs = dict(key="value", key1="value1", key2="value2")
    if key_to_none is not None:
        del attrs[key_to_none]
    test_row = row_with_fks(**attrs)
    assert test_row.check_foreign_keys(tables, "row_id")


@pytest.mark.parametrize("key_to_change", ('key', 'key1', 'key2'))
def test_check_foreign_keys_error(tables, row_with_fks, key_to_change):
    test_row = row_with_fks(key="value", key1="value1", key2="value2")
    setattr(test_row, key_to_change, "bogus")
    assert not test_row.check_foreign_keys(tables, "row_id", raise_exc=False)


@pytest.mark.parametrize("key_to_change", ('key', 'key1', 'key2'))
def test_check_foreign_keys_exc(tables, row_with_fks, key_to_change):
    test_row = row_with_fks(key="value", key1="value1", key2="value2")
    setattr(test_row, key_to_change, "bogus")
    with pytest.raises(KeyError):
        assert not test_row.check_foreign_keys(tables, "row_id", raise_exc=True)


# Test_row has:
#   calc = Column('calc', calculated=True) # default, required, can_edit not allowed by Column
#   req1 = Column('req1', required=True)
#   req2 = Column('req2', required=True)
#   with_default = Column('with_default', default=0)  # can't be primary_key, but primary_keys ok
#   no_default = Column('no_default')
#   can_edit_f = Column('can_edit_f', can_edit=False)

@pytest.mark.parametrize("header, row", [
    (("req1", "req2", "with_default", "no_default", "can_edit_f"), ("r1", "r2", "wd", "nd", "cef")),
    (("req1", "req2", "with_default", "no_default  ", "can_edit_f  "), ("r1", "r2", "", "", "")),
    (("req1", "req2"), ("r1", "r2")),
])
def test_from_csv(Test_row, header, row):
    Test_row.from_csv(header, row)


@pytest.mark.parametrize("header, row", [
    (("req1", "req2", "with_default", "no_default", "can_edit_f"), ("r1", "r2", "wd", "nd", "cef", "extra")),
    (("req1", "req2", "with_default", "no_default", "can_edit_f"), ("r1", "r2", "wd", "nd")),
    (("req1", "req2", "with_default", "bogus", "can_edit_f"), ("r1", "r2", "", "", "")),
    (("req1", "req2", "with_default"), ("r1", "", "")),
    (("req1", "with_default"), ("r1", "wd")),
])
def test_from_csv_error(Test_row, header, row):
    with pytest.raises(AssertionError):
        Test_row.from_csv(header, row)
