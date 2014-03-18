# Twisted Imports
from twisted.python import log

# Package Imports
from ..constants import State
from ..util import now

# Sibling Imports
import util
import error


class Bind (util.Looping, util.Dependent):
	"""
	Connects a variable to an expression.
	
	Each iteration, the value of expr is evaluated. 
	If process is defined, then the result is passed through this function.
	(If expr is None, then the return value of process is used).
	
	variable is updated with this new value.
	
	Process must be a function that accepts one parameter, 
	usually a Variable or Expression.

	Set max and min to limit the value of variable.
	"""

	@property
	def interval (self):
		return self._interval

	# NB altering interval doesn't work when running.
	# Maybe make an EditableInterval mixin that restarts the LoopingCall
	# if it is running.
	@interval.setter
	def interval (self, value):
		self._interval = value

	max = None
	min = None

	class NoUpdate (Exception):
		"""
		Throw this exception from process function to prevent variable
		from being changed.
		"""

		pass

	def __init__ (self, variable, expr = None, process = None):
		util.Dependent.__init__(self)
		util.Looping.__init__(self, interval = 0.5)

		self.variable = variable
		self.expr = expr
		self.process = process

	def _iterate (self):
		# Use self.process if set
		if callable(self.process):
			try:
				new_val = self.process(self.expr)
			except NoUpdate:
				return
		else:
			new_val = self.expr.value

		# Enforce bounds
		if self.max is not None:
			new_val = min(new_val, self.max)
		if self.min is not None:
			new_val = max(new_val, self.min)

		# Temporary optimisation - eventually add update triggers to variables.
		if self.variable.value != new_val:
			# Return a value so that self._calls gets incremented,
			# swallow any errors to avoid terminating the loop.
			return self.variable.set(new_val).addErrback(log.err)



class PID (util.Looping, util.Dependent):
	"""
	PID controller.
	
	Each iteration, response is updated with a new value based on
	the error variable.
	
	Alter the proportional, integral and differential parameters
	to alter the nature of the response.

	Set max and min to limit the response value.
	"""

	@property
	def interval (self):
		return self._interval

	@interval.setter
	def interval (self, value):
		self._interval = value

	proportional = 25
	integral = 0.25
	differential = 500

	max = None
	min = None

	def __init__ (self, response, error):
		util.Dependent.__init__(self)
		util.Looping.__init__(self, interval = 0.5)

		self.error = error
		self.response = response
		self._prev_error = None

	def _iterate (self):
		current = float(self.response)
		interval = float(self.interval)

		e = float(self.error)
		e_prev, self._prev_error = self._prev_error, e

		if e_prev is None:
			return

		# trapezium rule
		integral_term = \
			(min(e, e_prev) * interval) + \
			(0.5 * (e + e_prev) * interval)

		# difference rule
		differential_term = (e - e_prev) / interval

		# PID control
		change = \
			(self.proportional * e) + \
			(self.integral * integral_term) + \
			(self.differential * differential_term)

		new = current + change

		# Enforce bounds
		if self.max is not None:
			new = min(new, self.max)
		if self.min is not None:
			new = max(new, self.min)

		self.response.set(new)


class StateMonitor (util.Looping, util.Dependent):
	"""
	Monitors a set of expressions.

	Add an expression to the set of tests with:
		monitor.add(expr)

	If any of the monitors becomes False, monitor.trigger_step is run.
	When the monitors become True, monitor.trigger_step is cancelled and
	monitor.reset_step is run. (If the monitor is triggered again,
	reset_step is cancelled before trigger_step is run).
	
	Parameters:
		auto_reset: If False, then reset_trigger() must be called
		            before the monitor can be triggered again.
		cancel_on_trigger: If False, then reset_step will not be
					cancelled.
		cancel_on_reset: If False, then trigger_step will not be cancelled.
	
	"""

	@property
	def interval (self):
		return self._interval

	@interval.setter
	def interval (self, value):
		self._interval = value

	@property
	def trigger_step (self):
		return self._trigger_step

	@trigger_step.setter
	def trigger_step (self, step):
		self._trigger_step = util.init_child(self, step)

	@property
	def reset_step (self):
		return self._reset_step

	@reset_step.setter
	def reset_step (self, step):
		self._reset_step = util.init_child(self, step)

	def __init__ (self, tests = None, trigger_step = None, reset_step = None, auto_reset = True, cancel_on_trigger = True, cancel_on_reset = True):
		util.Dependent.__init__(self)
		util.Looping.__init__(self, interval = 0.5)

		self.tests = set()

		if tests is not None:
			for t in tests:
				self.add(t)

		self.trigger_step = trigger_step
		self.reset_step = reset_step

		self._triggered = False
		self.cancel_on_trigger = cancel_on_trigger
		self.cancel_on_reset = cancel_on_reset
		self.auto_reset = auto_reset

	def add (self, test):
		"""
		Add an expression to the set that is tested. If test becomes
		False, the monitor is triggered.
		"""

		self.tests.add(test)

	def remove (self, test):
		"""
		Remove an expression from the set of tests.
		"""

		self.tests.discard(test)

	def _iterate (self):
		# If the monitor is already triggered, check if we need to reset.
		if self._triggered:
			if self.auto_reset and all(self.tests):
				self.reset_trigger()

		# Check if the monitor should be triggered.
		elif not all(self.tests):
			# Cancel reset_step
			try:
				if self.cancel_on_trigger:
					self.reset_step.cancel()
			except error.NotRunning:
				pass

			# Run trigger_step
			try:
				self.trigger_step.reset()
				self.trigger_step.run()
			except error.AlreadyRunning:
				return

			self._triggered = True

			# Increment _calls
			return True

	def reset_trigger (self, run_reset_step = True):
		self._triggered = False

		if self.cancel_on_reset:
			try:
				self.trigger_step.cancel()
			except error.NotRunning:
				pass

		if run_reset_step:
			try:
				self.reset_step.reset()
				self.reset_step.run()
			except error.AlreadyRunning:
				return

	def _cancel (self, abort = False):
		util.Looping._cancel(self, abort)
		self.reset_trigger()
