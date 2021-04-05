# System Imports
import os

# Twisted Imports
from twisted.internet import reactor, defer

# Sibling Imports
from octopus.sequence.sequence import Step
from octopus import data
from octopus.sequence import experiment
from octopus.machine import Machine
from octopus.sequence.shortcuts import *

_experiment = experiment.Experiment()

## inject machine registration
_old_machine_init = Machine.__init__


def _new_machine_init(self, *a, **k):
    _old_machine_init(self, *a, **k)
    _experiment.register_machine(self)


Machine.__init__ = _new_machine_init


def id(id):
    _experiment.id = id


def title(title):
    _experiment.title = title


def chdir(dir):
    return os.chdir(dir)


def variable(value, alias, title, unit=""):
    v = experiment.Variable(title, type(value), unit=unit)
    v.alias = alias
    v.set(value)

    return v


def derived(expr, alias, title, unit=""):
    expr.title = title
    expr.alias = alias

    return expr


def constant(value, alias, title, unit=""):
    v = data.Constant(value)
    v.title = title
    v.alias = alias
    v.unit = unit

    return v


def log_variables(*variables):
    _experiment.log_variables(*variables)


def run(step):
    started_reactor = False

    def _finished(result):
        if started_reactor:
            reactor.stop()

    def _run():
        d = _experiment.run()
        d.addBoth(_finished)

    if step is not None:
        _experiment.step = step

    reactor.callWhenRunning(_run)

    if reactor.running is False:
        started_reactor = True
        reactor.run()


def run_later(step):
    if step is not None:
        _experiment.step = step

    if reactor.running is False:
        reactor.run()


def log_output(name):
    return SetLogOutputStep(name)


class SetLogOutputStep(Step):
    def _run(self):
        Step._run(self)
        _experiment.set_log_output(str(self._expr))
        return self._complete(self._expr)
