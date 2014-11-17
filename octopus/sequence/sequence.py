"""
Asynchronous sequence execution
"""

# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.python import log
import twisted.internet.error

# System Imports
from exceptions import IndexError
import re

# Sibling Imports
from error import Error, NotRunning, AlreadyRunning, NotPaused, Stopped
import util

# Package Imports
from ..util import now, EventEmitter
from ..constants import State
from ..data.data import BaseVariable, Variable, Constant

__all__ = [
	"Step", "Sequence", "Parallel", "IfStep", "SetStep", "CancelStep",
	"LogStep", "WhileStep", "WaitStep", "WaitUntilStep", "CallStep", 
	"Error", "NotRunning", "AlreadyRunning", "NotPaused", "Stopped"
]

def _counter ():
	i = 1
	while i > 0:
		yield i
		i += 1

_counter = _counter()


class Step (util.BaseStep, EventEmitter):

	type = "step"
	duration = 0

	@property
	def state (self):
		return self._state

	@state.setter
	def state (self, value):
		self._state = value
		self.emit("state-changed", item = self, state = value)

	def __init__ (self, expr = None):
		self.id = _counter.next()
		self.complete = defer.Deferred()
		self.dependents = util.Dependents()

		if expr is not None and not isinstance(expr, BaseVariable):
			expr = Constant(expr)

		self._expr = expr

		self.state = State.READY

	def _bubbleEvent (self, event, data):
		self.emit(event, **data)

	def _run (self):
		self.dependents.on("all", self._bubbleEvent)
		self.dependents.run()

		return self.complete

	def _reset (self):
		self.complete = defer.Deferred()
		return self.dependents.reset()

	def _pause (self):
		return self.dependents.pause()

	def _resume (self):
		return self.dependents.resume()

	def _cancel (self, abort = False):
		if abort:
			return self._error(Stopped())
		else:
			return self._complete()

	def _complete (self, result = None):
		self.state = State.COMPLETE
		return self.__cb(self.complete.callback, self.dependents.cancel, result)

	def _complete_cb (self, result = None):
		self._complete(result)
		return result

	def _error (self, failure):
		self.state = State.ERROR
		return self.__cb(self.complete.errback, self.dependents.abort, failure)

	def _error_cb (self, failure):
		self._error(failure)
		return failure

	def __cb (self, cb_fn, dep_fn, value):
		def cb (result):
			self.dependents.off("all", self._bubbleEvent)

			try:
				cb_fn(value)
			except defer.AlreadyCalledError:
				pass

		dep_fn() \
			.addErrback(log.err) \
			.addBoth(cb) \
			.addErrback(log.err)

		return self.complete

	def serialize (self):
		serialized = {
			"id": self.id,
			"type": self.__class__.__name__.lower(),
			"state": self.state.value,
			"duration": self.duration
		}

		if self._expr is not None:
			try:
				serialized["expr"] = self._expr.serialize()
			except AttributeError:
				serialized["expr"] = str(self._expr)

		return serialized


class _StepWithChild (Step):

	def __init__ (self, expr = None, step = None):
		Step.__init__(self, expr)
		self._step = util.init_child(self, step)

	def _cancel (self, abort = False):
		d = self.dependents.cancel(abort)

		try:
			d2 = self._step.cancel(abort)
			return defer.gatherResults([d, d2])
		except NotRunning:
			return d

	def _reset (self):
		return defer.gatherResults([
			defer.maybeDeferred(Step._reset, self),
			self._step.reset()
		])

	def _pause (self):
		return defer.gatherResults([
			defer.maybeDeferred(Step._pause, self),
			self._step.pause()
		])

	def _resume (self):
		return defer.gatherResults([
			defer.maybeDeferred(Step._resume, self),
			self._step.resume()
		])

	def serialize (self):
		serialized = Step.serialize(self)
		serialized["child"] = self._step.serialize()

		return serialized


