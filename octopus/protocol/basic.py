# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.internet.error import TimeoutError, AlreadyCalled, AlreadyCancelled
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log, failure

# System Imports
from collections import deque
import exceptions
import logging

# Package Imports
from ..queue import AsyncQueue, AsyncQueueRetry


def _IndexGenerator (max):
	i = 0

	while True:
		yield i
		i += 1
		i %= max


class QueuedLineReceiver (LineOnlyReceiver):

	class Command (dict):
		def __getattr__ (self, attr):
			return self[attr]

		def __setattr__ (self, attr, value):
			self[attr] = value

	timeout = 1
	character_delay = 0
	max_command_length = 1000
	debug = False

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
			"QueuedLineReceiver [{!s}]: {!s}".format(
				self.connection_name,
				msg
			),
			logLevel = level
		)

	def write (self, line, expectReply = True, wait = 0):
		d = defer.Deferred()

		if len(line) > self.max_command_length:
			raise ValueError(
				'Command string is too long. Max {:s} characters'.format(
					self.max_command_length
				)
			)

		command = self.Command(
			index = self.index.next(),
			line = line,
			expectReply = expectReply,
			wait = float(wait),
			d = d
		)
		self.queue.append(command)

		return d

	def _advance (self, command: _Command):
		self._current = command
		self._queue_d = defer.Deferred()

		if self.debug:
			log.msg('Send: ' + repr(command.line.encode('ascii') + self.delimiter))

		if self.character_delay > 0:
			self.sendLine(command.line.encode('ascii') + self.delimiter)
		else:
			self.transport.write(command.line.encode('ascii') + self.delimiter)

		if command.expectReply:
			self._timeout = reactor.callLater(
				(len(command.line) * self.character_delay) + self.timeout,
				self._timeoutCurrent
			)

		else:
			# Avoid flooding the network or the device.
			# 30ms is approximately a round-trip time.
			reactor.callLater(command.wait, command.d.callback, None)
			reactor.callLater(max(command.wait, 0.03), self._queue_d.callback, None)

		return self._queue_d

	@defer.inlineCallbacks
	def sendLine (self, line: bytes):
		for character in line:
			self.transport.write(character)
			yield task.deferLater(reactor, self.character_delay, lambda: True)

	def dataReceived (self, data: bytes):
		self._buffer += data

		# something weird to do with the brainboxes?
		if self._buffer[:9] == b'\xff\xfd\x03\xff\xfd\x00\xff\xfd,':
			self._buffer = self._buffer[9:]

		return LineOnlyReceiver.dataReceived(self, b"")

	def lineReceived (self, line: bytes):
		if len(line) == 0:
			return
			
		if self.debug:
			log.msg('Recv: ' + repr(line))

		try:
			self._timeout.cancel()

			command = self._current
			reactor.callLater(command.wait, command.d.callback, self.processLine(line.decode('ascii')))
			reactor.callLater(command.wait, self._queue_d.callback, None)

		except (AttributeError, AlreadyCalled, AlreadyCancelled):
			# Either a late response or an unexpected Message
			if self.debug:
				log.msg('  (Unexpected)')

			return self.unexpectedMessage(line.decode('ascii'))

		finally:
			self._current = None
			self._queue_d = None
			self._timeout = None

	def processLine (self, line: str):
		return line

	def unexpectedMessage (self, line: bytes):
		pass

	def _timeoutCurrent (self):
		try:
			self._log("Timed Out: {!s}".format(self._current.line), logging.ERROR)
			self._current.d.errback(TimeoutError(self._current.line))
			self._queue_d.errback(TimeoutError(self._current.line))

		except AttributeError:
			# There is actually no current command
			pass


class VaryingDelimiterQueuedLineReceiver (QueuedLineReceiver):

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

		if len(line) > self.max_command_length:
			raise ValueError(
				'Command string is too long. Max {:s} characters'.format(
					self.max_command_length
				)
			)

		d = defer.Deferred()
		command = self.Command(
			index = self.index.next(),
			line = line,
			expectReply = expect_reply,
			wait = float(wait),
			length = length,
			lengthFn = lengthFn,
			endDelimiter = end_delimiter,
			endDelimiterLength = len(end_delimiter or ''),
			startDelimiter = start_delimiter,
			startDelimiterLength = len(start_delimiter or ''),
			d = d
		)
		self.queue.append(command)

		return d

	def dataReceived (self, data: bytes):
		current = self._current

		if self.debug:
			log.msg('Data: ' + repr(data))

		if current is None:
			if self.debug:
				log.msg('  (Unexpected)')

			self.unexpectedMessage(data)
			return

		self._buffer += data

		# If there is a start delimiter, discard any data before the delimiter.
		if current.startDelimiter is not None:
			try:
				idx = self._buffer.index(current.startDelimiter)
				if idx > 0:
					if self.debug:
						log.msg('  Discard before start delim:' + repr(self._buffer[:idx]))

					self._buffer = self._buffer[idx:]

			except ValueError:
				# Haven't received a start delimiter yet
				if self.debug:
					log.msg('  Discard before start delim:' + repr(self._buffer))

				self._buffer = ''
				return

		# If the length needs to be calculated, try to do so.
		if current.length is None and current.lengthFn is not None:
			try:
				length = current.lengthFn(self._buffer[current.startDelimiterLength:])

				if length is not None:
					current.length = length

			except ValueError:
				self._buffer = self._buffer[1:]
				return self.dataReceived(b'')

		# If a length was specified, attempt to return this many characters.
		if current.length is not None:
			start = current.startDelimiterLength
			end = current.startDelimiterLength + current.length

			if len(self._buffer) >= end:
				line = self._buffer[start:end]

				# Check that the end delimiter is present in the correct place
				# if not, the start delimiter may have been located too early.
				# Discard the first character in the buffer and start again
				if current.endDelimiter is not None \
				and self._buffer[end:end + current.endDelimiterLength] != current.endDelimiter:
					if self.debug:
						log.msg('  Wrong end delimiter. Discarding first char of: ' + repr(self._buffer))

					self._buffer = self._buffer[1:]

					# In this case the length would need to be calculated again
					if current.lengthFn is not None:
						current.length = None

				# Remove the message from the buffer and return it.
				else:
					self._buffer = self._buffer[end + current.endDelimiterLength:]
					self.lineReceived(line.decode('ascii'))

			elif self.debug:
				log.msg('  Waiting for length ' + repr(current.length))


		# If no length was specified, look for the end delimiter
		elif current.endDelimiter is not None \
		and current.lengthFn is None:
			try:
				# Select data up to the end delimiter
				idx = self._buffer.index(current.endDelimiter)

			except ValueError:
				# Haven't received an end delimiter yet
				if self.debug:
					log.msg('  Waiting for end delimiter: ' + repr(current.endDelimiter))

				return

			line = self._buffer[current.startDelimiterLength:idx]
			self._buffer = self._buffer[idx + current.endDelimiterLength:]

			self.lineReceived(line.decode('ascii'))

		# something weird to do with the brainboxes?
		if self._buffer[:9] == b'\xff\xfd\x03\xff\xfd\x00\xff\xfd,':
			self._buffer = self._buffer[9:]
