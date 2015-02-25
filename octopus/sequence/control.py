# Twisted Imports
from twisted.python import log

# Package Imports
from ..constants import State
from ..util import now

# Sibling Imports
import util
import error


class Bind (util.Dependent):
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

		self.variable = variable
		self.expr = expr
		self.process = process

	def _run (self):
		self.expr.on("change", self._update)

	def _cancel (self):
		self.expr.off("change", self._update)

	def _update (self, data):
		if self.state is not State.RUNNING:
			return

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

	proportional = 0.5
	integral = 0.05
	differential = 0

	max = None
	min = None

	max_integral = 500
	min_integral = -500

	def __init__ (self, response, error, proportional = None, integral = None, differential = None, max = None, min = None, interval = 0.5):
		util.Dependent.__init__(self)
		util.Looping.__init__(self, interval)

		self.error = error
		self.response = response

		if proportional is not None:
			self.proportional = proportional
		if integral is not None:
			self.integral = integral
		if differential is not None:
			self.differential = differential

		self.max = max
		self.min = min

		self._prev_error = None
		self._integral = 0 # Accumulated integral

	def reset_integral (self):
		self._integral = 0

	def _integral_bound (self, integral):
		if self.max_integral is not None:
			integral = min(integral, self.max_integral)
		if self.min_integral is not None:
			integral = max(integral, self.min_integral)

		return integral

	def _output_bound (self, new):
		if self.max is not None:
			new = min(new, self.max)
		if self.min is not None:
			new = max(new, self.min)

		return new

	def _iterate (self):
		current = float(self.response)
		interval = float(self.interval)

		e = float(self.error)
		e_prev, self._prev_error = self._prev_error, e

		if e_prev is None:
			return

		# Trapezium rule
		integral_term = self._integral + \
			(min(e, e_prev) * interval) + \
			(0.5 * (e + e_prev) * interval)

		integral_term = self._integral_bound(integral_term)
		self._integral = integral_term

		# Difference rule
		differential_term = (e - e_prev) / interval
		self._differential = differential_term

		# Compute PID
		change = \
			(self.proportional * e) + \
			(self.integral * integral_term) + \
			(self.differential * differential_term)

		new = current + change

		# Enforce bounds
		new = self._output_bound(new)

		self.response.set(new)


class StateMonitor (util.Dependent):
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

		self._tests = set()

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

		self._tests.add(test)

		if self.state is State.RUNNING:
			test.on("change", self._changed)

	def remove (self, test):
		"""
		Remove an expression from the set of tests.
		"""

		self._tests.discard(test)

		try:
			test.off("change", self._changed)
		except KeyError:
			pass

	def _changed (self, data = None):
		if self.state is not State.RUNNING:
			return

		# If the monitor is already triggered, check if we need to reset.
		if self._triggered:
			if self.auto_reset and all(self._tests):
				self.reset_trigger()

		# Check if the monitor should be triggered.
		elif not all(self._tests):
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

	def _run (self):
		for test in self._tests:
			test.on("change", _changed)

		_changed()

	def _cancel (self, abort = False):
		self.reset_trigger()

		for test in self._tests:
			try:
				test.off("change", _changed)
			except KeyError:
				pass

	def _pause (self):
		d = []

		try:
			d.append(self.trigger_step.pause())
		except error.NotRunning:
			pass

		try:
			d.append(self.reset_step.pause())
		except error.NotRunning:
			pass

		return defer.gatherResults(d)

	def _resume (self):
		d = []

		try:
			d.append(self.trigger_step.resume())
		except error.NotRunning:
			pass

		try:
			d.append(self.reset_step.resume())
		except error.NotRunning:
			pass

		return defer.gatherResults(d)

