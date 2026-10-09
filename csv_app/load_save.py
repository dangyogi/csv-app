# load_save.py

import sys
import os
import os.path
import fcntl
import select
import signal
import pwd
import csv

from csv_app.table import Tables, Table_unique, Table_by_date


__all__ = [
    'set_database_filename',
    'get_database_filename',
    'CSV_dialect',
    'CSV_format',
    'load_database',
    'save_database',
    'load_csv',
    'load_all',
    'clear_all',
    'Database',
    'load_rows',
]

def set_database_filename(database_filename):
    global Database_filename
    Database_filename = database_filename

def get_database_filename():
    return Database_filename

CSV_dialect = 'excel'  # 'excel', 'excel-tab' or 'unix'
CSV_format = dict(delimiter='|', quoting=csv.QUOTE_NONE, skipinitialspace=True, strict=True)


_open_database_fd = None

def _write_status(message):
    data = (message + "\n").encode()

    # Each message should fit in a single atomic pipe write.
    pipe_buf = os.fpathconf(sys.stderr.fileno(), "PC_PIPE_BUF")

    if len(data) > pipe_buf:
        raise ValueError(f"Test message exceeds PIPE_BUF ({len(data)} > {pipe_buf})")

    written = os.write(sys.stderr.fileno(), data)

    if written != len(data):
        raise OSError(f"Short write to test pipe: {written} of {len(data)} bytes")

def print_step(test_name, next_step=None, finished_step=None, result="done"):
    if test_name is not None:
        if finished_step is not None:
            _write_status(f"{test_name}:finished:{finished_step}={result}")
        if next_step is not None:
            _write_status(f"{test_name}:next:{next_step}")
            signal.raise_signal(signal.SIGSTOP)

def username_from_pid(pid, test_name=None):
    prefix = f"{test_name}: " if test_name is not None else ""
   #print(f"{prefix}username_from_pid: {pid=}", file=sys.stderr)
    try:
        with open(f"/proc/{pid}/status", "r") as f:
            for line in f:
                if line.startswith("Uid:"):
                    uid = int(line.split()[1])
                    username = pwd.getpwuid(uid).pw_name
                   #print(f"{prefix}username_from_pid: {pid=}, {uid=}, {username=}", file=sys.stderr)
                    return username
    except (OSError, ValueError, KeyError):
        pass
   #print(f"{prefix}username_from_pid: pid not found, returning 'unknown'", file=sys.stderr)
    return "unknown"

def username_from_flock(fd, test_name=None):
    prefix = f"{test_name}: " if test_name is not None else ""
    fd_stat = os.fstat(fd)
   #print(f"{prefix}username_from_flock: {fd=}, {fd_stat.st_dev=}, {fd_stat.st_ino=}, "
   #      f"major={os.major(fd_stat.st_dev)}, minor={os.minor(fd_stat.st_dev)}",
   #      file=sys.stderr)
    file_id = f"{os.major(fd_stat.st_dev):02x}:{os.minor(fd_stat.st_dev):02x}:{fd_stat.st_ino}"
   #print(f"{prefix}username_from_flock: {file_id=}", file=sys.stderr)
    try:
        with open("/proc/locks", "r") as f:
            for line in f:
                fields = line.split()
                if fields[1] == "FLOCK" and fields[3] == "WRITE":
                   #print(f"{prefix}username_from_flock: got {fields=}", file=sys.stderr)
                    if fields[5] == file_id:
                       #print(f"{prefix}username_from_flock: pid={fields[4]}", file=sys.stderr)
                        return username_from_pid(fields[4], test_name)
    except (OSError, ValueError, KeyError):
        pass
   #print(f"{prefix}username_from_flock: flock record not found in /proc/locks, returning 'unknown'", file=sys.stderr)
    return "unknown"

