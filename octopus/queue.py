# Twisted Imports
from twisted.internet import reactor, defer

# System Imports
from collections import deque
import functools

# Sibling Imports
from octopus.events import Event


class AsyncQueue(object):
    @property
    def running(self):
        return self._workers > 0

    @property
    def current(self):
        return self._current

    def __init__(self, worker, concurrency=1, paused=False):
        self._tasks = deque()
        self._worker = worker
        self._workers = 0
        self._concurrency = concurrency
        self._paused = int(paused)
        self._current = set()

        self.drained = Event()

    def pause(self):
        self._paused += 1

    def resume(self):
        self._paused -= 1
        self._process()

    def append(self, data):
        task = _AsyncQueueTask(data)
        self._tasks.append(task)
        reactor.callLater(0, self._process)
        return task.d

    def appendleft(self, data):
        task = _AsyncQueueTask(data)
        self._tasks.appendleft(task)
        reactor.callLater(0, self._process)
        return task.d

    def _process(self):
        if not self._paused and self._workers < self._concurrency:

            def run(task):
                worker_d = defer.maybeDeferred(self._worker, task.data)
                worker_d.addCallbacks(success, error)

            def success(result):
                task.d.callback(result)
                next()

            def error(reason):
                if reason.type is AsyncQueueRetry:
                    run(task)
                else:
                    task.d.errback(reason)
                    next()

            def next():
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

    def __len__(self):
        return len(self._tasks)


class AsyncQueueRetry(Exception):
    pass


class _AsyncQueueTask(object):
    def __init__(self, data, deferred=None):
        self.data = data
        self.d = deferred or defer.Deferred()
