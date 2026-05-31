# row.py

from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timedelta


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

Date_format = "%b %d, %y"


class Column:
    r'''Handles reading in, validating, and writing out the cell values for one column.
    '''
    alignment = 'left'
    omit = False

    def __init__(self, name, abbr=None, hidden=False, required=False, calculated=False, 
                 parse=None, default=None, choices=None, min_width=None, can_edit=None, omit=None):
        self.name = name
        self.abbr = abbr or name  # for column names in reports
        self.hidden = hidden
        self.required = required
        self.calculated = calculated
        if parse is not None:
            self.parse = parse
            self.alignment = 'right'
        if not required:
            self.default = default
        if choices is None:
            self.choices = None
        else:
            self.choices = frozenset(choices)
        self.min_width = min_width
        self.can_edit = can_edit
        if omit is not None:
            self.omit = omit

    def to_python(self, csv_value):
        if not isinstance(csv_value, str):
            return self.parse(csv_value)
        s = csv_value.strip()
        if not s:
            return None
        return self.parse(s)

    def parse(self, s):
        return s

    def to_csv(self, value):
        if value is None:
            return ''
        return self.convert(value)

    def convert(self, value):
        if value is None:
            return ""
        ans = str(value)
        if self.choices:
            assert ans in self.choices, f"{self.name}.convert: {ans!r} not in {self.choices}"
        return ans

class Custom_column(Column):
    def __init__(self, name, abbr=None, hidden=False, required=False, calculated=False):
        super().__init__(name, abbr, hidden, required, calculated)

class Date_column(Custom_column):
    def parse(self, s):
        if isinstance(s, date):
            return s
        try:
            return date.fromisoformat(s)
        except ValueError:
            pass
        return datetime.strptime(s, Date_format).date()

    def convert(self, date_value):
        if date_value is None:
            return ""
        return date_value.strftime(Date_format)

class Set_column(Custom_column):
    r'''Assumes a set of strings.
    '''
    def parse(self, s):
        if isinstance(s, set):
            return s
        return set(x.strip() for x in s.split(','))

    def convert(self, set_value):
        if set_value is None:
            return ""
        return ','.join(sorted(set_value))

class Bool_column(Custom_column):
    alignment = 'right'

    def parse(self, s):
        if isinstance(s, bool):
            return s
        if s == 'True':
            return True
        elif s == 'False':
            return False
        raise ValueError(f"{self.name}.parse({s=}): not a valid bool value")

    def convert(self, bool_value):
        if bool_value is None:
            return ""
        if bool_value:
            return "True"
        return "False"


class Row_metaclass(type):
    r'''Sets column_map, stored_names, required and default values on cls from cls.columns.
    '''
    def __new__(cls, name, bases, dct):
        if 'columns' in dct:
            dct['column_map'] = {col.name.lower(): col for col in dct['columns']}
            dct['stored_names'] = [col.name.lower() for col in dct['columns'] if not col.calculated and not col.omit]
            dct['required'] = frozenset(col.name.lower() for col in dct['columns'] if col.required)
            for col in dct['columns']:
                col_name = col.name
               #print(f"Row_metaclass({name=}).__new__({col_name=}): col_name={col_name}, {hasattr(col, 'can_edit')=}, "
               #      f"{dct.get('primary_key', None)=}")
                if col.can_edit is None:
                    if col_name.lower() == dct.get('primary_key', None) or \
                       col_name.lower() in dct.get('primary_keys', ())  or \
                       col.calculated:
                       #print(f"Row_metaclass.__new__({col_name=}): setting col.name={col_name}.can_edit to False")
                        col.can_edit = False
                    else:
                        col.can_edit = True
                if not col.calculated and not col.required:
                    dct[col.name] = col.default
        return super().__new__(cls, name, bases, dct)

