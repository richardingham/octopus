from __future__ import annotations

import asyncio
from inspect import isawaitable

# Twisted Imports
from twisted.python import log, failure
from twisted.logger import Logger

# Sibling Imports
from .error import NotRunning, AlreadyRunning, NotPaused, Stopped

# Package Imports
from octopus.task import LoopingCall, cancel_and_wait
from octopus.constants import State
from octopus.events import EventEmitter


class Runnable(object):
	"""
	Objects that can be run, reset, paused, cancelled.
	"""

	def __init__(self):
		self.state = State.READY
		self.resumed = asyncio.Event()

	async def run(self):
		if self.state is not State.READY:
			raise AlreadyRunning

		self.state = State.RUNNING
		self.resumed.set()

		try:
			await self._run()
			self.state = State.COMPLETE
		except asyncio.CancelledError:
			self.state = State.CANCELLED
			raise

	async def reset(self):
		if self.state in (State.RUNNING, State.PAUSED):
			raise AlreadyRunning

		self.state = State.READY
		self.resumed.clear()
		return await self._reset()

	async def pause(self):
		if self.state is not State.RUNNING:
			raise NotRunning

		self.state = State.PAUSED
		self.resumed.clear()
		return await self._pause()

	async def resume(self):
		if self.state is not State.PAUSED:
			raise NotPaused

		self.state = State.RUNNING
		self.resumed.set()
		return await self._resume()

	async def cancel(self, abort: bool = False):
		"""
		Stop gracefully, cancelling a loop or moving on to next step.
		"""

		if self.state not in (State.RUNNING, State.PAUSED):
			raise NotRunning

		self.state = State.CANCELLED
		return await self._cancel(abort)

	async def abort(self):
		"""
		Stop nongracefully, raising an error.
		"""

		try:
			return await self.cancel(abort=True)
		except NotRunning:
			pass

	async def _run(self):
		pass

	async def _reset(self):
		pass

	async def _pause(self):
		pass

	async def _resume(self):
		pass

	async def _cancel(self, abort: bool = False):
		pass


class BaseStep(Runnable):
	log = Logger()


class Dependent(Runnable, EventEmitter):
	log = Logger()

	def __init__(self):
		super().__init__()
		self.__task_calls = 0
		self.__task = None
		self.__loop = None
	
	async def __aenter__(self):
		if self.__task_calls == 0:
			self.__loop = asyncio.get_running_loop()
			self.__task = self.__loop.create_task(self.run())

		self.__task_calls += 1
	
	async def __aexit__(self, exc_type, exc, tb):
		if exc_type is not None:
			self.__task.cancel()
			return False
		
		self.__task_calls -= 1

		if self.state in (State.RUNNING, State.PAUSED):
			if self.__task_calls == 0:
				await cancel_and_wait(self.__task, self.__loop)
		

class Looping(Runnable):
	"""
	Subclass this to create step or dependent objects that involve iteration.
	"""
	log = Logger()

	def __init__(self, max_calls: int = None):
		super().__init__()
		self._max_calls = max_calls
		self._calls = 0

	async def _run(self):
		# Don't run at all if max_calls was set to 0.
		if self._max_calls is not None and self._max_calls == 0:
			return self._iteration_complete()

		self._calls = 0
		self._iteration_start()

	def _test(self):
		"""
		Override to control whether or not _iterate() is called on each cycle.
		Return True to run, False to skip
		"""

		return True

	def _iterate(self):
		def _done (result):
			self._schedule()

		def _error (failure):
			self.state = State.ERROR

		try:
			if self.state is State.PAUSED:
				self._iteration_stop()
				self._onResume = self._iteration_start
			elif self.state is State.CANCELLED:
				self._iteration_stop()
				return
			elif (self._max_calls is not None and self._max_calls > 0 and self._calls >= int(self._max_calls)):
				raise StopIteration
			elif self.state is State.RUNNING and self._test():
				d = self._call()

				if d is not None:
					self._calls += 1
					d.addCallbacks(_done, _error)
			else:
				self._schedule()

		except StopIteration:
			self._iteration_stop()
			self._iteration_complete()

		except Exception as e:
			self._iteration_stop()
			self._iteration_error(e)

	def _schedule(self):
		"""
		Executed when each loop is complete, if another loop is required.
		"""

		pass

	def _call(self):
		"""
		Executed on each loop
		"""

		pass

	def _iteration_start(self):
		"""
		Starts the loop running
		"""

		self._iterate()

	def _iteration_stop(self):
		"""
		Stops the loop.

		Triggered if _test() or _iterate raise StopIteration,
		or if state is PAUSED or CANCELLED.
		"""

		pass

	def _iteration_complete(self):
		"""
		Called when the loop finishes.

		This is either when max_calls has been reached
		or when StopIteration is raised by _test() or _iterate().
		"""

		pass

	def _iteration_error(self, error):
		"""
		Called if an error other than StopIteration is raised within
		_test() or _iterate()
		"""

		# NB also called if an error is raised by _iteration_stop()!

		pass

	async def _cancel(self, abort: bool = False):
		self._iteration_stop()

	async def _reset(self):
		self._iteration_stop()
		self._calls = 0



