# System Imports
import os

# Twisted Imports
from twisted.internet import reactor, defer

# Sibling Imports
from . import sequence as s
from ...data import Variable

# To implement:
# with(sets, stmt)

## Helper functions

def sequence (*steps):
	return s.Sequence(steps)


def parallel (*steps):
	return s.Parallel(steps)


def set (var, expr):
	if not isinstance(var, Variable):
		raise Exception('set(): first argument must be a Variable')

	return s.SetStep(var, expr)


def increment (var):
	if not isinstance(var, Variable):
		raise Exception('increment(): argument must be a Variable')

	return s.SetStep(var, var + 1)


def decrement (var):
	if not isinstance(var, Variable):
		raise Exception('increment(): argument must be a Variable')

	return s.SetStep(var, var - 1)


def wait (time):
	return s.WaitStep(time)


def wait_until (test):
	return s.WaitUntilStep(test)


def loop_while (test, stmt, min_calls = 0):
	return s.WhileStep(test, stmt, min_calls)


def loop_until (test, stmt, min_calls = 0):
	return loop_while(test == False, stmt, min_calls)


def on (test, stmt, max_calls = None):
	return s.OnStep(test, stmt, max_calls)


def once (test, stmt):
	return on(test, stmt, 1)


def tick (stmt, interval, now = True, max_calls = None):
	return s.TickStep(stmt, interval, now, max_calls)


def call (fn, *args, **kwargs):
	return s.CallStep(fn, *args, **kwargs)


def do_if (test, stmt_true, stmt_false = None):
	if stmt_false is None:
		stmt_false = sequence()

	return s.IfStep(test, stmt_true, stmt_false)


def cancel (step):
	return s.CancelStep(step)


def log (message):
	return s.LogStep(message)