class _StepWithChildren (Step):

	def __init__ (self, expr = None, steps = None):
		Step.__init__(self, expr)
		self._steps = []

		if steps is None:
			steps = []

		# Raise a TypeError if steps is not iterable
		for step in steps:
			if step is not None:
				self._steps.append(util.init_child(self, step))

	def _cancel (self, abort = False):
		d = [self.dependents.cancel(abort)]

		for step in self._steps:
			try:
				d.append(step.cancel(abort))
			except NotRunning:
				pass

		return defer.gatherResults(d)

	def _reset (self):
		d = [defer.maybeDeferred(Step._reset, self)]

		for step in self._steps:
			step.reset()

	def _pause (self):
		d = [defer.maybeDeferred(Step._pause, self)]

		for step in self._steps:
			try:
				d.append(step.pause())
			except NotRunning:
				pass

		return defer.gatherResults(d)

	def _resume (self):
		d = [defer.maybeDeferred(Step._resume, self)]

		for step in self._steps:
			try:
				d.append(step.resume())
			except NotPaused:
				pass

		return defer.gatherResults(d)

	def serialize (self):
		serialized = Step.serialize(self)
		serialized["children"] = [step.serialize() for step in self._steps]

		return serialized


class _StepWithLoop (util.Looping, _StepWithChild):

	def __init__ (self, expr, step, max_calls = None):
		_StepWithChild.__init__(self, expr, step)
		util.Looping.__init__(self, max_calls)

	def _run (self):
		_StepWithChild._run(self)
		util.Looping._run(self)

		return self.complete

	def _test (self):
		return self._expr

	def _schedule (self):
		reactor.callLater(0, self._iterate)

	def _call (self):
		try:
			self._step.reset()
			return self._step.run(parent = self)
		except AlreadyRunning:
			return None

	def _iteration_stop (self):
		# If the child never started, make sure its callback runs.
		if self._step.state is State.READY:
			self._step._complete()

	def _iteration_complete (self):
		self._complete()

	def _iteration_error (self, error):
		self._error(error)

	def _cancel (self, abort = False):
		util.Looping._cancel(self, abort)

		if abort:
			# Stops execution of child step
			try:
				return defer.maybeDeferred(_StepWithChild._cancel, self, abort)
			except NotRunning, Stopped:
				pass
		else:
			# Allows child step to finish normally
			try:
				return defer.maybeDeferred(_StepWithChild._cancel, self)
			except NotRunning:
				pass

	def _reset (self):
		return defer.gatherResults([
			defer.maybeDeferred(_StepWithChild._reset, self),
			defer.maybeDeferred(util.Looping._reset, self)
		])


class Sequence (_StepWithChildren):

	type = "sequence"

	def __init__ (self, steps):
		_StepWithChildren.__init__(self, None, steps)

	def __len__ (self):
		return len(self._steps)

	def __iter__ (self):
		return iter(self._steps)

	def __getitem__ (self, key):
		return self._steps[key]

	def add (self, step):
		self.__setitem__(len(self), step)

	def __setitem__ (self, key, value):
		if self.state is not State.READY:
			raise AlreadyRunning

		self._steps[key] = value
		##self.event

	def __delitem__ (self, key):
		if self.state is not State.READY:
			raise AlreadyRunning

		del self._steps[key]
		##self.event

	def _run (self):
		_StepWithChildren._run(self)
		iterator = iter(self)

		def advance (result = None):
			if self.state is State.PAUSED:
				self._onResume = advance
			elif self.state is State.CANCELLED:
				return None
			else:
				try:
					step = iterator.next()
				except StopIteration:
					self._complete(result)
				else:
					reactor.callLater(0,
						lambda step: step.run(parent = self) \
							.addCallbacks(advance, self._error),
						step
					)

			return result

		advance()

		return self.complete

	@property
	def duration (self):
		return sum([x.duration for x in self._steps])


