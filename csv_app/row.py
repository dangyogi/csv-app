# row.py

from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timedelta
from copy import copy

from tui_app.row_screen import row_screen
from .trace import trace


# date.weekday numbers:
MONDAY    = 0
TUESDAY   = 1
WEDNESDAY = 2
THURSDAY  = 3
FRIDAY    = 4
SATURDAY  = 5
SUNDAY    = 6

Months_abbreviated = (None,
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
)

def abbr_month(m):
    r'''abbr_month(mth_num) returns the 3 letter abbreviation for the month's name.
    '''
    return Months_abbreviated[m]

Date_format = "%b %d, %y"               # Nov 03, 26
Datetime_format = "%I:%M%P, %b %d, %y"  # 01:14pm, Nov 03, 26


class Column:
    r'''Handles reading in, validating, and writing out the cell values for one column.
    '''
    alignment = 'left'

    def __init__(self, name, abbr=None, hidden=False, required=False, calculated=False, 
                 parse=None, default=None, choices=None, min_width=None, edit_width=None, can_edit=None):
        self.name = name
        self.abbr = abbr or name  # for column names in reports
        self.hidden = hidden
        if parse is not None:
            self.parse = parse
            self.alignment = 'right'
        if calculated:
            assert default is None, f"Column {name}: calculated column can't have default"
            assert not required, f"Column {name}, calculated column can't be required"
            assert not can_edit, f"Column {name}, calculated column can't be editable"
            can_edit = False
        self.calculated = calculated
        if required:
            assert default is None, f"Column {name}: required column can't have default"
        elif not calculated and default is None:
            self.default = default
        self.required = required
        if default is not None:
            self.default = default
        if choices is None:
            self.choices = None
        else:
            self.choices = frozenset(choices)
        self.min_width = min_width
        self.edit_width = edit_width
        self.can_edit = can_edit

    def validate(self, s):
        if self.parse(s) is None and self.required:
            raise ValueError(f"{self.name}: requires a value")

    def column_attr_pair(self, row):
        return None

    def to_python(self, csv_value):
        r'''Converts a string from a csv column to a python value.

        Raises ValueError if csv_value is not a legal value.

        See to_csv(value) for the reverse.
        '''
        if not isinstance(csv_value, str):
            return self.parse(csv_value)
        s = csv_value.strip()
        if not s:
            return None
        try:
            return self.parse(s)
        except InvalidOperation as e:
            raise ValueError(str(e))

    def parse(self, s):
        r'''Default parse.
        '''
        if self.choices and s not in self.choices:
            raise ValueError(f"{self.name}: {s!r} not in {self.choices}")
        return s

    def to_csv(self, value):
        r'''Converts python value to a string for a csv column.

        See to_python(csv_value) for the reverse.
        '''
        if value is None:
            return ''
        return self._convert(value)

    def _convert(self, value):
        r'''Used by to_csv().
        '''
        ans = str(value)
        if self.choices and ans not in self.choices:
            raise ValueError(f"{self.name}.to_csv: {ans!r} not in {self.choices}")
        return ans

class Custom_column(Column):
    def __init__(self, name, abbr=None, hidden=False, required=False, calculated=False):
        super().__init__(name, abbr, hidden, required, calculated)

class Date_column(Custom_column):
    edit_width = len("Nov 11, 26")

    def parse(self, s):
       #if isinstance(s, date):
       #    return s
        try:
            return date.fromisoformat(s)
        except ValueError:
            pass
        return datetime.strptime(s, Date_format).date()

    def _convert(self, date_value):
        return date_value.strftime(Date_format)

class Datetime_column(Custom_column):
    edit_width = len("01:14pm, Nov 03, 26")

    def parse(self, s):
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass
        return datetime.strptime(s, Datetime_format)

    def _convert(self, date_value):
        return date_value.strftime(Datetime_format)

class Set_column(Custom_column):
    r'''Assumes a set of strings.
    '''
    def parse(self, s):
       #if isinstance(s, set):
       #    return s
        return set(x.strip() for x in s.split(','))

    def _convert(self, set_value):
        return ','.join(sorted(set_value))

class Bool_column(Custom_column):
    edit_width = len("False")

    alignment = 'right'

    def parse(self, s):
       #if isinstance(s, bool):
       #    return s
        if s == 'True':
            return True
        elif s == 'False':
            return False
        raise ValueError(f"{self.name}: {s!r} not a valid bool value")

    def _convert(self, bool_value):
        if bool_value:
            return "True"
        return "False"


