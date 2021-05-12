import asyncio

# Package Imports
from octopus.constants import State
from octopus.util import now

# Sibling Imports
from octopus.sequence.util import Looping, Dependent
from octopus.sequence import error


class Bind(Dependent):
	"""
	Connects a variable to an expression.

	Whenever the value of expr changes:
	1. If process is defined, then expr is passed to this function 
	   which should return the new value.
	2. The variable is updated with this new value.

	Process must be a function that accepts one parameter,
	usually a Variable or Expression.

	Set max and min to limit the value of variable.
	"""

	class NoUpdate(Exception):
		"""
		Throw this exception from process function to prevent variable
		from being changed.
		"""

	def __init__(self, variable, expr=None, process=None, max=None, min=None):
		Dependent.__init__(self)

		self.calls = 0
		self.variable = variable
		self.expr = expr
		self.process = process
		self.max = max
		self.min = min
		self._waiter = None

	async def _run(self):
		self.calls = 0

		while True:
			if self.state is State.PAUSED:
				self._waiter = self.resumed.wait()
				await self._waiter

			if self.state is not State.RUNNING:
				return
			
			self._waiter = self.expr.changed.wait()
			await self._waiter

			if self.state is not State.RUNNING:
				continue

			# Use self.process if set
			if callable(self.process):
				try:
					new_val = self.process(self.expr)
				except Bind.NoUpdate:
					continue
			else:
				new_val = self.expr.value

			# Enforce bounds
			if self.max is not None:
				new_val = min(new_val, self.max)
			if self.min is not None:
				new_val = max(new_val, self.min)

			if self.variable.value != new_val:
				self.calls += 1

				try:
					self._waiter = self.variable.set(new_val)
					await self._waiter
				except Exception as err:
					self.log.error(err)
	
	async def _cancel(self, abort=False):
		if self._waiter is not None:
			self._waiter.cancel()


class PID (Looping, Dependent):
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
		Dependent.__init__(self)
		Looping.__init__(self, interval)

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


class StateMonitor(Dependent):
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

	def __init__(self, tests=None, trigger_step=None, reset_step=None, auto_reset=True, cancel_on_trigger=True, cancel_on_reset=True):
		Dependent.__init__(self)

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

		self._trigger_coro_task = None
		self._reset_coro_task = None
		self._tests_changed = asyncio.Event()
		self._trigger_reset = asyncio.Event()

	def add(self, test):
		"""
		Add an expression to the set that is tested. If test becomes
		False, the monitor is triggered.
		"""

		self._tests.add(test)
		self._tests_changed.set()
		self._tests_changed.clear()

	def remove(self, test):
		"""
		Remove an expression from the set of tests.
		"""

		self._tests.discard(test)
		self._tests_changed.set()
		self._tests_changed.clear()

	def reset_trigger(self, run_reset_step=True):
		self._triggered = False

		if self.cancel_on_reset:
			self._trigger_coro_task.cancel()

		if run_reset_step:
			if self._reset_coro_task is None or self._reset_coro_task.done():
				self._reset_coro_task = asyncio.create_task(self.reset_step())

		self._trigger_reset.set()
		self._trigger_reset.clear()

	async def _run(self):
		while True:
			if self.state is State.PAUSED:
				self._waiter = self.resumed.wait()
				await self._waiter

			if self.state is not State.RUNNING:
				return
			
			self._waiter = asyncio.wait(
				[self._tests_changed.wait()] + [test.changed.wait() for test in self._tests()],
				return_when=asyncio.FIRST_COMPLETED
			)
			await self._waiter

			if self.state is not State.RUNNING:
				continue

			# If the monitor is already triggered, check if we need to reset.
			if self._triggered:
				if self.auto_reset and all(self._tests):
					self.reset_trigger()
				elif not self.auto_reset:
					self._waiter = self._trigger_reset.wait()
					await self._waiter

			# Check if the monitor should be triggered.
			elif not all(self._tests):
				# Cancel reset_step
				if self.cancel_on_trigger:
					self._reset_coro_task.cancel()

				# Run trigger_step
				if self._trigger_coro_task is None or self._trigger_coro_task.done():
					self._trigger_coro_task = asyncio.create_task(self.trigger_step())
				else:
					continue

				self._triggered = True

	async def _cancel(self, abort=False):
		if self._waiter is not None:
			self._waiter.cancel()
		
		if self._reset_coro_task is not None:
			self._reset_coro_task.cancel()
		
		if self._trigger_coro_task is not None:
			self._trigger_coro_task.cancel()

	async def _pause(self):
		d = []

		try:
			d.append(self._waiter.pause())
		except AttributeError:
			pass

		try:
			d.append(self._trigger_coro_task.pause())
		except AttributeError:
			pass

		try:
			d.append(self._reset_coro_task.pause())
		except AttributeError:
			pass

		await asyncio.gather(d)

	async def _resume(self):
		d = []

		try:
			d.append(self._waiter.pause())
		except AttributeError:
			pass

		try:
			d.append(self._trigger_coro_task.resume())
		except AttributeError:
			pass

		try:
			d.append(self._reset_coro_task.resume())
		except AttributeError:
			pass

		await asyncio.gather(d)
