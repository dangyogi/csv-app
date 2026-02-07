# report.py

r'''Reports, both pdf and text, in rows and columns

Steps:

    1. Initialize the ReportLab canvas:

        set_canvas(filename, path=Path("~/Documents/"), landscape=False):

    2. Create Report object:

        report = Report("T-Report",  # this will be the filename

                        title=(Centered(span=2, size="title", bold=True),),
                        l0=(Left(bold=True), Right()),
                        l1=(Left(indent=1, bold=True), Right(indent=1)),
                        l2=(Left(indent=2, bold=True), Right(indent=2)),
                        l3=(Left(indent=3), Right(indent=3)),
                       )

    3. Create a row.  These will be output in the order created:

        title_row = report.new_row("title")        # can also provide the values to the first N rows as additional args
    
    4. Add text to columns.  This may be done after other rows are created.

        title_row.next_cell("Treasurer's Report")  # can override size and/or bold here

        # optional:
        title_row.set_text2("...")                 # Tack text onto the end of the last cell.
                                                   # Can specify bold (default False).

    5. initialize the report.  These print the size of the report to stdout:

        report.draw_init()
     or report.print_init()

    6. generate the report:

        report.draw()   # may send x_offset and/or y_offset (from top) to transpose report on page
                        # file generated in ~/Documents/<report-name>.pdf
     or report.print()  # may send file argument, otherwise report is sent to stdout.

'''

# letter page size is 612 x 792

# y values:
#   top of "l"                         =  71.8%
#   top of "g"                         =  54%
#   bottom of "l"                      =   0%
#   bottom of "g" (excluding decender) =  -1%
#   bottom of "g" decender             = -22%
#
# x values:
#   left of "g"                        =   4%
#   right of "g"                       =  50.02%
#   width of "g"                       =  46.02%
#   right of "l"                       =  74.8%
#   right of stringWidth("gl")         =  83.4%
#   stringWidth("g")           360.288 =  55.6%
#   stringWidth("l")           143.856 =  22.2%
#   stringWidth(" ")           180.144 =  27.8%

# canvas.setPageSize(pair)
# canvas.transform(a,b,c,d,e,f):
# canvas.translate(dx, dy)
# canvas.scale(x, y)
# canvas.rotate(theta)
# canvas.skew(alpha, beta)

from pathlib import Path
import sys

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape as Landscape, portrait as Portrait, letter, inch


__all__ = "set_canvas get_pagesize set_landscape canvas_showPage canvas_save Report " \
          "Left Centered Right Value Row_template dump_table".split()


Canvas = None
Pagesize = None
Page_width = None
Page_height = None

def set_canvas(filename, path=Path("~/Documents/"), landscape=False):
    global Canvas, Pagesize, Page_width, Page_height
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    path = (path / filename).expanduser()
    if landscape:
        Pagesize = Landscape(letter)
    else:
        Pagesize = Portrait(letter)
    Page_width, Page_height = Pagesize
    Canvas = canvas.Canvas(str(path), pagesize=Pagesize)

def get_pagesize():
    return Pagesize

def set_landscape():
    global Pagesize, Page_width, Page_height
    Pagesize = Landscape(letter)
    Page_width, Page_height = Pagesize
    print(f"set_landscape({Pagesize})")
    Canvas.setPageSize(Pagesize)

def canvas_showPage():
    Canvas.showPage()

def canvas_save():
    Canvas.save()