def load_database(csv_filename=None, ignore_unknown_cols=False, exclusive=True, test_name=None):
    r'''Loads all database tables in csv_filename from scratch skipping fk_check.

    steps:
        open-current
        flock-current [BlockingIOError]
          close-current-1
          exit
        fstat-current
        stat-filename stats-differ|stats-same
          close-current-2
          open-current -> loops back to flock-current
        return
    '''
    global _open_database_fd

    if csv_filename is None:
        csv_filename = Database_filename
    def read_csv(f):
        reader = iter(csv.reader(f, CSV_dialect, **CSV_format))
        while True:
            try:
                header = next(reader)
                assert len(header) == 1, f"from_csv: Expected table name, got {header}"
                Tables[header[0].strip()].from_csv(reader, ignore_unknown_cols=ignore_unknown_cols,
                                                   skip_fk_check=True)
            except StopIteration:
                break
    if exclusive:
        print_step(test_name, "open-current")
        while True:
            _open_database_fd = open(csv_filename, 'r+')
            print_step(test_name, "flock-current", "open-current")
            try:
                fcntl.flock(_open_database_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print_step(test_name, "close-current-1", "flock-current", "BlockingIOError")
                lock_owner = username_from_flock(_open_database_fd.fileno(), test_name)
                _open_database_fd.close()
                print_step(test_name, "exit", "close-current-1")
                _open_database_fd = None
                prefix = f"{test_name}: " if test_name is not None else ""
                print(f"{prefix}Database {csv_filename} is locked by {lock_owner}", file=sys.stderr)
                sys.exit(1)
            # got flock, check if the file I have open is still current:
            print_step(test_name, "fstat-current", "flock-current")
            fd_stat = os.fstat(_open_database_fd.fileno())
            print_step(test_name, "stat-filename", "fstat-current")
            path_stat = os.stat(csv_filename)
            if (path_stat.st_dev, path_stat.st_ino) != (fd_stat.st_dev, fd_stat.st_ino):
                # some other process has created a new database file.  I got the lock on the old one...
                print_step(test_name, "close-current-2", "stat-filename", "stats-differ")
                _open_database_fd.close()   # releases the flock
                _open_database_fd = None
                print_step(test_name, "open-current", "close-current-2")
                continue
            print_step(test_name, "return", "stat-filename", "stats-same")
            if test_name is None:
                read_csv(_open_database_fd)
            break
    else:
        with open(csv_filename, 'r') as f:
            read_csv(f)

def save_database(csv_filename=None, test_name=None):
    r'''

    steps:
        open-new
        flock-new [BlockingIOError]
          exit
        exists-save yes|no
          yes:
            remove-save
            link-current-to-save
          no:
            link-current-to-save
        replace-new-to-current
        close-current
        exit
    '''
    global _open_database_fd

    if csv_filename is None:
        csv_filename = Database_filename
    if _open_database_fd is None:
        raise RuntimeError(f"Database {csv_filename} is not open")
    new_filename = csv_filename + '-new'
    print_step(test_name, "open-new")
    new_fd = open(new_filename, 'w+')
    print_step(test_name, "flock-new", "open-new")
    try:
        fcntl.flock(new_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print_step(test_name, "exit", "flock-new", "BlockingIOError")     
        lock_owner = username_from_flock(new_fd.fileno(), test_name)
        prefix = f"{test_name}: " if test_name is not None else ""
        print(f"{prefix}save_database: ERROR: database {new_filename} is locked by {lock_owner}", file=sys.stderr)
        sys.exit(1)
    print_step(test_name, None, "flock-new")
    if test_name is not None:
        print(f"{test_name}: new database contents", file=new_fd)
    else:
        for table in Tables.values():
            if table.row_class.in_database:
                table.to_csv(new_fd, add_empty_row=True)
    save_filename = csv_filename + '-save'
    print_step(test_name, "exists-save")
    if os.path.exists(save_filename):
        print_step(test_name, "remove-save", "exists-save", "yes")
        os.remove(save_filename)
        print_step(test_name, "link-current-to-save", "remove-save")
    else:
        print_step(test_name, "link-current-to-save", "exists-save", "no")
    os.link(csv_filename, save_filename)     # creates hard link: save_filename points to csv_filename
    print_step(test_name, "replace-new-to-current", "link-current-to-save")
    os.replace(new_filename, csv_filename)   # renames new_filename to csv_filename atomically,
                                             # replacing csv_filename.  flock on new_fd is preserved
    print_step(test_name, "close-current", "replace-new-to-current")
    _open_database_fd.close()                # releases flock on _open_database_fd
    _open_database_fd = new_fd               # continue running with new_fd, flock on new_fd is preserved
    print_step(test_name, "exit", "close-current")

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


# test harness:

def run_test(script, kw=None, choices=(), database_filename="dummy.csv"):
    r'''Runs a test script for each choice, doing line.format(**{kw: choice}) for each line in the script.

    Returns the number of choices that failed.
    '''
    errors = 0
    if not choices:
        if not run_script(script):
            errors += 1
    else:
        for choice in choices:
            print(file=sys.stderr)
            print(f"run_test calling run_script with {kw}={choice}", file=sys.stderr)
            def sub():
                for line in script:
                    yield line.format(**{kw: choice})
            if run_script(sub()):
                print(f"run_test run_script: {choice} PASSED", file=sys.stderr)
            else:
                print(f"run_test run_script: {choice} FAILED", file=sys.stderr)
                errors += 1
    return errors

def wait_until_stopped(pid):
    """Wait until this child has actually stopped, or exited."""
    while True:
        try:
            waited_pid, status = os.waitpid(pid, os.WUNTRACED)
        except InterruptedError:
            continue

        if waited_pid != pid:
            continue

        if os.WIFSTOPPED(status):
            if os.WSTOPSIG(status) != signal.SIGSTOP:
                raise RuntimeError(f"Child {pid} stopped by foreign signal {os.WSTOPSIG(status)}")
            # else stopped by SIGSTOP, so ready to continue!
            return

        if os.WIFEXITED(status):
            raise RuntimeError(f"Child {pid} exited with status {os.WEXITSTATUS(status)} before stopping")

        if os.WIFSIGNALED(status):
            raise RuntimeError(f"Child {pid} terminated from signal {os.WTERMSIG(status)} before stopping")

def run_script(script, database_filename="dummy.csv"):
    r'''Returns True if script passes, False otherwise.
    '''
    import subprocess

    with open(database_filename, 'w') as f:
        print("run_script: before test", file=f)
    r_pipe, w_pipe = os.pipe()
    processes = {}   # {test_name: Popen} 
    finished = {}    # {(test_name, step_name): result}
    next = {}        # {test_name: step_name}
    data_buffer = ""
    def drain(timeout):
        nonlocal data_buffer
        r, _, _ = select.select([r_pipe], [], [], timeout)
        if not r:
            if timeout:
                print(f"drain: timed out with {data_buffer!r}", file=sys.stderr)
            return False   # timeout
        data_buffer += os.read(r_pipe, 4096).decode(errors="replace")
        newline = data_buffer.find('\n')
        while newline >= 0:
            line = data_buffer[:newline]
            data_buffer = data_buffer[newline+1:]
            newline = data_buffer.find('\n')
            print(line, file=sys.stderr)
            if line and line[1] == ':' and line[2] != ' ':
                parts = line.split('=', 1)
               #print(f"drain: {line=}, {parts=}", file=sys.stderr)
                test_name, type, step_name = parts[0].split(':')
                match type:
                    case "finished":
                       #print(f"drain: setting finished[{test_name}, {step_name}] to {parts[1]}", file=sys.stderr)
                        finished[(test_name, step_name)] = parts[1]
                        if test_name in next:
                            del next[test_name]
                    case "next":
                       #print(f"drain: setting next[{test_name}] to {step_name}", file=sys.stderr)
                        next[test_name] = step_name
                        if (test_name, step_name) in finished:      # to cover looping
                            del finished[(test_name, step_name)]
                    case _:
                        print(f"run_script: ERROR: unknown type {type} in {line}", file=sys.stderr)
                        sys.exit(1)
        return True
    try:
        for line in script:
            line = line.strip()
            print(f"script: {line}", file=sys.stderr)
            if '#' in line:
                line = line[:line.find('#')].strip()
            if not line:  # skip blank lines
                continue
            test_name, *cmd = line.split()
            if '.' in test_name:
                test_name, func = test_name.split('.')
            else:
                func = None
            drain(0)
            def cont_through(step_name):
                print(f"{test_name}: continuing through {step_name}, {next.keys()=}, is {next.get(test_name)}", file=sys.stderr)
                while True:
                    while test_name not in next and drain(1): pass
                    if test_name not in next:
                        print(f"run_script: ERROR: {test_name} not in next", file=sys.stderr)
                        sys.exit(1)
                    print(f"{test_name}: stepping into {next[test_name]}", file=sys.stderr)
                    wait_until_stopped(processes[test_name].pid)
                    processes[test_name].send_signal(signal.SIGCONT)
                    if next[test_name] == step_name:
                        print(f"{test_name}: {step_name} started", file=sys.stderr)
                        del next[test_name]
                        break
                    else:
                        del next[test_name]
            match cmd[0]:
                case 'start':
                    processes[test_name] = subprocess.Popen(
                                             args=["python", "-m", "csv_app.load_save",
                                                   "load_database", "-d", database_filename, test_name],
                                             stdin=subprocess.DEVNULL,
                                             stdout=subprocess.DEVNULL,
                                             stderr=w_pipe,
                                             text=True,
                                           )
                    print(f"{test_name}: started: pid={processes[test_name].pid}", file=sys.stderr)
                case 'cont':         # cmd[1] is step name, continues until step name is run
                    cont_through(cmd[1])
                case 'result':       # cmd[1] is step name, cmd[2] is expected result
                    while (test_name, cmd[1]) not in finished and drain(1): pass
                    if (test_name, cmd[1]) not in finished:
                        print(f"run_script: ERROR: {test_name} {cmd[1]} not in finished", file=sys.stderr)
                        sys.exit(1)
                    result = finished[(test_name, cmd[1])]
                    if result != cmd[2]:
                        print(f"{test_name}: ERROR: wrong result for {cmd[1]} got {result}, expected {cmd[2]}",
                              file=sys.stderr)
                        sys.exit(1)
                    print(f"{test_name}: {cmd[1]} result={result}: matched", file=sys.stderr)
               #case 'stderr':       # cmd[1:] is expected line
                case 'exit':    # cmd[1] is returncode
                    cont_through("exit")
                    returncode = processes[test_name].wait(2)
                    if returncode != int(cmd[1]):
                        print(f"ERROR: {test_name} exited with {returncode}, expected {cmd[1]}", file=sys.stderr)
                        sys.exit(1)
                    print(f"{test_name}: terminated {returncode}", file=sys.stderr)
                case 'database':   # checks database contents for test_name
                    with open(database_filename, 'r') as f:
                        database_test_name = f.read().strip().split(':')[0]
                    if test_name != database_test_name:
                        print(f"ERROR: wrong database contents, expected {test_name}, got {database_test_name}",
                              file=sys.stderr)
                        sys.exit(1)
                    print(f"{test_name}: database correct", file=sys.stderr)
                case _:
                    print(f"{test_name}: Unknown command", cmd[0], file=sys.stderr)
                    sys.exit(1)
    except SystemExit:
        result = False
    else:
        result = True
    finally:
       #print("run_script: terminating processes", file=sys.stderr)
        for p in processes.values():
            p.kill()
        for name, p in processes.items():
       #    print(f"run_script: waiting for process {name}", file=sys.stderr)
            p.wait()
       #print("run_script: done", file=sys.stderr)
    return result



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run_test", "load_database"])
    parser.add_argument("argument", default=None)
    parser.add_argument("--database", "-d", default="dummy.csv")
    args = parser.parse_args()

    if args.command == "run_test":
        print(f"command run_test: {args.argument=}", file=sys.stderr)
        with open(args.argument, 'r') as script:
            kw = None
            choices = []
            in_body = False
            body = []
            for line in script:
                if in_body:
                    body.append(line)
                elif line.startswith('choices'):
                    words = line.split()
                    if len(words) > 1:
                        kw, *choices = words[1:]
                    else:
                        in_body = True
                elif kw:
                    if line.startswith(' '):
                        choices.extend(line.split())
                    else:
                        in_body = True
                        body.append(line)
            print(f"command run_test: {kw=}, {choices=}, lines={len(body)}", file=sys.stderr)
            run_test(body, kw, choices, args.database)

    elif args.command == "load_database":
        test_name = args.argument
        try:
            load_database(csv_filename=args.database, exclusive=True, test_name=test_name)
            save_database(csv_filename=args.database, test_name=test_name)
        except Exception:
            print(f"{test_name}: UNCAUGHT EXCEPTION", file=sys.stderr)
            raise
    else:
        print("Unknown command", args.command, file=sys.stderr)
        sys.exit(1)
