# Twisted Imports
from twisted.internet import reactor, defer
from twisted.internet.error import TimeoutError, AlreadyCalled, AlreadyCancelled
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log, failure

# System Imports
import exceptions
from collections import deque
import logging

# Package Imports
from ..util import AsyncQueue, AsyncQueueRetry


class _Command (object):
	def __init__ (self, index, line, expectReply, wait):
		self.index = index
		self.line = line
		self.expectReply = bool(expectReply)
		self.wait = float(wait)
		self.d = defer.Deferred()


def _IndexGenerator (max):
	i = 0

	while True:
		yield i
		i += 1
		i %= max


class QueuedLineReceiver (LineOnlyReceiver):

	timeoutDuration = 1

	def __init__ (self):
		self.connection_name = "disconnected"

		self.queue = AsyncQueue(self._advance, paused = True)
		self.index = _IndexGenerator(2 ** 16)

		self._current = None
		self._queue_d = None
		self._timeout = None
		self._running = False

	def connectionMade (self):
		self.queue.resume()

	def connectionLost (self, reason):
		self.queue.pause()

	def _log (self, msg, level = None):
		log.msg(
			"QueuedLineReceiver [%s]: %s" % (
				self.connection_name, 
				msg
			), 
			logLevel = level
		)

	def write (self, line, expectReply = True, wait = 0):
		command = _Command(self.index.next(), line, expectReply, wait)
		self.queue.append(command)

		return command.d

	def _advance (self, command):
		self._current = command
		self._queue_d = defer.Deferred()

		self.sendLine(command.line)

		if command.expectReply:
			self._timeout = reactor.callLater(self.timeoutDuration, self._timeoutCurrent)

		else:
			# Avoid flooding the network or the device. 
			# 30ms is approximately a round-trip time.
			reactor.callLater(command.wait, command.d.callback, None)
			reactor.callLater(max(command.wait, 0.03), self._queue_d.callback, None)

		return self._queue_d

	def dataReceived (self, data):
		self._buffer += data

		# something weird to do with the brainboxes?
		if self._buffer[:9] == '\xff\xfd\x03\xff\xfd\x00\xff\xfd,':
			self._buffer = self._buffer[9:]

		return LineOnlyReceiver.dataReceived(self, "")

	def lineReceived (self, line):
		if len(line) is 0:
			return

		try:
			self._timeout.cancel()

			command = self._current
			reactor.callLater(command.wait, command.d.callback, line)
			reactor.callLater(command.wait, self._queue_d.callback, None)

		except (AttributeError, AlreadyCalled, AlreadyCancelled):
			# Either a late response or an unexpected Message
			return self.unexpectedMessage(line)

		finally:
			self._current = None
			self._queue_d = None
			self._timeout = None

	def unexpectedMessage (self, line):
		pass

	def _timeoutCurrent (self):
		try:
			self._log("Timed Out: %s" % self._current.line, logging.ERROR)
			self._current.d.errback(TimeoutError(self._current.line))
			self._queue_d.errback(TimeoutError(self._current.line))

		except exceptions.AttributeError:
			# There is actually no current command
			pass

