# table.py

import os
import os.path
import csv
from operator import methodcaller
import logging

from tui_app.row_screen import row_screen
from .row import *
from .report import dump_table


logger = logging.getLogger('csv-app.table')
logger_execute = logging.getLogger('tui-app.execute')

def set_database_filename(database_filename):
    global Database_filename
    Database_filename = database_filename

CSV_dialect = 'excel'  # 'excel', 'excel-tab' or 'unix'
CSV_format = dict(delimiter='|', quoting=csv.QUOTE_NONE, skipinitialspace=True, strict=True)


def align(value, width, alignment):
    if alignment == 'right':
        return ' ' * (width - len(value)) + value
    return value + ' ' * (width - len(value))

class Base_table:
    def __init__(self, row_class):
        self.row_class = row_class
        row_class.table = self

    @property
    def screen_popup_commands(self):
        return tuple(table.name for table in Tables.values() if not table.row_class.omit) \
             + self.row_class.table_popup_commands_end

    @property
    def columns(self):
        return self.row_class.columns

    @property
    def name(self):
        return self.row_class.table_name

    def get_rows(self, app, **select):
       #logger.info(f"{self.name}({self.name=}).get_rows")
        return [row for row in self.values() if row.selected(app, **select)]

    def execute(self, screen, command):
        logger_execute.info(f"{self.name=}.execute({command=})")
        match command:
            case 'Print':
                dump_table(self.name, pdf=True, load=False)
                logger_execute.info(f"{self.name=}.execute -> None")
                return None
            case 'Create':
                screen.app.set_changed()
                ans = row_screen.for_create(self, screen)
                logger_execute.info(f"{self.name=}.execute -> {ans}")
                return ans
            case _:
                logger_execute.info(f"{self.name=}.execute: unknown -> 'Continue'")
                return 'Continue'

    def check_foreign_keys(self):
        r'''Returns the number of errors found.
        '''
        errors = 0
        for row_num, row in enumerate(self.values(), 1):
            if not row.check_foreign_keys(Tables, row_num, False):
                errors += 1
        return errors

    def insert(self, skip_fk_check=False, **attrs):
        r'''Attributes may not be set to None.  Instead omit the attribute from `attrs`.

        The values in attrs are python values (not just strings).
        '''
        self.add_row(self.row_class(**attrs), skip_fk_check=skip_fk_check)

    def insert_from_csv(self, header, row, ignore_unknown_cols=False, skip_fk_check=False):
       #print(f"{self.name}.insert_from_csv({header=}, {row=})")
        self.add_row(self.row_class.from_csv(header, row, ignore_unknown_cols=ignore_unknown_cols),
                     skip_fk_check=skip_fk_check)

    def from_csv(self, csv_reader, from_scratch=True, ignore_unknown_cols=False, skip_fk_check=False):
        r'''Loads rows from csv_reader.  First row is header row that identifies the attrs.

        If from_scratch is False, appends the rows to the current contents; otherwise it replaces
        the current contents.

        Returns the number of rows inserted.
        '''
        if from_scratch:
            self.clear()
        header = next(csv_reader)
        try:
            num_rows = 0
            while True:
                row = next(csv_reader)
                if len(row) == 0:
                    break
                self.insert_from_csv(header, row, ignore_unknown_cols=ignore_unknown_cols,
                                     skip_fk_check=skip_fk_check)
                num_rows += 1
        except StopIteration:
            pass
        return num_rows

    def to_csv(self, file, add_table_name=True, add_empty_row=False):
        r'''Writes itself in database csv format to `file`.
        '''
        if add_table_name:
            print(self.name, file=file)                 # first line is name of table (only one column)
        widths = {}
        alignments = {}
        headers = tuple(self.row_class.stored_names)
        header_row = []
        for name in headers:
            max_width = len(name)
            alignment = self.row_class.column_map[name].alignment
            alignments[name] = alignment
            for row in self.values():
                if getattr(row, name) is not None:
                    width = len(row.csv_value(name))
                    if width > max_width:
                        max_width = width
            widths[name] = max_width
            header_row.append(align(name, max_width, alignment))
        print('|'.join(header_row), file=file)
        for row in self.to_csv_rows():
            values = []
            for name in headers:
                value = row.csv_value(name)
                if not value:
                    values.append(' ' * widths[name])
                else:
                    values.append(align(value, widths[name], alignments[name]))
            print('|'.join(values), file=file)          # data line.
        if add_empty_row:
            print(file=file)                            # empty row terminator

    def dump(self):
        r'''Dumps the table to stdout, one line per row.
        '''
        print(f"{self.name}:")
        for row in self.values():
            print('   ', end='')
            row.dump()

