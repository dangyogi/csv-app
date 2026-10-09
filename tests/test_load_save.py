# test_load_save.py

import pytest

from csv_app.load_save import run_script


# load_database steps:
#     open-current
#     flock-current [BlockingIOError]
#       close-current-1
#       exit
#     fstat-current
#     stat-filename stats-differ|stats-same
#       close-current-2
#       open-current -> loops back to flock-current
#     return

# save_database steps:
#     open-new
#     flock-new [BlockingIOError]
#       exit
#     exists-save yes|no
#       yes:
#         remove-save
#         link-current-to-save
#       no:
#         link-current-to-save
#     replace-new-to-current
#     close-current
#     exit


One = """
    A start
    A exit 0
    A database
""".splitlines()


A_wins1_a = """
    A start
                                    B start
                                    B cont open-current
    A cont flock-current
    A result flock-current done
    A cont {stop}
                                    B cont flock-current
                                    B result flock-current BlockingIOError
                                    B exit 1
    A exit 0
    A database
""".splitlines()

A_wins1_b = """
    A start
                                    B start
                                    B cont open-current
    A cont flock-current
    A result flock-current done
    A cont close-current
                                    B cont flock-current
                                    B result flock-current done
                                    B cont stat-filename
                                    B result stat-filename stats-differ
                                    B cont flock-current
                                    B result flock-current BlockingIOError
                                    B exit 1
    A exit 0
    A database
""".splitlines()

Both_win = """
    A start
                                    B start
                                    B cont open-current
    A cont flock-current
    A result flock-current done
    A cont close-current
                                    B cont flock-current
                                    B result flock-current done
                                    B cont stat-filename
                                    B result stat-filename stats-differ
    A exit 0
    A database
                                    B cont flock-current
                                    B result flock-current done
                                    B exit 0
                                    B database
""".splitlines()


A_wins2_a = """
    A start
                                    B start
    A cont flock-current
    A result flock-current done
    A cont {stop}
                                    B cont flock-current
                                    B result flock-current BlockingIOError
                                    B exit 1
    A exit 0
    A database
""".splitlines()

A_wins2_b = """
    A start
                                    B start
    A cont flock-current
    A result flock-current done
                                    B cont open-current
    A exit 0
    A database
                                    B cont flock-current
                                    B result flock-current done
                                    B exit 0
                                    B database
""".splitlines()


def sub(script, kw, choice):
    for line in script:
        yield line.format(**{kw: choice})


def test_One():
    assert run_script(One)


@pytest.mark.parametrize("choice",
    "fstat-current stat-filename return open-new flock-new exists-save link-current-to-save replace-new-to-current".split()
)
def test_A_wins1_a(choice):
    assert run_script(sub(A_wins1_a, "stop", choice))

def test_A_wins1_b():
    assert run_script(A_wins1_b)

def test_Both_win():
    assert run_script(Both_win)

@pytest.mark.parametrize("choice",
    ("fstat-current stat-filename return open-new flock-new exists-save link-current-to-save replace-new-to-current "
     "close-current").split()
)
def test_A_wins2_a(choice):
    assert run_script(sub(A_wins2_a, "stop", choice))

def test_A_wins2_b():
    assert run_script(A_wins2_b)
