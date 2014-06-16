# Twisted Imports
from twisted.internet import reactor, defer, error
from twisted.python import failure

# System Imports
from time import time as now
from collections import deque

# NumPy
import numpy as np


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
	def on (self, name, function):
		try:
			self._events[name]
		except AttributeError:
			self._events = {}
			self._events[name] = []
		except KeyError:
			self._events[name] = []

		if function not in self._events[name]:
			self._events[name].append(function)
	
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
	
	def trigger (self, name, *args, **kwargs):
		try:
			events = this._events[name]
		except AttributeError
			return
		except KeyError:
			pass
		else:
			for function in events:
				function(*args, **kwargs)
		
		try:
			events = this._events["all"]
		except KeyError:
			pass
		else:
			for function in events:
				function(name, *args, **kwargs)
		

def timerange (start, interval, step):
	if start < 0:
			start = now() + start

	return np.arange(start, start + interval, step, float)



class AsyncQueue (object):
	@property
	def running (self):
		return self._workers > 0

	@property
	def current (self):
		return self._current

	def __init__ (self, worker, concurrency = 1, paused = False):
		self._tasks = deque()
		self._worker = worker
		self._workers = 0
		self._concurrency = concurrency
		self._paused = int(paused)
		self._current = set()

		self.drained = Event()

	def pause (self):
		self._paused += 1

	def resume (self):
		self._paused -= 1
		self._process()

	def append (self, data):
		task = _AsyncQueueTask(data)
		self._tasks.append(task)
		reactor.callLater(0, self._process)
		return task.d

	def appendleft (self, data):
		task = _AsyncQueueTask(data)
		self._tasks.appendleft(task)
		reactor.callLater(0, self._process)
		return task.d

	def _process (self):
		if not self._paused and self._workers < self._concurrency:
			def run (task):
				worker_d = defer.maybeDeferred(self._worker, task.data)
				worker_d.addCallbacks(success, error)

			def success (result):
				task.d.callback(result)
				next()

			def error (reason):
				if reason.type is AsyncQueueRetry:
					run(task)
				else:
					task.d.errback(reason)
					next()

			def next ():
				self._workers -= 1
				self._current.discard(task)
				reactor.callLater(0, self._process)

			try:
				task = self._tasks.popleft()
			except IndexError:
				self.drained()
			else:
				self._workers += 1
				self._current.add(task)
				run(task)

	def __len__ (self):
		return len(self._tasks)

class AsyncQueueRetry (Exception):
	pass

class _AsyncQueueTask (object):
	def __init__ (self, data, deferred = None):
		self.data = data
		self.d = deferred or defer.Deferred()
