"""
Asynchronous sequence execution
"""

# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.python import log
import twisted.internet.error

# System Imports
import re

# Sibling Imports
from .error import Error, NotRunning, AlreadyRunning, NotPaused, Stopped
from . import util

# Package Imports
from ..util import now
from ..events import EventEmitter
from ..constants import State
from ..data.data import BaseVariable, Variable, Constant


__all__ = [
	"Step", "WaitStep", "WaitUntilStep",
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

	def __init__(self, expr=None):
		super().__init__()
		self.id = next(_counter)

		if expr is not None and not isinstance(expr, BaseVariable):
			expr = Constant(expr)

		self._expr = expr


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

	async def _run(self):
		await Step._run(self)
		self._start = now()

		while True:
			await self._expr.changed.wait()

			if self.state is State.PAUSED:
				await self.resumed()

			if self.state is State.RUNNING and bool(self._expr) is True:
				return
			
	def _reset (self):
		self._start = 0

		return Step._reset(self)

