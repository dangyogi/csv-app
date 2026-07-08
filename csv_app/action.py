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
    for id in action.prereqs:
        Dependents[id].add(action.id)

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
        return self.step.committed

    @property
    def has_run(self):
        return self.step.has_run

    def invalidate(self):
        trace(f"{self.__class__.__name__}({self.name=}).invalidate()")
        self.step.invalidate()

    def invalidate_dependents(self):
        trace(f"{self.__class__.__name__}({self.name=}).invalidate_dependents()")
        self.step.invalidate_dependents()

    def disable(self):
        trace(f"{self.__class__.__name__}({self.name=}).disable()")
        self.step.disable()

    @property
    def disabled(self):
        return self.step.disabled

    def reset(self):
        trace(f"{self.__class__.__name__}({self.name=}).reset()")
        self.step.reset()

    @property
    def step(self):
        return Database.Steps[self.id]

    def app_is(self, app):
        self.app = app


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

    @property
    def can_run(self):
        return False

    def commit(self):
        trace(f"Task({self.name=}).commit(): {self.step.state=}")
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

    @property
    def can_run(self):
        return not self.disabled \
           and (   not self.has_run
                or (not self.committed and self.can_rerun)
                or (self.committed and self.can_rerun_after_commit)) \
           and all(Actions[prereq].has_run for prereq in self.prereqs)

    def execute(self, app, *fn_args, **fn_kws):
        try:
            return self.fn(self, app, *fn_args, **fn_kws)
        except ActionFailed as e:
            app.screen.show_error(str(e))
            return None

    def mark_run(self, app):
        trace(f"Step({self.name=}).mark_run(): {self.step.state=}")
        assert self.step.state != "disabled", f'Step({self.name=}).mark_run: state is "disabled"'
        if self.step.state == "run":
            self.step.state = "rerun"
        elif self.step.state != 'rerun':
            self.step.state = "run"
        self.step.last_run = datetime.now()
        if self.commits_task:
            self.task.commit()  # do this before disable, so that disable overrides commit
        if self.disable_prereqs:
            for prereq in self.prereqs:
                Actions[prereq].disable()
        self.invalidate_dependents()
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
        trace(f"Steps({self.name=}).reset(): {self.state=}")
        self.state = "not-run"
        self.last_run = None

    def disable(self):
        trace(f"Steps({self.name=}).disable(): {self.state=}")
        self.state = "disabled"

    @property
    def disabled(self):
        return self.state == 'disabled'

    @property
    def committed(self):
        return self.state == 'committed'

    @property
    def has_run(self):
        return self.state is not None and self.state != "not-run"

    def invalidate(self):
        trace(f"Steps({self.id=}, {self.name=}).invalidate(): {self.state=}")
        if self.has_run:
            self.state = "not-run"
            self.invalidate_dependents()

    def invalidate_dependents(self):
        trace(f"Steps({self.name=}).invalidate_dependents(): {self.state=}")
        if self.id in Dependents:
            for id in Dependents[self.id]:
                Actions[id].invalidate()
