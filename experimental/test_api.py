# test_api.py

from functools import partial
from pathlib import Path
import csv

import machineid
import gspread


def getl2(length):
    l2 = list(map(partial(int, base=16), machineid.id()))
    copies = length // len(l2)
    remainder = length % len(l2)
    ans = []
    for i in range(1, copies + 1):
        ans = list(map(lambda n: i * n, l2)) + ans
    ans += l2[:remainder]
    assert length == len(ans)
    return ans

def makekey(id):
    l1 = list(id)
    return ''.join(l1.pop(i % len(l1)) for i in getl2(len(l1)))
    #return ''.join(l1.pop(min(len(l1) - 1, i)) for i in getl2(len(l1)))

def getkey():
    with open('../.private') as f:
        key = f.read().strip()
    l1 = list(key)
    l3 = []
    for c, i in zip(reversed(l1), reversed(getl2(len(key)))):
        l3.insert(i % (len(l3) + 1), c)
        #if i >= len(l3):
        #    l3.append(c)
        #else:
        #    l3.insert(i, c)
    return ''.join(l3)

def run(initial_load):
    import time
    from decimal import Decimal
    from datetime import date

    start = time.time()
    def show(msg):
        nonlocal start
        now = time.time()
        elapsed = now - start
        print(f"{msg}: {elapsed:.03f}")
        start = now
    key = getkey()
    show("getkey")
    #gc = gspread.service_account_from_dict(key)
    show("gc = gspread.service_account")
    gc = gspread.service_account(filename="../api-access-to-gg-mens-club-26db53e8116f.json")
    sh = gc.open("Test Sheet")
    show("sh = gc.open")
    worksheets = {ws.title: ws for ws in sh.worksheets()}
    show("worksheets = sh.worksheets")
    print("worksheets", worksheets.keys())
    if False:
        for name, rows in initial_load.items():
            ws = sh.add_worksheet(title=name, rows=len(rows), cols=len(rows[0]))
            show(f"ws = sh.add_worksheet({name}, rows={len(rows)}, cols={len(rows[0])})")
            ws.update(rows)
            show("ws.update")
    else:
        header = sh.sheet1.get("A1:F1")
        data = sh.sheet1.get("A2:F2")
        for name, value in zip(header[0], data[0]):
            print(name, type(value), value)

        #sh.sheet1.insert_row([12, 3.1415, '4.30', True, str(date(2026, 2, 21)), 'hello mom'], 2,
        #                     value_input_option=gspread.utils.ValueInputOption.raw, inherit_from_before=True)
    #print(sh.sheet1.get("A1"))
    #show("sh.sheet1.get")


CSV_dialect = 'excel'  # 'excel', 'excel-tab' or 'unix'
CSV_format = dict(delimiter='|', quoting=csv.QUOTE_NONE, skipinitialspace=True, strict=True)

Beans_file = Path("beans.csv")

def load(csv_filename=Beans_file):
    with Beans_file.open() as f:
        reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        ans = {}
        while True:
            try:
                header = next(reader)
                assert len(header) == 1, f"load: Expected table name, got {header}"
                rows = []
                while (row := next(reader)):
                    rows.append([x.strip() for x in row])
                ans[header[0].strip()] = rows
            except StopIteration:
                break
    return ans


if __name__ == "__main__":
    if True:
        with open("../api-access-to-gg-mens-club-26db53e8116f.json") as f:
            key = f.read()
        data = makekey(key)
        with open("../.private", "wt") as private:
            private.write(data)
        assert key == getkey()
    else:
        sheets = load()
        print("got")
        for name, rows in sheets.items():
            print(name, len(rows))
        run(sheets)