class Report:
    default_font = 'Helvetica'
    default_bold = 'Helvetica-Bold'
    default_size = 13
    title_size   = 17

    indent_chars  = 4
    indent_points = indent_chars * default_size * 0.278

    col_gap_chars = 2
    col_gap_points = col_gap_chars * default_size * 0.278

    text2_gap_percent = 0.278

    def __init__(self, default_size=None, **row_layout_cols):
        if default_size is not None:
            self.default_size = default_size

        # Column_layouts
        self.columns = {}
        self.name_suffixes = {}   # {col_name: next_suffix}
        self.col_x_starts = None
        self.col_x_char_starts = None

        # Row_layouts
        self.row_layouts = {}     # {row_name: row_layout}
        last_right_index = None
        for rl_name, cols in row_layout_cols.items():
            col_index = 0
            for col in cols:
                col.set_report(self, col_index)
                col_index = col.right_index + col.skip
            assert last_right_index is None or last_right_index == col_index, \
                   f"{last_right_index=}, {col_index=}"
            last_right_index = col_index
            if self.col_x_starts is None:
                self.col_x_starts = [0] * (col_index + 1)
                self.col_x_char_starts = [0] * (col_index + 1)
            self.row_layouts[rl_name] = Row_layout(self, rl_name, *cols)

        # Rows
        self.rows = []

    def new_row(self, row_layout, *values, size=None, bold=None, pad=0):
        return self.row_layouts[row_layout].new_row(*values, size=size, bold=bold, pad=pad)

    def init(self):
        self.set_sizes()
        self.set_y_starts()
        self.set_x_starts()

    def draw_init(self, verbose=False):
        r'''Returns report width, height.
        '''
        self.init()
        width = self.report_width()
        height = self.report_height()
        if width > Page_width and width > height:
            set_landscape()
            if verbose:
                print("pagesize", Pagesize)
                print("Report width", width, "height", height, "set landscape")
        elif verbose:
            print("Report width", width, "height", height)
        return width, height

    def draw(self, x_offset=2, y_offset=0):
        for row in self.rows:
            row.draw(x_offset, y_offset)

    def print_init(self, verbose=False):
        self.init()
        if verbose:
            print("Report width", self.report_width_chars(), "height", self.report_height_chars())

    def print(self, header_row=None, file=sys.stdout):
        if header_row is not None:
            from subprocess import run
            import io
            assert file == sys.stdout, "report.print file may not be specified with header_row"
            result = run(('stty', 'size'), capture_output=True, check=True)
            height, width = (int(x) for x in result.stdout.split())
            height -= 1  # less takes one line at the bottom
           #print(f"{height=}, {width=}")
            file = io.StringIO()
        lines_on_page = 0
        for row in self.rows:
            if header_row is not None and lines_on_page == height:
               #print('\f', end='', file=file)
                self.rows[header_row].print(file)
                lines_on_page = 1
            row.print(file)
            lines_on_page += 1
        if header_row is not None:
            run(('less', '-c'), input=file.getvalue(), text=True, check=True)

    def make_col_name(self, col_name):
        if col_name not in self.name_suffixes:
            self.name_suffixes[col_name] = 1
        ans = f"{col_name}-{self.name_suffixes[col_name]}"
        self.name_suffixes[col_name] += 1
        return ans

    def register_column(self, col_layout):
        assert col_layout.name not in self.columns, f"Duplicate Column name={col_layout.name}"
        self.columns[col_layout.name] = col_layout

    def add_row(self, row):
        self.rows.append(row)
        return len(self.rows)

    def set_sizes(self):
        for row in self.rows:
            row.set_sizes()

    def set_y_starts(self):
        BM(self)  # add dummy bottom margin row to capture the height of the report.
        for i, row in enumerate(self.rows[:-1]):
            self.rows[i + 1].set_y_start(row.y_start + row.height, row.y_char_start + row.height_chars)

    def set_x_starts(self):
        for i in range(len(self.col_x_starts)):  # all col_x_starts have been taken care of up to and including i
            for col in self.columns.values():
                if col.left_index == i:
                    right_start = \
                      self.col_x_starts[col.left_index] + col.indent + col.my_width + self.col_gap_points
                    if right_start > self.col_x_starts[col.right_index]:
                        self.col_x_starts[col.right_index] = right_start
                    right_char_start = \
                      self.col_x_char_starts[col.left_index] + col.indent_chars \
                      + col.my_width_chars + self.col_gap_chars
                    if right_char_start > self.col_x_char_starts[col.right_index]:
                        self.col_x_char_starts[col.right_index] = right_char_start

    def report_height(self):
        return self.rows[-1].y_start

    def report_height_chars(self):
        return self.rows[-1].y_char_start

    def report_width(self):
        return self.col_x_starts[-1]

    def report_width_chars(self):
        return self.col_x_char_starts[-1]


