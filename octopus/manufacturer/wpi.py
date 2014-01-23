"""
World Precision Instruments
"""

# Twisted Imports
from twisted.internet import reactor, defer, protocol, error
from twisted.python import log

# Package Imports
from ..machine import Machine, Property, Stream, ui
from ..util import now, AsyncQueue, AsyncQueueRetry

# System Imports
import crc16, struct, logging

__all__ = ["Aladdin"]

def format_command (address, command):
	"""
	Format a command for transmission to Aladdin pump in Safe Mode.

	Result includes the length and checksum but not the 
	start / termination characters (\x02 and \x03).

	@param address: Numeric address of the pump, 0-99, or None.
	@param command: Textual command to send.
	"""

	# Confirm address parameter
	if address > 99:
		raise SyntaxError("Invalid Address: %s" % address)
	if address is not None:
		command = "{:02d}{:s}".format(address, command)

	# Account for the length byte, the two crc bytes
	# and the termination byte
	length = len(command) + 4 

	if length > 255:
		raise SyntaxError("Command too long: %s" % command)

	crc = struct.pack(">H", crc16.crc16xmodem(command))
	return "{:c}{:s}{:s}".format(length, command, crc)


def interpret_response (response, basic = False):
	"""
	Parse response from Aladdin pump.

	Returns a tuple (address, status, message)

	@param response: Message received. Should not include the 
	                 start / termination characters.
	@param basic: Parse in basic mode (no checksum).
	"""

	# Reject empty response
	if len(response) == 0:
		raise SyntaxError

	# Basic mode response in format:
	# <address, 2 chars><status, one char><message>
	if basic:
		address = int(response[0:2])
		status = response[2]
		msg = response[3:]

	# Safe mode response in format:
	# <address, 2 chars><status, one char><message><checksum, 2 chars>
	else:
		msg = response[:-2]
		crc = struct.unpack(">H", response[-2:])[0]

		# Check that the checksum is as expected
		if crc != crc16.crc16xmodem(msg):
			raise SyntaxError(
				"CRC does not match: %s, expected %s." % 
				(crc, crc16.crc16xmodem(msg))
			)

		address = int(msg[0:2])
		status = msg[2]
		msg = msg[3:]

	# Catch alarms
	if status == "A":
		raise Alarm(msg)

	# Catch errors
	if len(msg) > 0 and msg[0] == '?':
		raise CommandError(msg)

	return address, status, msg