class Row(metaclass=Row_metaclass):
    r'''One row in a database table.

    These have normal object attributes that can be read/set.  When the database is saved, these
    new values will be written to the database file.

    Default values are done with class attributes.  Any missing or empty columns in an imported csv file
    are not set as attributes and default to the class attribute.

    Additional non-stored attributes (similar to relational view) are simply done with a standard
    python @property.
    '''
    primary_key = None
    primary_keys = None
    foreign_keys = ()
    in_database = True
    omit = False
    row_popup_commands = 'View/Edit', 'Delete', 'Cancel'
    commands = ()

    def __init__(self, **attrs):
        attrs_in = frozenset(name.strip().lower() for name in attrs.keys())
        unknown_attrs = attrs_in.difference(self.stored_names)
        assert not unknown_attrs, f"{self.table_name}.__init__: unknown attrs={tuple(unknown_attrs)}"
        missing_attrs = self.required.difference(attrs_in)
        assert not missing_attrs, f"{self.table_name}.__init__: missing attrs={sorted(missing_attrs)}, " \
                                  f"got {sorted(attrs_in)}"
        for name, value in attrs.items():
            name = name.strip().lower()
            python_value = self.column_map[name].to_python(value)
            if python_value is not None:
                setattr(self, name, python_value)

    def get(self, column_name):
        r'''Returns value as string for display.
        '''
        return self.column_map[column_name.lower()].convert(getattr(self, column_name))

    def check_foreign_keys(self, tables, row_id, raise_exc=True):
        r'''Returns True if all tests pass.
        '''
        ans = True
        for table_name in self.foreign_keys:
            table = tables[table_name]
            if table.row_class.primary_key is not None:
                key = getattr(self, table.row_class.primary_key)
                if key is None:
                    continue
            else:
                assert table.row_class.primary_keys, \
                       f"{self.name}.check_foreign_keys: {table=} has no primary_key"
                key = tuple(getattr(self, key) for key in table.row_class.primary_keys)
                if any(k is None for k in key):
                    continue
            if key not in table:
                error_msg = f"{self.__class__.__name__}.check_foreign_keys({row_id=}): " \
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

        names in header are converted to lowercase as key for cls.column_map.

        attrs with an empty value are not loaded, so that they have their default values.
        '''
        attrs = {}
        assert len(header) == len(row), \
               f"{cls.table_name}.from_csv: len(header)={len(header)} != len(row)={len(row)}"
        for name, value in zip(header, row):
            name = name.strip().lower()
            value = value.strip()
            if name not in cls.stored_names:
                if not ignore_unknown_cols:
                    raise AssertionError(f"{cls.table_name}.from_csv: unknown attr={name}")
            else:
                python_value = cls.column_map[name].to_python(value)
                if python_value is not None:
                    attrs[name] = python_value
        return cls(**attrs)

    def csv_value(self, name):
        return self.column_map[name].to_csv(getattr(self, name))

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
        print(f"Row({self.table_name=}).execute: {command=} unknown", file=app.trace_file)
        raise ValueError(f"Row({self.table_name=}).execute: {command=} unknown")

    def dump(self):
        r'''Appends attr values onto end of current print line.

        Ends with newline.
        '''
        for i, attr in enumerate(self.stored_names):
            if i:
                print(', ', end='')
            print(f"{attr}={getattr(self, attr)}", end='')
        print()


# FIX: Not used...
def convert(s):
    r'''Converts a string, s, into one of the following python objects.

    Strips whitespace from s first.

    These are tried in the following order:

      - None (if s is empty string)
      - int
      - date in ISO format
      - date in Mon dd, yy format
      - Decimal (with two digits after the '.')
      - float
      - else str (stripped)
    '''
    s = s.strip()
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return date.fromisoformat(s)
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%b %d, %y").date()
    except ValueError:
        pass
    i = s.find('.')
    if i >= 0 and i + 3 == len(s):
        # Has 2 chars after the '.'
        try:
            return Decimal(s)
        except InvalidOperation:
            pass
    try:
        return float(s)
    except ValueError:
        pass
    return s



__all__ = "MONDAY TUESDAY WEDNESDAY THURSDAY FRIDAY SATURDAY SUNDAY " \
          "date datetime timedelta abbr_month Date_format " \
          "Decimal Column Date_column Set_column Bool_column Row create_database_py".split()


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

