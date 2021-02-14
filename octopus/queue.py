# System Imports
import asyncio
from collections import deque
import functools

# Sibling Imports
from .events import Event


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
		asyncio.create_task(self._process)
		return task.d

	def appendleft (self, data):
		task = _AsyncQueueTask(data)
		self._tasks.appendleft(task)
		asyncio.create_task(self._process)
		return task.d

	async def _process (self):
		if not self._paused and self._workers < self._concurrency:
			try:
				task = self._tasks.popleft()
			except IndexError:
				self.drained()
				return

			self._workers += 1
			self._current.add(task)
			
			try:
				result = self._worker(task.data)
				if asyncio.isfuture(result):
					task.d.set_result(await result)
				else:
					task.d.set_result(result)
			except Exception as err:
				task.d.set_exception(err)
			
			self._workers -= 1
			self._current.discard(task)

			asyncio.create_task(self._process)

	def __len__ (self):
		return len(self._tasks)


class AsyncQueueRetry (Exception):
	pass


class _AsyncQueueTask (object):
	def __init__ (self, data, future = None):
		self.data = data
		self.d = future or asyncio.Future()