class Parallel (Sequence):

	type = "parallel"

	def __init__ (self, steps):
		_StepWithChildren.__init__(self, None, steps)

	def _run (self):
		_StepWithChildren._run(self)

		count = len(self)
		self._stepsFinished = 0

		def finish (result = None):
			self._stepsFinished += 1

			if self._stepsFinished >= count:
				self._complete()

			return result

		for s in self._steps:
			# intercept error to abort all steps?
			s.run(parent = self).addCallbacks(finish, self._error_cb)

		return self.complete

	@property
	def duration (self):
		return max([x.duration for x in self._steps])


class IfStep (_StepWithChildren):

	type = "if"

	def __init__ (self, test, stmt_if_true, stmt_if_false):
		_StepWithChildren.__init__(self, test, [stmt_if_true, stmt_if_false])

	def _run (self):
		_StepWithChildren._run(self)

		step = self._steps[int(not bool(self._expr))]
		step.run(parent = self).addCallbacks(self._complete_cb, self._error_cb)

		return self.complete

	@property
	def duration (self):
		return max([x.duration for x in self._steps])


class SetStep (Step):

	type = "set"

	def __init__ (self, var, expr):
		Step.__init__(self, expr)

		self._var = var

	def _run (self):
		Step._run(self)

		d = defer.maybeDeferred(self._var.set, self._expr.value)
		d.addCallbacks(self._complete_cb, self._error_cb)

		return self.complete

	def serialize (self):
		serialized = Step.serialize(self)
		serialized["var"] = self._var.title

		return serialized


class CancelStep (Step):

	type = "cancel"

	def __init__ (self, step):
		Step.__init__(self)
		self._step = step

	def _run (self):
		Step._run(self)

		try:
			self._step.cancel()
		except NotRunning, Stopped:
			pass

		return self._complete()


class LogStep (Step):

	type = "log"

	def _run (self):
		Step._run(self)

		self.emit("log", message = self._expr.value)
		return self._complete(self._expr.value)


class WhileStep (_StepWithLoop):

	type = "while"

	def __init__ (self, expr, step, min_calls = 0):
		_StepWithLoop.__init__(self, expr, step)
		self._min_calls = min_calls

	def _run (self):
		self._current_min_calls = int(self._min_calls or 0)
		return _StepWithLoop._run(self)

	def _test (self):
		if self._calls >= self._current_min_calls and not bool(self._expr):
			raise StopIteration
		else:
			return True


_wait_re = re.compile("(?:(\d+) *h(?:our(?:s)?)?)? *(?:(\d+) *m(?:in(?:ute(?:s)?)?)?)? *(?:(\d+) *s(?:ec(?:ond(?:s)?)?)?)? *(?:(\d+) *m(?:illi)?s(?:ec(?:ond(?:s)?)?)?)?", re.I)

class WaitStep (Step):

	type = "wait"

	def __init__ (self, expr):
		Step.__init__(self, expr)

		self._c = None
		self._start = 0
		self._delay = 0

	def _run (self):
		Step._run(self)

		if self._expr.type in (int, float):
			self.duration = self._expr.value

		elif self._expr.type is str:
			s = _wait_re.match(self._expr.value);

			if s is None:
				raise Error('Bad time format')

			# Convert human-readable time to number of seconds
			s = [int(x or 0) for x in s.groups()]
			self.duration = (s[0] * 3600) + (s[1] * 60) + s[2] + (s[3] * 0.001)

		else:
			raise Error('Bad time format')

		def complete ():
			self._iteration_stop()
			self._complete()

		self._start = now()
		self._c = reactor.callLater(self.duration, complete)
		self.emit("started", item = self, start = self._start, 
			delay = round(self._delay, 4), duration = self.duration)

		return self.complete

	def delay (self, time):
		if self.state is not State.RUNNING:
			raise NotRunning

		time = max(0, time)
		self._delay += time
		self._c.delay(time)
		self.emit("delayed", item = self, delay = round(self._delay, 4))

	def restart (self, time):
		if self.state is not State.RUNNING:
			raise NotRunning

		time = max(0, time)
		self._delay += now() - self._start - self._delay
		self._c.reset(time)
		self.emit("delayed", item = self, delay = round(self._delay, 4))

	def _iteration_stop (self):
		try:
			self._c.cancel()
		except (
			AttributeError,
			twisted.internet.error.AlreadyCalled,
			twisted.internet.error.AlreadyCancelled
		):
			pass

	def _cancel (self, abort = False):
		self._iteration_stop()
		return Step._cancel(self, abort)

	def _reset (self):
		self._c = None
		self._start = 0
		self._delay = 0

		return Step._reset(self)

	def serialize (self):
		serialized = Step.serialize(self)
		serialized["start"] = self._start
		serialized["delay"] = round(self._delay, 4)

		return serialized

	def _pause (self):
		d = Step._pause(self)

		complete = self._c.func
		self._c.cancel()
		remaining = self._c.getTime() - now()
		self._pauseTime = now()

		def on_resume ():
			self._delay += now() - self._pauseTime
			self._c = reactor.callLater(remaining, complete)
			self.emit("delayed", item = self, delay = round(self._delay, 4))

		self._onResume = on_resume

		return d