class Cell:
    def __init__(self, text, col, row, size=None, bold=None, text_format=None, text2_format=None):
        self.text = text
        self.col = col
        self.row = row
        self.size = size if size is not None else self.col.fontsize
        self.bold = bold if bold is not None else self.col.bold
        if self.bold:
            self.fontName = self.col.report.default_bold
        else:
            self.fontName = self.col.report.default_font
        self.text_format = text_format or col.text_format
        self.text2_format = text2_format or col.text2_format
        self.width1 = Canvas.stringWidth(self.format_text(self.text, self.text_format),
                                         fontName=self.fontName,
                                         fontSize=self.size)
        self.text2 = None
        self.bold2 = None
        self.width2 = 0

    def format_text(self, text, text_format):
        if text is None:
            return ""
        if text_format is None:
            return str(text)
        return text_format.format(text)

    def set_text2(self, text2, bold=False, text2_format=None):
        assert self.text2 is None, \
               f"Second call to Cell.set_text2, first text2={self.text2}, this {text2=}"
        self.text2 = text2
        self.bold2 = bold
        if self.bold2:
            self.fontName2 = self.col.report.default_bold
        else:
            self.fontName2 = self.col.report.default_font
        if text2_format is not None:
            self.text2_format = text2_format
        self.width1 += self.col.report.text2_gap_percent * self.size
        self.width2 = Canvas.stringWidth(self.format_text(self.text2, self.text2_format),
                                         fontName=self.fontName2,
                                         fontSize=self.size)

    def set_sizes(self):
        self.col.set_width(self.my_width(), self.my_width_chars())
        self.row.set_height(self.my_height(), 1)

    def my_height(self):
        r'''In points.
        '''
        return self.size

    def my_width(self):
        r'''In points.
        '''
        return self.width1 + self.width2

    def my_width_chars(self):
        r'''In characters.
        '''
        width1 = len(self.format_text(self.text, self.text_format))
        if self.text2 is None:
            width2 = 0
        else:
            width2 = 1 + len(self.format_text(self.text2, self.text2_format))
        return width1 + width2

    def draw(self, x_offset, y_offset):
        Canvas.setFont(self.fontName, self.size)
        x = self.col.get_x_offset(self.my_width())
        Canvas.drawString(x + x_offset,
                          Page_height - (y_offset + self.row.y_end),
                          self.format_text(self.text, self.text_format))

        if self.text2 is not None:
            Canvas.setFont(self.fontName2, self.size)
            Canvas.drawString(x + x_offset + self.width1,
                              Page_height - (y_offset + self.row.y_end),
                              self.format_text(self.text2, self.text2_format))

    def print(self, file):
        text = self.format_text(self.text, self.text_format)
        if self.text2 is not None:
            text += ' '
            text += self.format_text(self.text2, self.text2_format)
        self.col.print_gap(file)
        left, right = self.col.get_padding(len(text))
        print(' ' * left, text, ' ' * right, sep='', end='', file=file)


# Column layouts:

class Column_layout:
    report = None

    def __init__(self, name=None, span=1, indent=0, skip=0, size=None, bold=False,
                 text_format=None, text2_format=None):
        self.name = name
        self.span = span
        self.skip = skip
        self.indent_level = indent
        self.fontsize = size
        self.bold = bold
        self.text_format = text_format
        self.text2_format = text2_format

    def set_report(self, report, col_index):
        self.report = report
        self.left_index = col_index
        self.right_index = self.left_index + self.span
        if self.name is None:
            self.name = report.make_col_name(self.__class__.__name__)
        report.register_column(self)
        self.indent = self.indent_level * report.indent_points
        self.indent_chars = self.indent_level * report.indent_chars
        if self.fontsize is None:
            self.fontsize = report.default_size
        elif isinstance(self.fontsize, str):
            self.fontsize = getattr(report, self.fontsize + "_size")
        self.my_width = 0
        self.my_width_chars = 0

    def set_width(self, points, chars):
        if points > self.my_width:
            self.my_width = points
        if chars > self.my_width_chars:
            self.my_width_chars = chars

    @property
    def x_start(self):
        return self.report.col_x_starts[self.left_index]

    @property
    def x_char_start(self):
        return self.report.col_x_char_starts[self.left_index]

    def width(self):
        return self.report.col_x_starts[self.right_index] - self.x_start - self.report.col_gap_points

    def width_chars(self):
        return self.report.col_x_char_starts[self.right_index] - self.x_char_start - self.report.col_gap_chars

    def print_gap(self, file):
        if self.left_index:
            print(' ' * self.report.col_gap_chars, end='', file=file)

class Left(Column_layout):
    def get_x_offset(self, text_width):
        return self.x_start + self.indent

    def get_padding(self, text_width):
        r'''Returns num spaces to print to the left and right of text.
        '''
        return self.indent_chars, self.width_chars() - self.indent_chars - text_width

class Centered(Column_layout):
    r'''No indent on these...
    '''
    def get_x_offset(self, text_width):
        ans = self.x_start + self.width() / 2 - text_width / 2
       #print(f"Centered({self.name}).get_x_offset({text_width=}): {self.x_start=}, {self.width()=} -> {ans}")
        return ans

    def get_padding(self, text_width):
        r'''Returns num spaces to print to the left and right of text.
        '''
        left = (self.width_chars() - text_width) // 2
        right = self.width_chars() - text_width - left
        return left, right

class Right(Column_layout):
    r'''Assumes text is a Decimal with 2 digits after the decimal point, so just aligns right rather than
    aligning on decimal point.
    '''
    def get_x_offset(self, text_width):
        return self.x_start + self.width() - self.indent - text_width

    def get_padding(self, text_width):
        r'''Returns num spaces to print to the left and right of text.
        '''
        right = self.indent_chars
        left = self.width_chars() - self.indent_chars - text_width
        return left, right


class Row_layout:
    def __init__(self, report, name, *columns):
        r'''columns are Column_layout instances.
        '''
        self.report = report
        self.name = name
        self.columns = columns

    def new_row(self, *values, size=None, bold=None, pad=0):
        new_row = Row(self, pad)
        new_row.next_cells(*values, size=size, bold=bold)
        return new_row
  


class BM:
    r'''Bottom Margin.
    '''
    def __init__(self, report):
        self.y_start = 0
        self.y_char_start = 0
        self.row_num = report.add_row(self)  # NOTE: 1 greater than index into report.rows

    def set_y_start(self, y, y_char):
        if y > self.y_start:
            self.y_start = y
        if y_char > self.y_char_start:
            self.y_char_start = y_char

    def set_sizes(self):
        pass

    def draw(self, x_offset, y_offset):
        pass

    def print(self, file):
        pass

class Row(BM):
    def __init__(self, layout, pad=0):
        super().__init__(layout.report)
        self.layout = layout
        self.pad = pad
        self.column_index = 0
        self.height = 0
        self.height_chars = 0
        self.cells = []

    def set_height(self, points, chars):
        if points + self.pad > self.height:
            self.height = points + self.pad
        if chars > self.height_chars:
            self.height_chars = chars

    @property
    def y_end(self):
        return self.y_start + self.height

    def next_cell(self, text=None, size=None, bold=None, text_format=None, text2_format=None):
        r'''Doesn't return anything.
        '''
        assert self.column_index < len(self.layout.columns), f"Row({self.row_num}).next_cell: too many calls"
        cell = Cell(text, self.layout.columns[self.column_index], self, size=size, bold=bold,
                    text_format=text_format, text2_format=text2_format)
        self.cells.append(cell)
        self.column_index += 1

    def next_cells(self, *texts, size=None, bold=None):
        r'''Doesn't return anything.
        '''
        for text in texts:
            self.next_cell(text, size=size, bold=bold)

    def set_text2(self, text, bold=False, text2_format=None):
        r'''Adds text to the end of the last cell.
        '''
        self.cells[-1].set_text2(text, bold, text2_format)

    def set_sizes(self):
        for cell in self.cells:
            cell.set_sizes()

    def draw(self, x_offset, y_offset):
        for cell in self.cells:
            cell.draw(x_offset, y_offset)

    def print(self, file):
        for cell in self.cells:
            cell.print(file)
        print(file=file)


