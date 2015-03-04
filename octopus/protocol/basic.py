# Twisted Imports
from twisted.internet import reactor, defer
from twisted.internet.error import TimeoutError, AlreadyCalled, AlreadyCancelled
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log, failure

# System Imports
import exceptions
from collections import deque, namedtuple
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


class VaryingDelimiterQueuedLineReceiver (QueuedLineReceiver):
	Command = namedtuple('Command', [
		'index',
		'line',
		'expectReply',
		'wait',
		'length',
		'lengthFn',
		'endDelimiter',
		'endDelimiterLength',
		'startDelimiter',
		'startDelimiterLength',
		'd'
	])

	start_delimiter = None
	end_delimiter = None
	length = None

	def write (self, line, expect_reply = True, wait = 0, length = None,
		start_delimiter = None, end_delimiter = None):

		# length can be a callable, which when passed the
		# contents of the buffer (excluding start delim), should return either
		# None (not enough data yet) or an integer to use as the line length
		# (excluding length of delimiters).

		if length is None:
			length = self.length

		if start_delimiter is None:
			start_delimiter = self.start_delimiter

		if end_delimiter is None:
			end_delimiter = self.end_delimiter

		if callable(length):
			lengthFn = length
			length = None
		else:
			lengthFn = None

		d = defer.Deferred()
		command = self.Command(
			self.index.next(),
			line,
			expect_reply,
			wait,
			length,
			lengthFn,
			end_delimiter,
			len(end_delimiter or ''),
			start_delimiter,
			len(start_delimiter or ''),
			d
		)
		self.queue.append(command)

		return d

	def dataReceived (self, data):
		current = self._current

		if current is None:
			self.unexpectedMessage(data)
			return

		self._buffer += data

		# If there is a start delimiter, discard any data before the delimiter.
		if current.startDelimiter is not None:
			try:
				idx = self._buffer.index(current.startDelimiter)
				if idx > 0:
					self._buffer = self._buffer[idx:]

			except ValueError:
				# Haven't received a start delimiter yet
				self._buffer = ''
				return

		# If the length needs to be calculated, try to do so.
		if current.length is None and current.lengthFn is not None:
			length = current.lengthFn(self._buffer[current.startDelimiterLength:])

			if length is not None:
				current.length = length

		# If a length was specified, attempt to return this many characters.
		if current.length is not None:
			start = current.startDelimiterLength
			end = current.startDelimiterLength + current.length

			if len(self._buffer) >= start + end:
				line = self._buffer[start:end]

				# Check that the end delimiter is present in the correct place
				# if not, the start delimiter may have been located too early.
				# Discard the first character in the buffer and start again
				if self._buffer[end:end + current.endDelimiterLength] != current.endDelimiter:
					self._buffer = self._buffer[1:]

					# In this case the length would need to be calculated again
					if current.lengthFn is not None:
						current.length = None

				# Remove the message from the buffer and return it.
				else:
					self._buffer = self._buffer[end + current.endDelimiterLength:]
					self.lineReceived(line)

		# If no length was specified, look for the end delimiter
		elif current.expectEndDelimiter is not None \
		and current.lengthFn is None:
			try:
				# Select data up to the end delimiter
				idx = self._buffer.index(current.endDelimiter)

			except ValueError:
				# Haven't received an end delimiter yet
				return

			line = self._buffer[current.startDelimiterLength:idx]
			self._buffer = self._buffer[idx + current.endDelimiterLength:]

			self.lineReceived(line)

		# something weird to do with the brainboxes?
		if self._buffer[:9] == '\xff\xfd\x03\xff\xfd\x00\xff\xfd,':
			self._buffer = self._buffer[9:]