class WaitUntilStep (Step):

	type = "waituntil"

	def __init__ (self, expr):
		Step.__init__(self, expr)

		self._start = 0

	def _run (self):
		Step._run(self)

		self._start = now()
		self.emit("started", item = self, start = self._start)
		self._expr.on("change", self._test)
		self._test()

		return self.complete

	def _test (self, data = None):
		if self.state is State.RUNNING and bool(self._expr) is True:
			self._expr.off("change", self._test)
			self._complete()

	def _cancel (self, abort = False):
		self._expr.off("change", self._test)
		return Step._cancel(self, abort)

	def _pause (self):
		self._onResume = self._test
		return Step._pause(self)

	def _reset (self):
		self._start = 0

		return Step._reset(self)

	def serialize (self):
		serialized = Step.serialize(self)
		serialized["start"] = self._start

		return serialized


class CallStep (util.Caller, Step):

	type = "call"

	def __init__ (self, fn, *args, **kwargs):
		Step.__init__(self)
		util.Caller.__init__(self, fn, args, kwargs)

	def _run (self):
		Step._run(self)

		d = self._call()
		d.addCallbacks(self._complete_cb, self._error_cb)

		return self.complete

	def _cancel (self, abort = False):
		d = self.dependents.cancel(abort)

		try:
			d2 = util.Caller._cancel(self, abort)
			return defer.gatherResults([d, d2])
		except AttributeError, NotRunning:
			return d

	def _reset (self):
		d = Step._reset(self)

		try:
			d2 = util.Caller._reset(self)
			return defer.gatherResults([d, d2])
		except AttributeError:
			return d

	def _pause (self):
		d = Step._pause(self)

		try:
			d2 = util.Caller._pause(self)
			return defer.gatherResults([d, d2])
		except AttributeError:
			return d

	def _resume (self):
		d = Step._resume(self)

		try:
			d2 = util.Caller._resume(self)
			return defer.gatherResults([d, d2])
		except AttributeError:
			return d

	def serialize (self):
		serialized = Step.serialize(self)

		if instanceof(self._step, Step):
			serialized["child"] = self._step.serialize()

		return serialized


class OnStep (Step):

	type = "on"

	def __init__ (self, expr, fn, max_calls = None, fnArgs = None, fnKeywords = None):
		Step.__init__(self)

		self._trigger = util.Trigger(expr, fn, max_calls, fnArgs, fnKeywords)

	def _run (self):
		Step._run(self)

		if self.parent is not None:
			parent = self.root.dependents.add(self._trigger)
 
		return self._complete()


class TickStep (Step):

	type = "tick"

	def __init__ (self, expr, fn, interval, now = True, max_calls = None, fnArgs = None, fnKeywords = None):
		Step.__init__(self)

		self._tick = util.Trigger(expr, fn, interval, now, max_calls, fnArgs, fnKeywords)

	def _run (self):
		Step._run(self)

		if self.parent is not None:
			parent = self.root.dependents.add(self._tick)
 
		return self._complete()


# with(sets, stmt)

