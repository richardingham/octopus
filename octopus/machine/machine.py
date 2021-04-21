# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.python import failure, log
from twisted.logger import Logger

# System Imports
import logging

# Package Imports
from .. import util, data
from ..data.data import BaseVariable
from ..image.data import Image

# Sibling Imports
from .interface import InterfaceSection

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

		if base != "":
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
	_ticks           = None

	log = Logger()

	@property
	def connected (self):
		try:
			return self.protocol is not None
		except AttributeError:
			return False

	def disconnect (self):
		self.log.debug(
			"Machine: {log_source.alias!s} - disconnect()"
		)

		self.stop()
		try:
			self.protocol.transport.loseConnection()
		except AttributeError:
			pass
	
		self.protocol = None
	
	def waitUntilReady (self):
		if self.connected:
			return defer.succeed(True)
		elif self._startError is not None:
			return defer.fail(self._startError)
		
		d = defer.Deferred()
		self._connectedWaits.append(d)
		return d

	def __init__(self, endpoint, alias = None, **kwargs):

		self._ticks = []
		self._connectedWaits = []
		self._startError = None

		if alias is None:
			Machine._machine_count += 1
			alias = self.__class__.__name__ + "_" + str(Machine._machine_count)

		self.setup(**kwargs)

		# Must be called after setup() as this assignment
		# propagates the alias to all of the variables.
		self.alias = alias

		def callbackReady (_):
			for d in self._connectedWaits:
				d.callback(True)
		
		def errbackReady (failure):
			self._startError = failure

			for d in self._connectedWaits:
				d.errback(failure)

		@defer.inlineCallbacks
		def connect ():
			if isinstance(endpoint, defer.Deferred):
				self.log.debug(
					"Machine: {log_source.alias!s} - waiting for endpoint",
					state = 'awaiting endpoint'
				)

				connected_endpoint = yield connected_endpoint

			else:
				connected_endpoint = endpoint

			# Endpoint is ready
			connection_name = connected_endpoint.name

			self.log.debug(
				"Machine: {log_source.alias!s} - connecting to endpoint {endpoint.name}",
				state = 'connecting to endpoint',
				endpoint = connected_endpoint
			)

			try:
				protocol = yield defer.maybeDeferred(connected_endpoint.connect, self.protocolFactory)
			except Exception as e:
				errbackReady(e)
				raise

			# Connection made
			self.protocol = protocol
			self.protocol.connection_name = connection_name
			self.protocol.machine_alias = alias

			self.log.debug(
				"Machine: {log_source.alias!s} - connected to endpoint {protocol.connection_name}",
				state = 'connected',
				protocol = protocol
			)

			try:
				start_result = yield defer.maybeDeferred(self.start)
				callbackReady(start_result)

			except Exception as e:
				self.log.error(
					"Machine: {log_source.alias!s} - error during start",
					state = 'error start',
					failure = failure
				)

				self.disconnect()
				errbackReady(e)
				raise

		# def disconnected (reason):
		# 	self.log.debug(
		# 		"Machine: {log_source.alias!s} - disconnected {reason}",
		# 		reason = reason
		# 	)

		# 	self.stop()
		# 	del self.protocol
		
		connect().addErrback(log.err)

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
			return defer.fail(data.errors.Immutable())

		try:
			value = self._type(value)
		except ValueError:
			return defer.fail(data.errors.InvalidType(f"{self.alias}: Unable to convert {value!r} into {self._type}."))

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
			raise data.errors.InvalidValue(f"{self.alias}: {value!r} is not a valid option. Allowed values: {self.options}")

		if self.min is not None and value < self.min:
			raise data.errors.ValueTooSmall(f"{self.alias}: {value} is below the minimum value of {self.min}")

		if self.max is not None and value > self.max:
			raise data.errors.ValueTooLarge(f"{self.alias}: {value} is above the maximum value of {self.max}")

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
