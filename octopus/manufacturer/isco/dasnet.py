# Twisted Imports
from twisted.internet import reactor, defer, error
from twisted.python import failure
from twisted.protocols.basic import LineOnlyReceiver

# System Imports
import logging

# Package Imports
from ..util import AsyncQueue, AsyncQueueRetry

def checksum (s):
	return reduce(lambda a, c: a + ord(c), s, 0)

def dasnet_out_convert (destination_id, message = "", source_id = 0, ack = "R"):
	d_id = int(destination_id) + 0x30
	s_id = int(source_id) + 0x30
	length = len(message)
	
	if ack not in ("R", "E", "B"):
		raise SyntaxError

	if length > 256:
		raise SyntaxError

	if length is 0:
		msg = "{:c}{:s} ".format(d_id, ack)
	else:
		msg = "{:c}{:s}{:c}{:02X}{:s}".format(d_id, ack, s_id, length, message)

	# (checksum + _sum(msg)) % 256 = 0
	msg_checksum = (0x100 - checksum(msg)) & 0x0FF           

	return "{:s}{:2X}".format(msg, msg_checksum)

def dasnet_in_convert (msg):
	msg_checksum = int(msg[-2:], 16)
	msg = msg[:-2]
	if (checksum(msg) + msg_checksum) % 256 > 0:
		# On catching a DasnetSyntaxError, the controller 
		# should ask the slave to resend the message.
		raise SyntaxError 

	ack = msg[0]
	if ack == "B":
		raise Busy # Slaves do not return "E".

	s_id = ord(msg[1]) - 0x30
	if s_id < 0:
		return None # Empty message. ord(" ") - 0x30 == -16

	length = int(msg[2:4], 16)
	msg = msg[4:]

	if len(msg) != length:
		raise SyntaxError

	return s_id, msg
	

class Error(Exception):
	pass

class SyntaxError (Error):
	pass

class Busy (Error):
	pass

class Timeout (Error):
	pass

class SingleControllerReceiver (LineOnlyReceiver):
	delimiter = b'\r'
	MAX_RETRIES = 2

	@property
	def unit_id (self):
		return self._unit_id

	@unit_id.setter
	def unit_id (self, value):
		if self._unit_id is not None:
			raise Error("unit_id has been set")

		if value > 7:
			raise Error("unit_id must be < 7")

		self._unit_id = int(value)
		self._queue.resume()

	def __init__ (self):
		self._unit_id = None
		self._queue = AsyncQueue(self._send, paused = True)
		self._active_deferred = None
		self._active_command = None
		self._active_retries = 0
		self._active_timeout = None

	def _log (self, msg, level = None):
		pass

	def lineReceived (self, line):
		self._active_deferred, d = None, self._active_deferred

		try:
			self._active_timeout.cancel()
		except AttributeError, error.AlreadyCalled, error.AlreadyCancelled:
			self._log("Ignoring response: %s (timed out)" % line, logging.WARN)

		try:
			unit_id, msg = dasnet_in_convert(line)

			if unit_id == self._unit_id:
				try:
					d.callback(msg)
				except AttributeError:
					self._log("Ignoring response: %s (unexpected)" % line, logging.WARN)
			else:
				self._log("Unexpected response from unit id %s" % unit_id, logging.ERROR)

		except SyntaxError:
			# Ask for repeat response
			self._retry(("", "E"))

		except Busy:
			# Try again at the next poll
			reactor.callLater(0.2, self._retry, (self._active_command, "R"))

	def _retry (self, task):
		if self._active_retries < self.MAX_RETRIES:
			self._active_retries += 1

			retry = AsyncQueueRetry(task)
			self._active_deferred.errback(retry)
		else:
			self._active_deferred.errback(Timeout)

	def command (self, command):
		return self._queue.append((command, "R"))
		
	def _send (self, task):
		command, ack = task

		self._active_deferred = defer.Deferred()
		self._active_command = command
		self._active_retries = 0

		formatted = dasnet_out_convert(self._unit_id, command, 0, ack)
		self.sendLine(formatted)

		# If no response is received within 200ms, command is sent again.
		self._active_timeout = reactor.callLater(0.2, self._retry, task)

		return self._active_deferred
