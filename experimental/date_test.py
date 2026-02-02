# date_test.py

from datetime import date

from table import *
from tables import *

today = date.today()
print(f"{today=}, {str(today)=}")


def run():
    row = tuple(Orders.get())[0]
    print(row, row.date, type(row.date))


if __name__ == "__main__":
    run()
