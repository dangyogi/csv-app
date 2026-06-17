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
    for action in Actions.values():
        action.reset()


class Action:
    def __init__(self, id, *prereqs, can_rerun_after_commit=False, commits_task=False):
        self.id = id
        self.prereqs = frozenset(prereqs)
        self.commits_task = commits_task
        self.can_rerun_after_commit = can_rerun_after_commit
        register(self)

    @property
    def name(self):
        return self.step.name

    def has_run(self):
        return self.step.state != "not-run"

    def invalidate(self):
        if self.step.state != "not-run":
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
    def __init__(self, id, *prereqs, can_rerun_after_commit=False, commits_task=False):
        super().__init__(id, *prereqs, can_rerun_after_commit=can_rerun_after_commit, commits_task=commits_task)
        self.steps = []

    def add_step(self, step):
        self.steps.append(step)

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
           and all(prereq.has_run() for prereq in self.prereqs)

    def run(self, *fn_args, **fn_kws):
        self.fn(self, *fn_args, **fn_kws)
        if self.step.state == "run":
            self.step.state = "rerun"
        else:
            self.step.state = "run"
        self.step.last_run = datetime.now()
        if self.commits_task:
            self.task.commit()


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

