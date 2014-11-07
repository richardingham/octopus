# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.python import log, failure

# Sibling Imports
from error import NotRunning, AlreadyRunning, NotPaused, Stopped

# Package Imports
from ..constants import State
from ..util import Event

def init_child (parent, child):
	from sequence import Sequence

	if child is None:
		child = Sequence([])
	elif isinstance(child, BaseStep):
		pass
	else:
		try:
			child = Sequence(child)
		except TypeError:
			raise Error("Argument must be an instance of Step or a list of Steps")

	child.event += parent.event
	child.log += parent.log

	return child

class Runnable (object):
	"""
	Objects that can be run or reset.
	"""

	def run (self, parent = None):
		if self.state is not State.READY:
			raise AlreadyRunning

		self.state = State.RUNNING
		self.parent = parent
		return defer.maybeDeferred(self._run)

	def reset (self):
		if self.state in (State.RUNNING, State.PAUSED):
			raise AlreadyRunning

		self.state = State.READY
		self._onResume = None
		return defer.maybeDeferred(self._reset)

	@property
	def root (self):
		obj = self

		while obj.parent is not None:
			obj = obj.parent

		return obj

	def _run (self):
		pass

	def _reset (self):
		pass


class Pausable (object):
	def pause (self):
		if self.state is not State.RUNNING:
			raise NotRunning

		self.state = State.PAUSED
		return defer.maybeDeferred(self._pause)

	def resume (self):
		if self.state is not State.PAUSED:
			raise NotPaused

		self.state = State.RUNNING
		d = defer.maybeDeferred(self._resume)

		try:
			onResume, self._onResume = self._onResume, None
			onResume()
		except (AttributeError, TypeError):
			pass

		return d

	def _pause (self):
		pass

	def _resume (self):
		pass


class Cancellable (object):
	def cancel (self, abort = False):
		"""
		Stop gracefully, cancelling a loop or moving on to next step.
		"""

		if self.state not in (State.RUNNING, State.PAUSED):
			raise NotRunning

		self._onResume = None

		self.state = State.CANCELLED
		return defer.maybeDeferred(self._cancel, abort)

	def abort (self):
		"""
		Stop nongracefully, raising an error.
		"""

		try:
			return self.cancel(abort = True)
		except NotRunning:
			return defer.succeed(None)

	def _pause (self):
		pass

	def _resume (self):
		pass

	def _cancel (self, abort = False):
		pass


class BaseStep (Runnable, Pausable, Cancellable):
	pass


class Dependent (Runnable, Pausable, Cancellable):
	def __init__ (self):
		self.state = State.READY
		self.event = Event()
		self.log = Event()


class Looping (Runnable, Pausable, Cancellable):
	"""
	Subclass this to create step or dependent objects that involve iteration.
	"""

	def __init__ (self, max_calls = None, interval = 0.1, now = True):
		self._max_calls = max_calls
		self._interval = float(interval)
		self._now = bool(now)

		self._calls = 0
		self._c = None

	def _run (self):
		# Don't run at all if max_calls was set to 0.
		if self._max_calls is not None and self._max_calls == 0:
			return self._complete()

		self._calls = 0
		max_calls = int(self._max_calls or 0)

		def loop ():
			try:
				if self.state is State.PAUSED:
					self._iteration_stop()
					self._onResume = self._iteration_start
				elif self.state is State.CANCELLED:
					return
				elif (max_calls > 0 and self._calls >= max_calls):
					raise StopIteration
				elif self._test():
					d = self._iterate()

					if d is not None:
						self._calls += 1
						return d
			except StopIteration:
				self._iteration_stop()
				self._iteration_complete()
			except Exception as e:
				self._iteration_error(e)

		self._c = task.LoopingCall(loop)
		self._iteration_start()

	def _test (self):
		"""
		Override to control whether or not _iterate() is called on each cycle.
		Return True to run, False to skip
		"""

		return True

	def _iterate (self):
		"""
		Override to set logic that runs each cycle.

		_iterate() runs provided _test() returns True
		"""

		pass

	def _iteration_start (self):
		"""
		Starts the loop running
		"""

		self._c.start(self._interval, now = True)

	def _iteration_stop (self):
		"""
		Stops the loop. 
		
		Triggered if _test() or _iterate raise StopIteration,
		or if state is PAUSED or CANCELLED.
		"""

		if self._c and self._c.running:
			self._c.stop()

	def _iteration_complete (self):
		"""
		Called when the loop finishes.

		This is either when max_calls has been reached
		or when StopIteration is raised by _test() or _iterate().
		"""

		pass

	def _iteration_error (self, error):
		"""
		Called if an error other than StopIteration is raised within
		_test() or _iterate()
		"""

		# NB also called if an error is raised by _iteration_stop()!

		self._iteration_stop()
		self.state = State.ERROR

		log.err(error)

	def _cancel (self, abort = False):
		self._iteration_stop()

	def _reset (self):
		self._iteration_stop()
		self._calls = 0

#
# Idea 2 - allow dependents to be attached to multiple parents
# run() increments the run count, cancel() decrements it.
# if run count > 0, run.
# pause() pauses but doesn't raise error if already paused
# resume() returns to run state, also doesn't raise errors.
#