class Row_metaclass(type):
    r'''Sets column_map, stored_names, required and default values on cls from cls.columns.
    '''
    def __new__(cls, name, bases, dct):
        if 'columns' in dct:
            dct['column_map'] = {col.name: col for col in dct['columns']}
            dct['stored_names'] = [col.name for col in dct['columns'] if not col.calculated]
            dct['required'] = frozenset(col.name for col in dct['columns'] if col.required)
            assert dct.get('primary_key') is None or not dct.get('primary_keys', ()), \
                   f"Row {name} can't have both primary_key and primary_keys"
            has_key = False
            if dct.get('primary_key') is not None:
                assert dct['primary_key'] in dct['column_map'], \
                       f"Row {name}, primary key {dct['primary_key']}: not a column"
                has_key = True
            for pkey in dct.get('primary_keys', ()):
                assert pkey in dct['column_map'], f"Row {name}, {pkey} in primary_keys: not a column"
                has_key = True
           #if not has_key and 'row_num' not in dct['column_map']:
           #    row_num = Column('row_num', parse=int, calculated=True)
           #    dct['columns'] = tuple([row_num] + list(dct['columns']))
           #    dct['column_map']['row_num'] = row_num
            for col in dct['columns']:
                col_name = col.name
               #print(f"Row_metaclass({name=}).__new__: "
               #      f"col_name={col_name}, {hasattr(col, 'can_edit')=}, {dct.get('primary_key', None)=}")
                if col_name == dct.get('primary_key', None) or \
                   col_name in dct.get('primary_keys', ()):
                    assert not col.calculated, f"Row {name}, primary key {col_name} can't be calculated"
                    if dct.get('primary_keys', ()):
                       #print(f"Row_metaclass({name=}).__new__: {col_name=}, {dct['primary_keys']=}, "
                       #      f"{col.required=}, {hasattr(col, 'default')=}")
                        assert col.required or hasattr(col, "default") and col.default is not None, \
                               f"Row {name}, {col_name} in primary_keys must be required or have default"
                    else:
                        assert col.required, f"Row {name}, primary key {col_name} must be required"
                        assert not hasattr(col, "default"), \
                               f"Row {name}, primary key {col_name} can't have default"
                   #print(f"Row_metaclass.__new__({col_name=}): setting col.name={col_name}.can_edit to False")
                    if col.can_edit is None:
                        col.can_edit = False
                elif col.can_edit is None:
                    col.can_edit = True
                if hasattr(col, "default"):
                    dct[col.name] = col.default
        return super().__new__(cls, name, bases, dct)