class SinglePumpReceiver (protocol.Protocol, object):
	_buffer = b''
	delimiter = b'\x03'
	MAX_LENGTH = 16384
	MAX_RETRIES = 2

	@property
	def unit_id (self):
		return self._unit_id

	@unit_id.setter
	def unit_id (self, value):
		if self._unit_id is not None:
			raise Error("unit_id has been set")

		if value > 99:
			raise Error("unit_id must be < 100")

		self._unit_id = int(value)
		self._queue.resume()

	def __init__ (self):
		self._unit_id = None
		self._queue = AsyncQueue(self._send, paused = True)
		self._active_deferred = None
		self._active_command = None
		self._active_retries = 0
		self._active_timeout = None

		# Single pump: unit_id = 0
		self.unit_id = 0

	def _log (self, msg, level = None):
		log.msg("wpi.SinglePumpReceiver: %s" % (msg), logLevel = level)

	def dataReceived (self, data):
		"""
		Translates bytes into lines, and calls lineReceived.
		"""

		# Add new data to buffer.
		buffer = self._buffer + data

		# Minimum response length: 
		#   Basic mode: \x02AAS\x03
		#   Safe mode:  \x02LAASCC\x03
		while len(buffer) > 4:
			# Discard any junk data before a command
			if buffer[0] != "\x02":
				try:
					buffer = "\x02" + buffer.split("\x02", 1)[1]
				except IndexError:
					buffer = ""

			# Need at least 5 characters for a valid message
			if len(buffer) < 5:
				break

			# Detect basic mode:
			try:
				int(buffer[2:4], 10)
			except ValueError:
				try:
					line, buffer = buffer.split("\x03", 1)
				except ValueError:
					break

				if len(line) - 1 > self.MAX_LENGTH:
					return self.lineLengthExceeded(line)

				self.lineReceived(line[1:], basic = True)
				break

			# Check we've received the whole message
			length = ord(buffer[1])

			if len(buffer) < length + 1:
				break

			# Check that the termination character is present
			if buffer[length] == "\x03":
				line, buffer = buffer[2:length], buffer[length + 1:]
				self.lineReceived(line)
			else:
				# Bad data - discard first character and try again
				# to match a line.
				buffer = buffer[1:]

		self._buffer = buffer
		
		if len(self._buffer) > self.MAX_LENGTH:
			return self.lineLengthExceeded(self._buffer)

	def lineReceived (self, line, basic = False):
		self._active_deferred, d = None, self._active_deferred

		try:
			self._active_timeout.cancel()
		except (AttributeError, error.AlreadyCalled, error.AlreadyCancelled):
			self._log("Unexpected response: %s (timed out?)" % line, logging.WARN)

		try:
			address, status, msg = interpret_response(line, basic)

		except Alarm as a:
			# Emit a warning or error?
			# TODO: Special case for POWER_INTERRUPTED and TIMEOUT (ignore?)
			self._log("Syringe Pump Alarm: %s" % a.type, logging.WARN)

			try:
				self._active_retries = 0
				d.errback(a)
			except AttributeError:
				pass

			# Deal with alarm

		except CommandError as e:
			self._log("Syringe Pump Error: %s" % e.type, logging.WARN)

			try:
				self._active_retries = 0
				d.errback(e)
			except AttributeError:
				pass

		except SyntaxError:
			# Ask for repeat response
			self._log("Syringe Pump Syntax Error: %s" % repr(line), logging.WARN)

			try:
				self._retry(self._active_command, d)
			except AttributeError:
				pass

		else: 
			# Deal with status?

			if address == self._unit_id:
				try:
					self._active_retries = 0
					d.callback((status, msg))
				except AttributeError:
					self._log("Ignoring response: %s (unexpected)" % line, logging.WARN)
			else:
				self._log("Unexpected response from unit id %s" % address, logging.ERROR)

	def _retry (self, task, d):
		if self._active_retries < self.MAX_RETRIES:
			self._active_retries += 1

			d.errback(AsyncQueueRetry())
		else:
			self._active_retries = 0
			d.errback(Timeout())

	def command (self, command):
		return self._queue.append(command)

	def _send (self, task):
		command = task

		self._active_deferred = defer.Deferred()
		self._active_command = command

		formatted = format_command(self._unit_id, command)
		self.transport.writeSequence(("\x02", formatted, self.delimiter))

		# If no response is received within 200ms, command is sent again.
		self._active_timeout = reactor.callLater(0.2, self._retry, task, self._active_deferred)

		return self._active_deferred

	def lineLengthExceeded(self, line):
		"""
		Called when the maximum line length has been reached.
		Override if it needs to be dealt with in some special way.
		"""
		return error.ConnectionLost('Line length exceeded')

class Error (Exception):
	pass

class SyntaxError (Error):
	pass

class Alarm (Error):
	def __init__ (self, type_char):
		self.type_char = type_char

		if type_char == "?R":
			self.type = Alarm.POWER_INTERRUPTED
		elif type_char == "?S":
			self.type = Alarm.MOTOR_STALLED
		elif type_char == "?T":
			self.type = Alarm.TIMEOUT
		elif type_char == "?E":
			self.type = Alarm.PROGRAM_ERROR
		elif type_char == "?O":
			self.type = Alarm.PHASE_OUT_OF_RANGE

		Error.__init__(self, self.type)

Alarm.POWER_INTERRUPTED = "Power interrupted"
Alarm.MOTOR_STALLED = "Motor stalled"
Alarm.TIMEOUT = "Safe mode communication timed out"
Alarm.PROGRAM_ERROR = "Pumping program error"
Alarm.PHASE_OUT_OF_RANGE = "Pumping program phase out of range"

class CommandError (Error):
	def __init__ (self, msg):
		self.msg = msg

		if msg == "?":
			self.type = CommandError.NOT_RECOGNISED
		elif msg == "?NA":
			self.type = CommandError.NOT_APPLICABLE
		elif msg == "?OOR":
			self.type = CommandError.OUT_OF_RANGE
		elif msg == "?COM":
			self.type = CommandError.INVALID_PACKET
		elif msg == "?O":
			self.type = CommandError.IGNORED

		Error.__init__(self, self.type)

CommandError.NOT_RECOGNISED = "Command not recognised"
CommandError.NOT_APPLICABLE = "Command not currently applicable"
CommandError.OUT_OF_RANGE = "Command data out of range"
CommandError.INVALID_PACKET = "Invalid command packet"
CommandError.IGNORED = "Command ignored (simultaneous phase start)"

class Timeout (Error):
	pass

_aladdin_status = {
	"I": "infusing",
	"W": "withdrawing",
	"S": "program-stopped",
	"P": "program-paused",
	"T": "pause-phase",
	"U": "trigger-wait",
	"A": "alarm"
}

_vol_unit_factors = {
	"ML": 1,
	"UL": 0.001
}

