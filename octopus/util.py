# Twisted Imports
from twisted.internet import reactor, defer, error
from twisted.python import failure

# System Imports
from time import time as now
from collections import deque

# NumPy
import numpy as np


class Event:
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
