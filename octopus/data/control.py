"""
Provides controls that appear in the web user interface of an experiment.

Controls are generally associated with a data.Variable (most commonly 
a data.Property) which is updated when the user operates the control.

UI updates of the control are handled by the Variable.

A special case is the Button, which is associated with a function rather
than a variable.
"""

# Package Imports
from ..util import Event

# Sibling Imports
import errors

class Control (object):
	_counter = 0

	type = "control"

	def __init__ (self, variable = None):
		Control._counter += 1
		self.alias = "control_" + str(Control._counter)

		self._variable = variable
		self._disabled = False

		self.event = Event()

	@property
	def title (self):
		try:
			return self._title
		except AttributeError:
			pass

		try:
			return self._variable.title
		except AttributeError:
			return ""

	@title.setter
	def title (self, value):
		self._title = value

	@property
	def unit (self):
		try:
			return self._variable.unit
		except AttributeError:
			return None

	@property
	def var_alias (self):
		try:
			return self._variable.alias
		except AttributeError:
			return None

	@property
	def value (self):
		try:
			return self._variable.value
		except AttributeError:
			return None

	def update (self, value):
		"""Called when a remote client operates the control."""

		try:
			if not self._disabled:
				return self._variable.set(value)

		except errors.Error:
			raise

	def disable (self):
		self._disabled = True
		self.event(item = self, disabled = True)

	def enable (self):
		self._disabled = False
		self.event(item = self, disabled = False)

class Button (Control):
	"""A push button control (not associated with a variable)."""

	type = "button"

	action = None
	"""A function to perform when the button is pressed."""

	args = []
	"""Arguments to be passed to the action function when it is called."""

	kwargs = {}
	"""Keywords to be passed to the action function when it is called."""

	def __init__ (self, title, action = None, *args, **kwargs):
		Control.__init__ (self, None)
		self._title = title
		self.action = action
		self.args = args
		self.kwargs = kwargs

	def update (self, value):
		try:
			if not self._disabled:
				return self.action(*self.args, **self.kwargs)
		except TypeError:
			pass

class Text (Control):
	type = "text"

class Switch (Control):
	"""
	An on/off switch.
	
	The options property should be set with a tuple, where the
	first item is the value when false, and the second the
	value when true.
	"""

	type = "switch"
	options = (False, True)

class Select (Control):
	"""
	A multi-select control.
	
	The options property should contain a dictionary containing
	value => title pairs. A default set of options is created
	from the variable's options property, if it exists.
	"""
	
	type = "select"
	_options = None

	@property
	def options (self):
		if self._options is not None:
			return self._options

		if hasattr("options", self._variable):
			return dict(zip(
				self._variable.options,
				[s.capitalize() for s in self._variable.options]
			))

	@options.setter
	def options (self, value):
		self._options = value

class Number (Control):
	type = "number"

	_min = None
	_max = None

	@property
	def min (self):
		if self._min is not None:
			return self._min
		elif hasattr("min", self._variable):
			return self._variable.min
		else:
			return None

	@min.setter
	def min (self, value):
		self._min = value

	@property
	def max (self):
		if self._max is not None:
			return self._max
		elif hasattr("max", self._variable):
			return self._variable.max
		else:
			return None

	@max.setter
	def min (self, value):
		self._max = value