class Table_unique(Base_table, dict):
    def __init__(self, row_class):
        Base_table.__init__(self, row_class)
        dict.__init__(self)

    def to_csv_rows(self):
        return sorted(self.values(), key=methodcaller("key"))

    def add_row(self, row, skip_fk_check=False):
        key = row.key()
        if not skip_fk_check:
            row.check_foreign_keys(Tables, key, raise_exc=True)
        if key in self:
            # ValueError (not assert) so the create path can catch it and show a message
            raise ValueError(f"{self.name}: duplicate key {key!r}")
        self[key] = row

    def delete_row(self, row):
        logger.info(f"{self.__class__.__name__}({self.name=}).delete_row({row.key()=})")
        del self[row.key()]

class Table_by_date(Base_table, list):
    def __init__(self, row_class):
        Base_table.__init__(self, row_class)
        list.__init__(self)

    def append(self, item):
        raise NotImplementedError(f"{self.name}.append")

    def extend(self, item):
        raise NotImplementedError(f"{self.name}.extend")

    def first_date(self, date):
        r'''Returns index to the first date == `date`.
        '''
        return self.find_date(date, find_first=True)

    def last_date(self, date):
        r'''Returns index to smallest date > `date`.
        '''
        return self.find_date(date, find_first=False)

    def find_date(self, date, find_first):
        r'''This returns the index at which to insert `date`.

        The find_first parameter disambiguates the case where one or more matching dates already
        appear in the file.

        If find_first is True, `date` will be inserted _before_ all other matching dates.  This means that
        the index returned is to the first matching date.

        If find_first is False, `date` will be inserted _after_ all other matching dates.  This means that
        the index returned is just after the last matching date.  It also means that the index returned
        may equal length of the file, meaning that it does not point to any row in the file.

        If no matching dates appear in the file, this will return the index to the first date > `date`
        regardless of find_first.
        '''
        first = 0              # ignore < first
        last = len(self)       # ignore >= last
        while first < last:
            i = (last + first) // 2  # might be first, but never last
            if date < self[i].date:
                last = i
            elif date > self[i].date:
                first = i + 1
            elif find_first:
                last = i
            else:
                first = i + 1
        # first == last
        return first

    def to_csv_rows(self):
        return self

    def add_row(self, row, skip_fk_check=False):
        i = self.last_date(row.date)
       #print(f"{self.name}.add_row(date={row.date}), inserted at {i=}")
        list.insert(self, i, row)
        if not skip_fk_check:
            row.check_foreign_keys(Tables, row.date, raise_exc=True)

    def delete_row(self, row):
        logger.info(f"{self.__class__.__name__}({self.name=}).delete_row({row.row_num=})")
        del self[row.row_num]

    def values(self):
        return self

    def get_rows(self, app, **select):
        ans = []
        for row_num, row in enumerate(self, 1):
            if row.selected(app, **select):
                row.set_row_num(row_num)
                ans.append(row)
       #logger.info(f"Table_by_date({self.name=}).get_rows: {ans[0].row_num=}")
        return ans

Tables = {}

class DB:
    def load(self):
        for name, table in Tables.items():
            setattr(self, name, table)

Database = DB()

def load_rows(rows, *custom_tables):
    custom_map = {cls.__name__: cls for cls in custom_tables}
    def table_for_row(row_class):
        if row_class.table_name in custom_map:
            return custom_map[row_class.table_name](row_class)
        if row_class.primary_key is not None or row_class.primary_keys:
            return Table_unique(row_class)
        assert 'date' in row_class.required, f"{row_class.table_name} must have primary_key/s or date"
        return Table_by_date(row_class)
    for row_class in rows:
        Tables[row_class.table_name] = table_for_row(row_class)
    Database.load()


