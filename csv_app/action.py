# action.py

from collections import defaultdict

from .row import *
from .table import Database


__all__ = "reset ActionFailed Task Step Steps".split()


Actions = {}                    # {id: action}
Dependents = defaultdict(set)   # {prereq: {dependants}}


class ActionFailed(Exception):
    pass


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

    def __init__(self, id, *prereqs, can_rerun_after_commit=False):
        self.id = id
        self.prereqs = frozenset(prereqs)
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

    def disable(self):
        self.step.state = "disabled"

    @property
    def disabled(self):
        return self.step.state == 'disabled'

    def reset(self):
        self.step.reset()

    @property
    def step(self):
        return Database.Steps[self.id]


class Task(Action):
    r'''Made up of several Steps.
    '''
    is_task = True

    def __init__(self, id, *prereqs, column_break=False, can_rerun_after_commit=False):
        super().__init__(id, *prereqs, can_rerun_after_commit=can_rerun_after_commit)
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
    is_task = False

    def __init__(self, id, task, fn, *prereqs, can_rerun=False, can_rerun_after_commit=False, commits_task=False,
                 disable_prereqs=False):
        super().__init__(id, *prereqs, can_rerun_after_commit=can_rerun_after_commit)
        self.task = task
        if task is not None:
            task.add_step(self)
        self.fn = fn
        self.can_rerun = can_rerun
        self.commits_task = commits_task
        self.disable_prereqs = disable_prereqs

    def can_run(self):
        return not self.disabled \
           and (   not self.has_run()
                or (not self.committed and self.can_rerun)
                or (self.committed and self.can_rerun_after_commit)) \
           and all(Actions[prereq].has_run() for prereq in self.prereqs)

    def execute(self, app, *fn_args, **fn_kws):
        try:
            return self.fn(self, app, *fn_args, **fn_kws)
        except ActionFailed as e:
            app.screen.show_error(str(e))
            return None

    def mark_run(self, app):
        if self.step.state == "run":
            self.step.state = "rerun"
        else:
            self.step.state = "run"
        self.step.last_run = datetime.now()
        if self.commits_task:
            self.task.commit()  # do this before disable, so that disable overrides commit
        if self.disable_prereqs:
            for prereq in self.prereqs:
                Actions[prereq].disable()
        return 'REFRESH'


class Steps(Row):
    columns = (
        Column("id", parse=int, required=True),   # same as Action
        Column("number", required=True),
        Column("name", required=True),
        Column("state", choices="not-run run rerun committed disabled".split()),
        Datetime_column("last_run"),
    )
    primary_key = 'id'

    def reset(self):
        self.state = "not-run"
        self.last_run = None

