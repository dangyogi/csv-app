# csv-app
Library supporting simple apps using a .csv file as a database, and CLI commands against the database.

Requires python reportlab library to produce .pdf reports.

OVERVIEW

This uses .csv files (using '|' as the delimiter with no quoting) to store data.

The database is a series of tables stored in one .csv file.

Each table starts with the name of the table as a row with a single column. This is followed by a
header row listing the attribute names.  This second row is followed by the data rows, terminating
in an empty row (no columns).  Each table has a python class, with each data row becoming an
instance of that class with header row names as its attributes.

An app built using this library would have several CLI python programs that each do one step.  Most
of these are very simple.

## Structure of application.

Each application based on this library would have the following modules:

 - rows.py
   defines a class derived from Row for each table it needs
 - tables.py
   defines a class derived from Table_unique or Table_by_date for each table that needs
   methods that operate on the whole table.
 - modules for the CLI programs

### rows.py

The row.py file declares the Column classes and a Row class for the rows in each of the tables
(one class derived from Row per table).

Includes these three things:

 - import these and declare what filename you want to use for your database.csv file:
   from csv_app.row import *
   from csv_app.table import Database, set_database_filename

   set_database_filename("my_database.csv")

 - define a class for each table to represent each row in that table.  These are derived from Row.
   - The name of the class becomes the name of the table.  Capitalize the first letter to help make these stand out.
   - Sets columns = a tuple of Column instances defined in csv_app.row: Column, Date_column, Set_column, Bool_column.
     - These include calculated columns that are not stored, but calculated with @property methods.
   - Define primary_key or primary_keys (not both).  Neither if keyed by date.
   - Define foreign_keys = tuple of class names
   - Set in_database = False if you don't want this table in the database
   - Add any calculated values you need as @property methods.
     - There is a Database global defined that has each of the table objects as attributes, e.g., Database.My_table.
       Use this to access any of the tables.
 - Create a global Rows variable with a tuple of these tables (not just their names).  These must be in logical order
   based on what has to be imported first to satisfy foreign constraints.
 - Add the following __all__ definition:
   __all__ = "Decimal date datetime timedelta abbr_month Rows".split()
 - Add the following to be able to run as a script to create the database.py module:
   if __name__ == "__main__":
       create_database_py(Rows)

Run this module as a program to generate the database.py module.  Rerun this whenever you add or delete classes in
this file.

   $ python rows.py

### tables.py

Table classes define what the whole table looks like.  Instances are given the Row class, which they store as row_class.
This allows one Table class to be used for many different tables, each instance having a different Row class.

The csv_app.table module defines two Table classes that should work for all or nearly all of your tables:

 - Table_unique for tables with unique primary keys (defined on the Row class as either primary_key or primary_keys).
   Table_unique is itself a dict, mapping these primary keys to Row objects when the database is read in
   (with load_database).
 - Table_by_date for tables without primary keys.  The Table_by_date is itself a list of rows in ascending date order.
   These Rows need a Date_column called "date" that is used to store the rows into the list.  Table_by_date does a
   binary search to insert each row (after all other duplicate rows).

The tables.py file defines any additional table classes you need.  These allow you to add methods that operate on
the entire table.

 - import these:
   from csv_app.table import *
   from .rows import Rows

 - write any additional custom table classes you need.  These are derived from Table_unique or Table_by_date.
   The name of the class must match the name of the Row class it represents.  You only need to define a class
   when you need a method that operates on the whole table.
 - at the global level call:
   load_rows(Rows [, <custom table 1>, <custom table 2>, ...])
 - Add the following __all__ definition:
   __all__ = "Decimal date datetime timedelta abbr_month Tables Database " \
             "load_database save_database load_csv load_all clear_all check_foreign_keys " \
             "CSV_dialect CSV_format".split()
 - Add the following to be able to run as a script to initialize and/or load/reload the database:
   if __name__ == "__main__":
       run()

### CLI programs

from .database import *

This will make each of the tables available as a global variable by the same name as the table.

The program must call "load_database()" to load the .csv file into memory.  When it is done, it must
also call "save_database()" to write the memory contents back to the .csv file (atomically replacing
its prior contents).  If there are errors, abort by simply not calling save_database.

Each table is a python dict mapping the table keys to rows.  In addition they have a "load_csv()" method
to load a csv file into memory just for that one table.  This allows you to use your text editor to edit
reference tables and then load them into memory, from which the "save_database()" will include them
in the .csv database.

Each table also has an "insert(attr=value...)" method to create new rows, and a "dump()" method
(see code in table.py) to dump the table to stdout.

You can keep your .csv database file in your github repo for backup.
