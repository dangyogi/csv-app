# action.py

from collections import defaultdict

from .row import *
from .table import Database


__all__ = "reset Task Step Steps".split()


Actions = {}                    # {id: action}
Dependents = defaultdict(set)   # {prereq: {dependants}}


def register(action):
    Actions[action.id] = action
    Dependents[action.id].update(action.prereqs)

def reset():
    r'''Run when a new month is created to start all over again...
    '''
    for action in Actions.values():
        action.reset()


class Action:
    column_break = False
    task = None

    def __init__(self, id, *prereqs, can_rerun_after_commit=False, commits_task=False):
        self.id = id
        self.prereqs = frozenset(prereqs)
        self.commits_task = commits_task
        self.can_rerun_after_commit = can_rerun_after_commit
        register(self)

    @property
    def number(self):
        return self.step.number

    @property
    def name(self):
        return self.step.name

    @property
    def committed(self):
        return self.step.state == 'committed'

    def has_run(self):
        return self.step.state is not None and self.step.state != "not-run"

    def invalidate(self):
        if self.has_run():
            self.step.state = "not-run"
            if self.id in Dependents:
                for id in Dependents[self.id]:
                    Actions[id].invalidate()

    def reset(self):
        self.step.reset()

    @property
    def step(self):
        return Database.Steps[self.id]


class Task(Action):
    r'''Made up of several Steps.
    '''
    def __init__(self, id, *prereqs, column_break=False, can_rerun_after_commit=False, commits_task=False):
        super().__init__(id, *prereqs, can_rerun_after_commit=can_rerun_after_commit, commits_task=commits_task)
        self.column_break = column_break
        self.steps = []

    def add_step(self, step):
        self.steps.append(step)

    def can_run(self):
        return False

    def commit(self):
        self.step.state = "committed"
        for child in self.steps:
            if child.step.state in ("run", "rerun"):
                child.step.state = "committed"


class Step(Action):
    r'''A single function.
    '''
    def __init__(self, id, task, fn, *prereqs, can_rerun_after_commit=False, commits_task=False):
        super().__init__(id, *prereqs, can_rerun_after_commit=can_rerun_after_commit, commits_task=commits_task)
        self.task = task
        if task is not None:
            task.add_step(self)
        self.fn = fn

    def can_run(self):
        return (not self.committed or self.can_rerun_after_commit) \
           and all(Actions[prereq].has_run() for prereq in self.prereqs)

    def run(self, *fn_args, **fn_kws):
        error = self.fn(self, *fn_args, **fn_kws)
        if not error:
            if self.step.state == "run":
                self.step.state = "rerun"
            else:
                self.step.state = "run"
            self.step.last_run = datetime.now()
            if self.commits_task:
                self.task.commit()
        return error


class Steps(Row):
    columns = (
        Column("id", parse=int, required=True),   # same as Action
        Column("number", required=True),
        Column("name", required=True),
        Column("state", choices="not-run run rerun committed".split()),
        Datetime_column("last_run"),
    )
    primary_key = 'id'

    def reset(self):
        self.state = "not-run"
        self.last_run = None