class Row(metaclass=Row_metaclass):
    r'''One row in a database table.

    These have normal object attributes that can be read/set.  When the database is saved, these
    new values will be written to the database file.

    Default values are done with class attributes.  Any missing or empty columns in an imported csv file
    are not set as attributes and default to the class attribute.  As a result, row attributes may not
    be set to None.

    Additional non-stored attributes (similar to relational view) are simply done with a standard
    python @property.
    '''
    primary_key = None
    primary_keys = None
    foreign_keys = ()
    in_database = True
    omit = False                                 # used by tui-app to omit from menu of tables

    table_popup_commands_end = 'Create', 'Print'
    row_popup_commands_start = 'View/Edit',
    row_popup_command_fns = ()                   # names of methods to execute the commands.
                                                 # these methods take a single (tui) app parameter
    row_popup_commands_end = 'Cancel',
    row_screen_commands = ()

    def __init__(self, create=False, **attrs):
        r'''Not called by user app directly.  Use table.insert instead.
        '''
        super().__setattr__("create", create)
        attrs_in = frozenset(name.strip() for name in attrs.keys())
        unknown_attrs = attrs_in.difference(self.stored_names)
        assert not unknown_attrs, f"{self.table_name}.__init__: unknown attrs={sorted(unknown_attrs)}"
        if not create:
            self.check_required(attrs_in)
        for name, value in attrs.items():
            if value is None:
                raise ValueError(f"{self.table_name}.__init__, column {name}: "
                                 "None is illegal value for any row attribute, omit from attrs instead")
            super().__setattr__(name, value)

    def copy(self):
        return copy(self)

    def check_required(self, attrs_in):
        missing_attrs = self.required.difference(attrs_in)
        assert not missing_attrs, f"{self.table_name}.check_required: missing attrs={sorted(missing_attrs)}"

    def __setattr__(self, name, value):
        assert name in self.stored_names, \
               f"{self.table_name}.__setattr__({name=}, {value=}): unknown column"
        assert self.create and not self.column_map[name].calculated or self.column_map[name].can_edit, \
               f"{self.table_name}.__setattr__({name=}, {value=}): can not set non-editable column"
        if value is None:
            if name in self.__dict__:
                try:
                    delattr(self, name)
                except AssertionError as exc:
                    raise ValueError(str(exc))
        else:
            super().__setattr__(name, value)

    def set_row_num(self, row_num):
        super().__setattr__('row_num', row_num)

    def __delattr__(self, name):
        assert name in self.stored_names, \
               f"{self.table_name}.__delattr__({name=}): unknown column"
        assert self.column_map[name].can_edit, \
               f"{self.table_name}.__delattr__({name=}): can not del non-editable column"
        assert not self.column_map[name].required, \
               f"{self.table_name}.__delattr__({name=}): can not del required column"
        super().__delattr__(name)

    @property
    def row_popup_commands(self):
        return self.row_popup_commands_start + self.row_popup_command_fns + self.row_popup_commands_end

    def get(self, column_name):
        r'''Returns value as string for display.
        '''
        return self.csv_value(column_name)

    def set(self, column_name, s):
        r'''Takes value as string.
        '''
        column = self.column_map[column_name]
        value = column.to_python(s)
        if value is None and column.required:
            raise ValueError(f"{column_name}: requires a value")
        setattr(self, column_name, value)

    def selected(self, app, **select):
        r'''Checks select clause for table.get_rows.
        '''
        for key, value in select.items():
            if '__' in key:
                key, op = key.split('__')
            else:
                op = 'eq'
            my_value = getattr(self, key, None)
           #print(f"row({self.table_name}).selected: {key=}, {op=}, {my_value=}, {value=}")
            match op:
                case 'lt':
                    if not (my_value < value):
                        return False
                case 'le':
                    if not (my_value <= value):
                        return False
                case 'eq':
                    if my_value != value:
                        return False
                case 'ne':
                    if my_value == value:
                        return False
                case 'ge':
                    if not (my_value >= value):
                        return False
                case 'gt':
                    if not (my_value > value):
                        return False
                case _:
                    raise AssertionError(f"row({self.table_name}).selected got unknown {op=}")
        return True

    def check_foreign_keys(self, tables, row_id, raise_exc=True):
        r'''Returns True if all tests pass.
        '''
        ans = True
        for table_name in self.foreign_keys:
            table = tables[table_name]
            if table.row_class.primary_key is not None:
                key = getattr(self, table.row_class.primary_key, None)
               #print(f"{self.table_name}.check_foreign_keys: {table.row_class.primary_key=}, {key=}")
                if key is None:
                    continue
            else:
                assert table.row_class.primary_keys, \
                       f"{self.name}.check_foreign_keys: {table_name=} has no primary_key"
                key = tuple(getattr(self, key, None) for key in table.row_class.primary_keys)
               #print(f"{self.table_name}.check_foreign_keys: {table.row_class.primary_keys=}, {key=}")
                if any(k is None for k in key):
                    continue
            if key not in table:
                error_msg = f"{self.table_name}.check_foreign_keys({row_id=}): " \
                            f"{key=} not in {table_name}"
                if raise_exc:
                    raise KeyError(error_msg)
                else:
                    print(error_msg)
                ans = False
        return ans

    @classmethod
    @property
    def table_name(cls):
        return cls.__name__

    @classmethod
    def from_csv(cls, header, row, ignore_unknown_cols=False):
        r'''strips both the names in header and the values in row.

        attrs with an empty value are not loaded, so that they have their default values.
        '''
        attrs = {}
        assert len(header) == len(row), \
               f"{cls.table_name}.from_csv: len(header)={len(header)} != len(row)={len(row)}"
        for name, value in zip(header, row):
            name = name.strip()
            value = value.strip()
            if name not in cls.stored_names:
                if not ignore_unknown_cols:
                    raise AssertionError(f"{cls.table_name}.from_csv: unknown attr={name}")
            elif value:
                python_value = cls.column_map[name].to_python(value)
                if python_value is not None:
                    attrs[name] = python_value
        return cls(**attrs)

    def csv_value(self, name):
        return self.column_map[name].to_csv(getattr(self, name, None))

    def key(self):
        if self.primary_key is not None:
            return getattr(self, self.primary_key)
        return tuple(getattr(self, key) for key in self.primary_keys)

    def human_key(self):
        if self.primary_key is not None:
            return self.get(self.primary_key)
        if self.primary_keys is not None:
            return ', '.join(self.get(key) for key in self.primary_keys)
        return str(self.row_num)

    def execute(self, app, command):
        r'''Run from row popup on table screen.
        '''
        trace(f"Row({self.table_name=}).execute({command=})")
        match command:
            case "View/Edit":
                return row_screen.for_update(self, app.screen)
            case "Delete":
                self.table.delete_row(self)
                app.set_changed()
                return 'REFRESH'
            case "Cancel":  # just closes the popup
                return None
        if command not in self.row_popup_commands:
            trace(f"Row({self.table_name=}).execute: {command=} unknown")
            raise ValueError(f"Row({self.table_name=}).execute: {command=} unknown")
        return getattr(self, command)(app)

    def dump(self):
        r'''Appends attr values onto end of current print line.

        Ends with newline.
        '''
        for i, attr in enumerate(self.stored_names):
            if i:
                print(', ', end='')
            print(f"{attr}={getattr(self, attr, None)}", end='')
        print()


__all__ = "MONDAY TUESDAY WEDNESDAY THURSDAY FRIDAY SATURDAY SUNDAY " \
          "date datetime timedelta abbr_month Date_format Datetime_format trace " \
          "Decimal Column Date_column Datetime_column Set_column Bool_column Row create_database_py".split()


def create_database_py(Rows, table_module="tables"):
    from pathlib import Path

    with open("database.py", 'w') as f:
        print(
f"""# database.py

# Do not edit!  This is machine generated by running "python rows.py".

if not __package__:
    __package__ = {Path.cwd().name!r}

from .{table_module} import *

""", file=f)
        for t in Rows:
            print(f"{t.table_name} = Tables['{t.table_name}']", file=f)
            print(file=f)