class Tick (Looping, Dependent):
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

	def __init__ (self, fn, interval, now = True, max_calls = None, fnArgs = None, fnKeywords = None):
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
		Looping.__init__(self, 
			max_calls = max_calls, 
			interval = interval, 
			now = now
		)

		self._fn = fn
		self._args = fnArgs or ()
		self._kwargs = fnKeywords or {}

		self._step = None

	def _iterate (self):
		if isinstance(self._fn, BaseStep):
			self._step = self._fn

		elif callable(self._fn):
			# Act based on the result of fn().
			result = self._fn(*self._args, **self._kwargs)

			if isinstance(result, defer.Deferred):
				# Tick will wait for the Deferred before cycling again.
				self._step = result
				return result
			elif isinstance(result, BaseStep):
				self._step = result
			else:
				return defer.succeed(result)

		# fn was not callable.
		else:
			return None

		# We have a Runnable to run.
		d = defer.Deferred()

		def remove_events (passthrough):
			# Clean up after the step is complete
			self._step.event -= self.event
			self._step.log -= self.log
			self._step = None

			if isinstance(passthrough, failure.Failure):
				d.errback(passthrough)
			else:
				d.callback(passthrough)

		# If a parent is allocated, pass on any events.
		if self.parent is not None:
			self._step.event += self.event

		# Always pass on log events
		self._step.log += self.log

		# Run the step
		self._step.reset()
		self._step.run(parent = self.parent).addBoth(remove_events)

		return d

	def _reset (self):
		Looping._reset(self)
		self._calls = 0

	def _cancel (self, abort = False):
		Looping._cancel(self, abort)

		# If fn returned a Deferred, continue to wait on it
		if isinstance(self._step, defer.Deferred):
			return self._step

		try:
			return self._step.cancel(abort)
		except AttributeError:
			pass # step might be None
		except NotRunning:
			pass # no problem


class Trigger (Tick):
	"""
	This is a dependent that runs a function as soon as a test evaluates to True.

	The function can return a value, a Deferred, or a Runnable to be executed.
	The function can also be a Runnable to be executed.

	If the function is or returns a Runnable then the Runnable must complete
	before the next iteration can begin, no matter how long it takes.

	Log entries for the Runnable are passed on to the step to which the 
	dependent is attached.

	If Tick is run with a parent parameter then all events are passed on
	to the parent.
	"""

	interval = 0.1

	def __init__ (self, expr, fn, max_calls = None, interval = None, fnArgs = None, fnKeywords = None):
		"""
		Initialise a Trigger.

		@type expr: Expression (or value; but that would be relatively pointless).
		@type fn:  callable or Runnable.
		@param fn: The function or sequence to execute.
		@param max_calls: Maximum number of times to run the function. Pass None for unlimited.
		@param interval: Frequency in seconds at which to test expr.
		@param fnArgs: Arguments to pass to fn.
		@param fnKeywords: Keyword arguments to pass to fn.
		"""

		Tick.__init__(self, fn,
			interval = (interval or Trigger.interval), 
			now = True,
			max_calls = max_calls,
			fnArgs = fnArgs, 
			fnKeywords = fnKeywords
		)

		self._expr = expr

	def _test (self):
		return bool(self._expr)


class Dependents (Dependent):
	
	def __init__ (self):
		Dependent.__init__(self)
		self._dependents = set()

	def add (self, dep):
		if hasattr(dep, "container") and dep.container is not None:
			raise Exception("Dependent is already assigned")

		self._dependents.add(dep)
		dep.container = self

		try:
			dep.event += self.event
		except (AttributeError, TypeError):
			pass

		try:
			dep.log += self.log
		except (AttributeError, TypeError):
			pass

		if self.state is State.RUNNING:
			dep.run()

		return dep

	def remove (self, dependent):
		try:
			self._dependents.remove(dependent)
		except KeyError:
			pass
		else:
			if self.state in (State.RUNNING, State.PAUSED):
				dependent.cancel()

			dependent.container = None

		try:
			dep.event -= self.event
		except (AttributeError, TypeError):
			pass

		try:
			dep.log -= self.log
		except (AttributeError, TypeError):
			pass

	# Runnable

	def _run (self):
		for d in self._dependents:
			try:
				d.run()
			except AlreadyRunning:
				pass
			except Exception as e:
				return defer.fail(e)

		return defer.succeed(None)

	def _reset (self):
		r = []

		for d in self._dependents:
			try:
				r.append(d.reset())
			except AlreadyRunning:
				r.append(d.cancel().addCallback(lambda _: d.reset())) # May take a while - should return a deferred. So all these functions should return deferred's (like run?)

		return defer.gatherResults(r)

	# Pausable

	def _pause (self):
		r = []

		for d in self._dependents:
			try:
				r.append(d.pause())
			except NotRunning:
				pass

		return defer.gatherResults(r)

	def _resume (self):
		r = []

		for d in self._dependents:
			try:
				r.append(d.resume())
			except NotPaused:
				pass

		return defer.gatherResults(r)

	# Cancelable

	def _cancel (self, abort = False):
		r = []

		for d in self._dependents:
			try:
				r.append(d.cancel(abort))
			except NotRunning:
				pass

		return defer.gatherResults(r)