class Value:
    r'''A numeric value that accepts += and -= and forwards these numbers to all parents.
    '''
    def __init__(self, *parents, invert=False):
        self.parents = []
        for parent in parents:
            self.add_parent(parent, invert)
        self.value = 0

    def add_parent(self, parent, invert=False):
        self.parents.append((parent, invert))

    def __iadd__(self, n):
        self.value += n
        for p, invert in self.parents:
            if not invert:
                p += n
            else:
                p -= n
        return self

    def __isub__(self, n):
        self.value -= n
        for p, invert in self.parents:
            if not invert:
                p -= n
            else:
                p += n
        return self

class Row_template(Value):
    r'''These are templates for individual rows.

    These are Values, so accept += and -=.  Their parents are generally other Row_templates.  The value is added as
    another (expected to be the last) cell in the row as it is inserted into the report.

    These are used in 3 steps:

        1. Create the Row_templates the define the structure of your document.

           Save the key rows in python variables for step 2.

           Each Row_template supports adding a text2 to the first cell.  The text2_format parameter
           is a python format string (e.g., "({})").  The Row_template includes a text2_value that is
           inserted into the format string as a positional argument (e.g., "{}").  This text2_value
           is also a Value object, so can be made the parent of any other Row_template.

        2. Run through your data, incrementing(+=)/decrementing(-=) the affected rows through the
           python variables they were saved in.
           
           You can also add new Row_templates with parent_row_template.add_child()

        3. Call insert on the top-level Row_template to insert all of the non-zero rows into the
           report.

           You can create multiple top-level Row_templates if you have multiple top-level sections 
           in your report.  Insert these in the desired order.  The Row_templates in each section
           may refer to Row_templates in other sections (with add_parent).
    '''
    text2_format = None

    def __init__(self, layout, first_cell, *children, parent=None, hide_value=False, invert_parent=False,
                 first_cells=(), force=False, text2_format=None, pad=0):
        if parent is None:
            super().__init__()
        else:
            super().__init__(parent)
        self.layout = layout
        self.children = []
        for child in children:
            self.add_child(child)
        self.hide_value = hide_value
        self.invert_parent = invert_parent
        self.first_cell = first_cell
        self.first_cells = first_cells
        self.force = force
        if text2_format is not None:
            assert first_cell is not None or first_cells, \
                   f"Row_template.__init__: must specify first_cell or first_cells with {text2_format=}"
            self.text2_format = text2_format
            self.text2_value = Value()
        self.pad = pad

    def inc_text2_value(self, n):
        self.text2_value += n

    def dec_text2_value(self, n):
        self.text2_value -= n

    def add_child(self, child):
        r'''The child becomes the next subordinate section under this Row_template in the resulting
        report.

        Use add_parent when the two Row_templates are not structurally related.
        '''
        self.children.append(child)
        child.add_parent(self, child.invert_parent)

    def skip(self):
        r'''Skip if value is 0 and all children are skipped.
        '''
        if self.force or self.value:
            return False
        for child in self.children:
            if not child.skip():
                return False
        return True

    def insert(self, report):
        if not self.skip():
            row = report.new_row(self.layout, pad=self.pad)
            if self.first_cell is not None:
                row.next_cell(self.first_cell)
                if self.text2_format is not None:
                    row.set_text2(self.text2_value.value, text2_format=self.text2_format)
                row.next_cells(*self.first_cells)
            elif self.first_cells:
                row.next_cell(self.first_cells[0])
                if self.text2_format is not None:
                    row.set_text2(self.text2_value.value, text2_format=self.text2_format)
                row.next_cells(*self.first_cells[1:])
            if not self.hide_value:
                row.next_cell(self.value)
            for child in self.children:
                child.insert(report)


