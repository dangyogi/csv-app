# dump_csv.py

import sys
import csv


CSV_dialect = 'excel'  # 'excel', 'excel-tab' or 'unix'
CSV_format = dict(delimiter='|', quoting=csv.QUOTE_NONE, skipinitialspace=True, strict=True)


def run(filename):
    with open(filename, 'r') as f:
        reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        for row in reader:
            print(f"{row=}")



if __name__ == "__main__":
    print(sys.argv[1])
    run(sys.argv[1])
