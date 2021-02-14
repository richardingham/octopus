# System Imports
import functools

# Twisted Imports
from twisted.logger import Logger

log = Logger()

class Event (object):
	def __init__(self):
		self.handlers = set()

	def handle(self, handler):
		self.handlers.add(handler)
		return self

	def unhandle(self, handler):
		self.handlers.discard(handler)
		return self

	def fire(self, *args, **kargs):
		for handler in self.handlers:
			handler(*args, **kargs)

	def getHandlerCount(self):
		return len(self.handlers)

	__iadd__ = handle
	__isub__ = unhandle
	__call__ = fire
	__len__  = getHandlerCount


class EventEmitter (object):
	def on (self, name, function = None):
		def _on (function):
			try:
				self._events[name]
			except (TypeError, AttributeError):
				self._events = {}
				self._events[name] = []
			except KeyError:
				self._events[name] = []

			# Use is instead of in to avoid equality comparison
			# (this would create extra expression objects).
			for f in self._events[name]:
				if function is f:
					return function

			self._events[name].append(function)

			return function

		if function is None:
			return _on
		else:
			return _on(function)

	def once (self, name, function = None):
		def _once (function):
			@functools.wraps(function)
			def g (*args, **kwargs):
				function(*args, **kwargs)
				self.off(name, g)

			return g

		if function is None:
			return lambda function: self.on(name, _once(function))
		else:
			self.on(name, _once(function))

	def off (self, name = None, function = None):
		try:
			self._events
		except AttributeError:
			return

		# If no name is passed, remove all handlers
		if name is None:
			self._events.clear()

		# If no function is passed, remove all functions
		elif function is None:
			try:
				self._events[name] = []
			except KeyError:
				pass

		# Remove handler [function] from [name]
		else:
			self._events[name].remove(function)

	def listeners (self, event):
		try:
			return self._events[event]
		except (AttributeError, KeyError):
			return []

	def emit (self, _event, **data):
		handled = False

		try:
			events = self._events[_event][:]
		except AttributeError:
			return False # No events defined yet
		except KeyError:
			pass
		else:
			handled |= bool(len(events))

			for function in events:
				try:
					function(data)
				except:
					log.failure()

		try:
			events = self._events["all"][:]
		except KeyError:
			pass
		else:
			handled |= bool(len(events))

			for function in events:
				try:
					function(_event, data)
				except:
					log.failure()

		return handled
