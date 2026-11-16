# test_action.py

import pytest
from csv_app import action
from csv_app.action import Actions, Dependents, Task, Note


@pytest.fixture(autouse=True)
def clean_actions():
    """Wipes the global Actions registry before and after every test."""
    Actions.clear()
    Dependents.clear()
    yield
    Actions.clear()
    Dependents.clear()


def test_note_can_run_is_false():
    """Verifies Note.can_run is a property that is False (as Task's is), so menus don't run Notes."""
    task = Task(100)
    note = Note(101, task)
    assert note.can_run is False
    assert task.can_run is False
    assert isinstance(type(note).__dict__["can_run"], property)