#
# Idea 2 - allow dependents to be attached to multiple parents
# run() increments the run count, cancel() decrements it.
# if run count > 0, run.
# pause() pauses but doesn't raise error if already paused
# resume() returns to run state, also doesn't raise errors.
#

def _next_interval(start_time: float, interval: float, when: float) -> float:
    """
    Calculate the time to wait until the next iteration of a looping call.
    @param start_time: the time the loop was started.
    @param interval: the interval between each call.
    @param when: The present time from whence the call is scheduled.
    """

    # How long should it take until the next invocation of our
    # callable?  Split out into a function because there are multiple
    # places we want to 'return' out of this.
    if interval == 0:
        # If the interval is 0, just go as fast as possible, always
        # return zero, call ourselves ASAP.
        return 0

    # Compute the time until the next interval; how long has this call
    # been running for?
    running_for = when - start_time

    # And based on that start time, when does the current interval end?
    until_next_interval = interval - (running_for % interval)

    # Now that we know how long it would be, we have to tell if the
    # number is effectively zero.  However, we can't just test against
    # zero.  If a number with a small exponent is added to a number
    # with a large exponent, it may be so small that the digits just
    # fall off the end, which means that adding the increment makes no
    # difference; it's time to tick over into the next interval.
    if when == when + until_next_interval:
        # If it's effectively zero, then we need to add another
        # interval.
        return interval

    # Finally, if everything else is normal, we just return the
    # computed delay.
    return until_next_interval


def _missed_calls(until_next_interval: float, interval: float, when: float) -> int:
    """
    Return the number of skipped calls from a loop.
    @param until_next_interval: value returned from wait_time.
    @param interval: the interval between each call.
    @param when: the last call time.
    """
    return int((until_next_interval - when) / interval - 1)


class Tick(Dependent):
	"""
	This is a dependent that runs a function periodically.

	The function can return a value, a Deferred, or a BaseStep to be executed.
	The function can also be a BaseStep to be executed.

	If the function is or returns a BaseStep then the BaseStep must complete
	before the next iteration can begin, no matter how long it takes.

	Log entries for the BaseStep are passed on to the step to which the
	dependent is attached.

	If Tick is run with a parent parameter then all events are passed on
	to the parent.
	"""

	def __init__(self, fn, interval: float, now: float = True, max_calls: int = None, fnArgs=None, fnKeywords=None):
		"""
		Initialise a Tick.

		@type fn:  callable or BaseStep.
		@param fn: The function or sequence to execute.
		@param interval: Frequency in seconds to call fn.
		@param now: The function should be called immediately, instead of after one interval.
		@param max_calls: Maximum number of times to run the function. Pass None for unlimited.
		@param fnArgs: Arguments to pass to fn.
		@param fnKeywords: Keyword arguments to pass to fn.
		"""
		Dependent.__init__(self)

		self._fn = fn
		self._args = fnArgs or ()
		self._kwargs = fnKeywords or {}

		self._interval = float(interval)
		self._now = bool(now)

		self._calls = 0
		self._max_calls = max_calls

	async def _run(self):
		from octopus.task import PausableSleep
		self._calls = 0

		loop = asyncio.get_running_loop()
		start_time = loop.time()

		if not self._now:
			self._waiter = PausableSleep(_next_interval(start_time, self._interval, start_time))
			await self._waiter

		while True:
			last_run_time = loop.time()
			result = self._fn(*self._args, **self._kwargs)

			if isawaitable(result):
				self._waiter = result
				result = await self._waiter
			
			self.last_result = result
			self._calls += 1

			if self._calls >= self._max_calls:
				break
		
			self._waiter = PausableSleep(_next_interval(start_time, self._interval, last_run_time))
			await self._waiter


class Trigger(Dependent):
	"""
	This is a dependent that runs a function as soon as a test evaluates to True.

	The function can return a value, a Deferred, or a Runnable to be executed.
	The function can also be a Runnable to be executed.

	If the function is or returns a Runnable then the Runnable must complete
	before the next iteration can begin, no matter how long it takes.

	Log entries for the Runnable are passed on to the step to which the
	dependent is attached.

	If Trigger is run with a parent parameter then all events are passed on
	to the parent.
	"""

	def __init__(self, expr, fn, max_calls: int = None, fnArgs=None, fnKeywords=None):
		"""
		Initialise a Trigger.

		@type expr: Expression (or value; but that would be relatively pointless).
		@type fn:  callable or Runnable.
		@param fn: The function or sequence to execute.
		@param max_calls: Maximum number of times to run the function. Pass None for unlimited.
		@param fnArgs: Arguments to pass to fn.
		@param fnKeywords: Keyword arguments to pass to fn.
		"""

		Dependent.__init__(self)

		self._fn = fn
		self._args = fnArgs or ()
		self._kwargs = fnKeywords or {}
		self._expr = expr

		self._calls = 0
		self._max_calls = max_calls

	async def _run(self):
		self._calls = 0

		while True:
			self._waiter = self._expr.changed.wait()
			await self._waiter

			if not bool(self._expr):
				continue

			result = self._fn(*self._args, **self._kwargs)

			if isawaitable(result):
				self._waiter = result
				result = await self._waiter
			
			self.last_result = result
			self._calls += 1

			if self._calls >= self._max_calls:
				break