def dump_table(table_name, pdf=False, default_fontsize=13):
    from itertools import chain
    sys.path.append('.')
    import database

    database.load_database()

    if table_name.endswith('.csv'):
        database.load_csv(table_name)  # replaces table in database with .csv file, but we don't save the database!
        table_name = table_name[:-4]

    table = getattr(database, table_name)

    header_cols = []
    data_cols = []
    header_names = []
    for column in table.row_class.columns:
        if not column.hidden:
            header_names.append(column.name.lower())
            if column.alignment == 'right':
                header_cols.append(Right(bold=True))
                data_cols.append(Right())
            else:
                header_cols.append(Left(bold=True))
                data_cols.append(Left())
    assert len(header_cols) == len(data_cols) == len(header_names), \
           f"ERROR: {len(header_cols)=}, {len(data_cols)=}, {len(header_names)=}"

    set_canvas(table_name)

    report = Report(default_size=default_fontsize,
           title=(Centered(span=len(header_names), size='title', bold=True),),
           headers=header_cols,
           data=data_cols,
          )
    report.new_row('title', table_name)
    report.new_row('headers', *(table.row_class.column_map[name].abbr for name in header_names))
    for row in table.values():
        data = report.new_row('data')
        for name in header_names:
            value = getattr(row, name)
            if value is None:
                data.next_cell()
            elif isinstance(value, database.date):
                data.next_cell(value.strftime("%b %d, %y"))
            else:
                data.next_cell(value)

    if pdf:
        report.draw_init()
        report.draw()
        Canvas.showPage()
        Canvas.save()
    else:
        report.print_init()
        report.print(header_row=1)


# FIX: Not used... ??
def dump_data(report_name, headers, data, pdf=False, default_fontsize=13):
    from itertools import chain
    sys.path.append('.')
    import database

    data = tuple(data)

    header_cols = [None] * len(headers)
    data_cols = [None] * len(headers)
    for row in data:
        assert len(row) == len(headers), f"ERROR: {len(row)=} != {len(headers)=}"
        for i, value in enumerate(row):
            if value is not None:
                if isinstance(value, (int, float, database.Decimal)):
                    header_cols[i] = Right(bold=True)
                    data_cols[i] = Right()
                else:
                    header_cols[i] = Left(bold=True)
                    data_cols[i] = Left()

    for i in range(len(headers)):
        if header_cols[i] is None:
            header_cols[i] = Left(bold=True)
            data_cols[i] = Left()

    set_canvas(report_name)

    report = Report(default_size=default_fontsize,
           title=(Centered(span=len(headers), size='title', bold=True),),
           headers=header_cols,
           data=data_cols,
          )
    report.new_row('title', report_name)
    report.new_row('headers', *headers)
    for row in data:
        data_row = report.new_row('data')
        for value in row:
            if value is None:
                data_row.next_cell()
            elif isinstance(value, database.date):
                data_row.next_cell(value.strftime("%b %d, %y"))
            else:
                data_row.next_cell(value)

    if pdf:
        report.draw_init()
        report.draw()
        Canvas.showPage()
        Canvas.save()
    else:
        report.print_init()
        report.print(header_row=1)


def run():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", "-p", action="store_true", default=False)
    parser.add_argument("--size", "-s", type=int, default=13, help="fontsize (default 13)")
    parser.add_argument("table")

    args = parser.parse_args()

    dump_table(args.table, args.pdf, args.size)



if __name__ == "__main__":
    run()