__all__ = "Decimal date datetime timedelta abbr_month Date_format Datetime_format " \
          "Tables Database load_rows Table_unique Table_by_date " \
          "load_database save_database load_csv load_all clear_all check_foreign_keys " \
          "CSV_dialect CSV_format set_database_filename run".split()


def load_database(csv_filename=None, ignore_unknown_cols=False):
    r'''Loads all database tables in csv_filename from scratch skipping fk_check.
    '''
    if csv_filename is None:
        csv_filename = Database_filename
    with open(csv_filename, 'r') as f:
        reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        while True:
            try:
                header = next(reader)
                assert len(header) == 1, f"from_csv: Expected table name, got {header}"
                Tables[header[0].strip()].from_csv(reader, ignore_unknown_cols=ignore_unknown_cols,
                                                   skip_fk_check=True)
            except StopIteration:
                break

def save_database(csv_filename=None):
    if csv_filename is None:
        csv_filename = Database_filename
    temp_filename = csv_filename + '-new'
    with open(temp_filename, 'w') as f:
        for table in Tables.values():
            if table.row_class.in_database:
                table.to_csv(f, add_empty_row=True)
    save_filename = csv_filename + '-save'
    if os.path.exists(save_filename):
        os.remove(save_filename)
    os.link(csv_filename, save_filename)     # creates hard link: save_filename points to csv_filename
    os.replace(temp_filename, csv_filename)  # renames temp_filename to csv_filename atomically,
                                             # replacing csv_filename

def load_csv(csv_filename, from_scratch=True, ignore_unknown_cols=False):
    r'''Loads table from csv_filename.

    clears current contents of table if from_scratch is True, otherwise, rows are appended.

    If csv_filename has no .csv suffix, one is added.

    Returns the number of rows inserted.
    '''
    if not csv_filename.endswith(".csv"):
        csv_filename += ".csv"
    with open(csv_filename, 'r') as f:
        csv_reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        row1 = next(csv_reader)
        assert len(row1) == 1, f"load_csv: Expected table name, got {row1=}"
        table_name = row1[0].strip()
        return Tables[table_name].from_csv(csv_reader, from_scratch=from_scratch, ignore_unknown_cols=ignore_unknown_cols)

def load_all(from_scratch=True, ignore_unknown_cols=False):
    for table in Tables.values():
        if os.path.exists(f"{table.name}.csv"):
            print("loading:", table.name)
            load_csv(table.name, from_scratch=from_scratch, ignore_unknown_cols=ignore_unknown_cols)
        else:
            print("load_all: skipping", table.name)

def clear_all():
    for table in reversed(Tables.values()):
        table.clear()

def check_foreign_keys():
    errors = 0
    for table in Tables.values():
        errors += table.check_foreign_keys()
    if errors:
        print("Total errors:", errors)
    else:
        print("No errors found")

def run():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", "-i", action="store_true", default=False, help="init database to all empty tables")
    parser.add_argument("--ignore-unknown-cols", "-u", action="store_true", default=False)
    parser.add_argument("--load", "-l", default=None, help="load one separate csv table")
    parser.add_argument("--save", "-s", default=None, help="save one separate csv table")
    parser.add_argument("--load-all", "-a", action="store_true", default=False, help="load all separate csv tables")
    parser.add_argument("--no-save", "-n", action="store_true", default=False, help="skip final database save")
    parser.add_argument("--check-foreign-keys", "-c", action="store_true", default=False)

    args = parser.parse_args()

    if args.init:
        # create empty database csv file.
        clear_all()
    else:
        load_database(ignore_unknown_cols=args.ignore_unknown_cols)
    if args.load_all:
        load_all(from_scratch=True, ignore_unknown_cols=args.ignore_unknown_cols)
    elif args.load is not None:
        print("loading:", args.load + '.csv')
        load_csv(args.load, ignore_unknown_cols=args.ignore_unknown_cols)
    if args.check_foreign_keys:
        check_foreign_keys()
    if args.save is not None:
        with open(f"{args.save}.csv", "w") as f:
            print("saving:", args.save + '.csv')
            Tables[args.save].to_csv(f)

    if not args.no_save:
        save_database()
