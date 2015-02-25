# Twisted Imports
from twisted.internet import defer, task
from twisted.python import failure, log

# System Imports
import logging
from exceptions import AttributeError

# Package Imports
from .. import util, data
from ..data.data import BaseVariable
from ..image.data import Image

# Sibling Imports
from interface import InterfaceSection

__all__ = ["Machine", "Component", "ComponentList", "Stream", "Property"]

class Component (object):
	"""
	A sub-component of a Machine.
	
	This can encapsulate sub-components (such as each of two pumps 
	on a multi-pump system). Components can contain methods, 
	Streams and Properties.
	"""

	@property
	def variables (self):
		base = self.alias

		if base is not "":
			base += "."

		# Enumerate public variables
		varList = dict([
			(base + x, getattr(self, x)) 
			for x in vars(self) 
			if (isinstance(getattr(self, x), BaseVariable) \
			or isinstance(getattr(self, x), Image))
		])

		# Reduce likelihood of recursion by avoiding any private variables
		cptList = [
			x for x in vars(self) 
			if isinstance(getattr(self, x), Component) and x[0] != "_"
		]

		for x in cptList:
			varList.update(getattr(self, x).variables)

		return varList

	@property
	def controls (self):
		ctrlList = dict([
			(getattr(self, x).alias, getattr(self, x)) 
			for x in vars(self) 
			if isinstance(getattr(self, x), data.control.Control)
		])

		# Reduce likelihood of recursion by avoiding any private variables
		cptList = [
			x for x in vars(self) 
			if isinstance(getattr(self, x), Component) and x[0] != "_"
		]

		for x in cptList:
			ctrlList.update(getattr(self, x).controls)

		return ctrlList

	@property
	def alias (self):
		try:
			return self._alias
		except AttributeError:
			return ""

	@alias.setter
	def alias (self, alias):

		self._alias = alias
		base = alias + "."

		for x in vars(self):
			if x[0] == "_":
				pass

			elif isinstance(getattr(self, x), BaseVariable):
				getattr(self, x).alias = base + x

			elif isinstance(getattr(self, x), Component):
				getattr(self, x).alias = base + x

			elif isinstance(getattr(self, x), Image):
				getattr(self, x).alias = base + x

	def __setattr__ (self, name, value):
		try:
			var = getattr(self, name)

			if isinstance(var, data.Variable):
				return var.set(value);

		except AttributeError:
			pass

		return object.__setattr__(self, name, value)


class ComponentList (Component, list):
	"""
	A list of components, e.g. if a machine has a number of
	identical components.

	NB all members must be subclasses of Component. This is
	not checked.
	"""

	@property
	def variables (self):
		# Enumerate public variables
		varList = {}

		# Reduce likelihood of recursion by avoiding any private variables
		for component in self:
			varList.update(component.variables)

		return varList

	@property
	def controls (self):
		ctrlList = {}

		for component in self:
			ctrlList.update(component.controls)

		return ctrlList

	@property
	def alias (self):
		try:
			return self._alias
		except AttributeError:
			return ""

	@alias.setter
	def alias (self, alias):

		self._alias = alias
		base = alias + "."

		for i, component in enumerate(self):
			component.alias = base + str(i)


class Machine (Component):

	_machine_count = 0

	title            = "Machine"
	protocolFactory  = None
	protocol         = None
	ui               = InterfaceSection()
	_ticks           = []

	@property
	def connected (self):
		try:
			return self.protocol is not None
		except AttributeError:
			return False

	def disconnect (self):
		self.stop()
		try:
			self.protocol.transport.loseConnection()
		except AttributeError:
			pass

	def __init__(self, endpoint, alias = None, **kwargs):

		if alias is None:
			Machine._machine_count += 1
			alias = self.__class__.__name__ + "_" + str(Machine._machine_count)

		self.ready = defer.Deferred()
		self.setup(**kwargs)

		# Must be called after setup() as this assignment
		# propagates the alias to all of the variables.
		self.alias = alias

		connection_name = ""

		def startError (failure):
			self.disconnect()
			self.ready.errback(failure)

		def connected (protocol):
			log.msg("Connected to endpoint", level = logging.DEBUG)

			self.protocol = protocol
			self.protocol.connection_name = connection_name

			started = defer.maybeDeferred(self.start)
			started.addCallbacks(self.ready.callback, startError)

		def disconnected (reason):
			self.stop()
			del self.protocol

		def endpointReady (endpoint):
			connection_name = endpoint.name

			log.msg("Connecting to endpoint %s" % connection_name, level = logging.DEBUG)

			d = defer.maybeDeferred(endpoint.connect, self.protocolFactory)
			d.addCallbacks(connected, self.ready.errback)

		# If transport is a Deferred, wait for it to be ready
		defer.maybeDeferred(lambda x: x, endpoint).addCallback(endpointReady)

	def setup (self, **kwargs):
		pass

	def start (self):
		pass

	def stop (self):
		pass

	def reset (self):
		return defer.succeed(None)

	def pause (self):
		return defer.succeed(None)

	def resume (self):
		return defer.succeed(None)

	def _tick (self, fn, interval):
		c = task.LoopingCall(fn)
		c.start(interval, now = True)
		self._ticks.append(c)

		return c

	def _stopTicks (self):
		for t in self._ticks:
			if t.running:
				t.stop()

	def __str__ (self):
		return "<%s at %s (%s)>" % (
			self.__class__.__name__,
			hex(id(self)),
            "connected" if self.connected else "disconnected"
		)
	__repr__ = __str__


# Continuous variables
class Stream (data.Variable):
	def __init__ (self, title, type, unit = None):
		data.Variable.__init__(self, type)

		self.title = title
		self.unit = unit

	def set (self, value):
		raise data.errors.Immutable

	def __repr__ (self):
		return "<{class_name} at {reference}: {var_alias} ({var_type}) = {var_value}{var_unit}>".format(
			class_name = self.__class__.__name__, 
			reference = hex(id(self)),
			var_alias = self.alias,
            var_type = self.type.__name__,
			var_value = self.value,
			var_unit = self.unit
		)
	# _push is used internally to add data coming in from the machine.


# Discrete (ish) variables
class Property (Stream):
	def __init__ (self, title, type, options = None, min = None, max = None, unit = None, setter = None):
		Stream.__init__(self, title, type, unit)

		self.options = options
		self.min = min
		self.max = max
		self._setter = setter

		# Properties are expected to change infrequently,
		# Therefore all values are stored.
		self._length = None
		self._archive.threshold_factor = None

	def set (self, value):
		if self._setter is None:
			raise data.errors.Immutable

		value = self._type(value)

		try:
			self.check(value)
			return defer.maybeDeferred(self._setter, value)
		except Exception as err:
			return defer.fail(err)

	def _push (self, value, time = None):
		if type(value) != self.type:
			value = self.type(value)

		# Ignore repeat values
		if value != self.value:
			# Make a step change by inserting the initial and
			# final values at the same time.
			if self.value is not None:
				data.Variable._push(self, self.value, time)

			data.Variable._push(self, value, time)

	def check (self, value):
		if self.options is not None and value not in self.options:
			raise data.errors.InvalidValue

		if self.min is not None and value < self.min:
			raise data.errors.ValueTooSmall

		if self.max is not None and value > self.max:
			raise data.errors.ValueTooLarge

		return True

	def get (self, start, interval = None, step = 1):
		return self._archive.get(start, interval)


class Error (Exception):
	"""Base class for exceptions in this module."""
	pass


class MachineBusy (Error):
	"""Exception raised if an attempt is made to load a machine
	which is already connected to another process."""
	pass