_rate_unit_factors = {
	"UM": 1,
	"MM": 1000,
	"UH": 1. / 60,
	"MH": 1000. / 60
}


class Aladdin (Machine):

	protocolFactory = protocol.Factory.forProtocol(SinglePumpReceiver)
	name = "World Precision Instruments Aladdin Syringe Pump"

	def setup (self, syringe_diameter):

		@defer.inlineCallbacks
		def set_rate (rate):
			# Get the current rate
			try:
				state, result = yield self.protocol.command("RAT")
			except CommandError as e:
				raise

			# Cannot set rate if the pump is running - stop the pump.
			if state in ("I", "W", "A"):
				try:
					yield self.protocol.command("STP")
				except CommandError as e:
					if e.type is not CommandError.NOT_APPLICABLE:
						pass

			# Set the rate
			yield self.protocol.command(
				"RAT{:.3f}".format(rate / _rate_unit_factors[self._rate_unit])[:8]
				+ self._rate_unit
			)

			# Only start if the rate > 0
			if rate > 0:
				state, result = yield self.protocol.command("RUN")

				if state in ("I", "W"):
					defer.returnValue("OK")
				else:
					raise Error("Could not start pump")
			else:
				defer.returnValue("OK")

		def set_direction (direction):
			direction = "WDR" if direction == "withdraw" else "INF"
			return self.protocol.command("DIR" + direction)

		# setup variables
		self.status = Property(title = "Status", type = str)
		self.rate = Property(title = "Flow rate", type = float, unit = "uL/min", setter = set_rate)
		self.direction = Property(title = "Direction", type = str, options = ("infuse", "withdraw"), setter = set_direction)
		self.dispensed = Stream(title = "Volume dispensed", type = float, unit = "mL")
		self.withdrawn = Stream(title = "Volume withdrawn", type = float, unit = "mL")

		self._syringe_diameter = syringe_diameter
		self._vol_unit = "UL"
		self._rate_unit = "MM"

		self.ui = ui(
			properties = [self.rate]
		)

	def start (self):
	
		self.protocol.command("SAF50").addErrback(log.err)
		self.protocol.command("VER").addErrback(log.err)
		self.protocol.command("DIA{:.3f}".format(self._syringe_diameter)[:8]).addErrback(log.err)

		## To set:
		# SAF50
		# VER = version
		# DIA = syringe diameter (only not during program)

		## To call
		# VOL = volume to be dispensed (only not during program)
		# CLD = clear dispensed volume (only not during program)

		## To monitor:
		# DIR = pumping direction (INF/WDR/REV)
		# DIS = volume dispensed
		# RAT = pumping rate (stored if not during program)

		## Phase Programming... todo?
		# RUN = run pumping program
		# STP = stop pumping program
		# LOC = keyboard lockout (only during program)
		# ...

		# Setup monitor on a tick to update variables
		def interpretDispensed (result):
			if result is None:
				return

			status, result = result

			self.status._push(_aladdin_status[status])

			vol_unit = result[12:14]
			unit = _vol_unit_factors[vol_unit]

			self._vol_unit = vol_unit
			self.dispensed._push(unit * float(result[1:6]))
			self.withdrawn._push(unit * float(result[7:12]))

		def interpretRate (result):
			if result is None:
				return

			status, result = result

			rate_unit = result[5:7]
			unit = _rate_unit_factors[rate_unit]

			self._rate_unit = rate_unit
			self.rate._push(unit * float(result[0:5]))

		def interpretDirection (result):
			if result is None:
				return

			self.direction._push("infuse" if result[1] == "INF" else "withdraw")

		def monitor ():
			return defer.gatherResults([
				self.protocol.command("DIS").addCallback(interpretDispensed).addErrback(log.err),
				self.protocol.command("RAT").addCallback(interpretRate).addErrback(log.err),
				self.protocol.command("DIR").addCallback(interpretDirection).addErrback(log.err)
			])

		self._tick(monitor, 1)

	def stop (self):
		# Disable safe mode to prevent timeout error.
		self._stopTicks()
		self.protocol.command("SAF0")

	def reset (self):
		# Setup a single program phase with unlimited volume
		# Default to stopped (0 rate) and infuse direction.
		return defer.gatherResults([
			self.protocol.command("PHN01"),
			self.protocol.command("FUNRAT"),
			self.protocol.command("VOL0"),
			self.protocol.command("RAT0"),
			self.protocol.command("DIRINF")
		])

	def pause (self):
		self._pauseState = self.rate.value
		return self.rate.set(0)

	def resume (self):
		try:
			return self.rate.set(self._pauseState)
		except AttributeError:
			return defer.succeed()
