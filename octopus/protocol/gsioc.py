# Twisted Imports
from twisted.internet import reactor, task, defer
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.python import log, failure

# System Imports
from collections import deque
from time import time as now
from math import floor
import logging

# Package Imports
from ..machine import Stream
from ..transport.gsioc import Slave

__all__ = [
	"Error", "Busy", "NoDevice", 
	"ChannelOutOfRange",
	"SyntaxError", "BufferedCommandFailed", 
	"InvalidImmediateCommand", 
	"Receiver", "Slave", "FIFOStream"
]

class Error (Exception):
	pass

class Busy (Error):
	pass

class TimedOut (Error):
	pass

class NoDevice (Error):
	pass
	
class ChannelOutOfRange (Error):
	pass

class SyntaxError (Error):
	pass

class BufferedCommandFailed (Error):
	pass

class InvalidImmediateCommand (SyntaxError):
	pass

class FIFONotReset (Error):
	pass


def iterstr (s):
	i = 0
	while len(s) > i:
		yield s[i]
		i += 1


class Receiver (LineReceiver):

	line_mode = 0

	_d = None
	_selected = None

	_busy = False
	_timer = None

	def __init__ (self):
		self._queue = deque()
		self.connection_name = "disconnected"

	def _log (self, msg, level = None):
		log.msg(
			"GSIOC Receiver [%s][%s]: %s" % (
				self.connection_name, 
				self._selected, 
				msg
			), 
			logLevel = level
		)

	def rawDataReceived (self, data):
##		print "<- %s [%s]" % (data, ",".join(str(ord(c)) for c in data))

		try:
			self._timer.cancel()
		except:
			self._log("discarding data: %s" % data, logging.WARN)
			return

		# Assume everything other than the last character is
		# junk data (from timed out responses etc.) The program
		# should deal with ensuing errors
		if len(data) > 1:
			data = data[-1]

		if self._d is not None:
			#self._log("rcv: %s" % data, logging.DEBUG)
			d, self._d = self._d, None
			d.callback(data)
		else:
			self._log("No deferred for packet", logging.WARN)

	def _write (self, string):
##		print "-> %s [%s]" % (string, ",".join(str(ord(c)) for c in string))
		if self._d is not None:
			raise Busy

		self._d = defer.Deferred()

		self.transport.write(string)
		self._timer = reactor.callLater(0.2, self._timeout, string)

		return self._d

	def _timeout (self, string, count = 0):
		# Try again (allow 5 retries after a timeout).
		if count < 5:
			self._log("command timed out, retrying: %s" % string, logging.WARN)
			
			self.transport.write(string)
			self._timer = reactor.callLater(0.5, self._timeout, string, count + 1)

		else:
			self._log("command timed out, max retries: %s" % string, logging.WARN)

			# Move on to the next command
			try:
				d, self._d = self._d, None
				d.errback(failure.Failure(TimedOut()))
			except AttributeError:
				self._log("No deferred for packet", logging.WARN)

	def _advance (self):

		try:
			self._busy = True
			chain_d, fn, id, command = self._queue.popleft()
		except IndexError:
			self._busy = False	
			return

		def next (result):
			reactor.callLater(0, self._advance)
			return result

		def error (failure, try_again = 0):
			if try_again is not 0:
				failure.trap(BufferedCommandFailed)
				d = task.deferLater(reactor, 0.2, fn, id, command)
				d.addCallbacks(next, error, errbackKeywords = { "try_again": try_again - 1 })
				return d

		# Allow two retries of failed buffered commands
		d = fn(id, command)
		d.addCallbacks(next, error, errbackKeywords = { "try_again": 2 })
		d.chainDeferred(chain_d)
		return d

	def slave (self, id):
		def immediate_command (command):
			return self.immediate_command(id, command)

		def buffered_command (command):
			return self.buffered_command(id, command)

		return Slave(
			immediate_command, 
			buffered_command, 
			name = "%s(GSIOC:%s)" % (self.connection_name, id)
		)

	#
	# Disconnect/Connect Sequence
	# ---------------------------
	#
	# This is the sequence used to select a desired slave
	# device:
	#
	# + The master device sends a 255 ASCII (FF hexadecimal)
	#   character to disconnect all slaves from
	#   the GSIOC.
	#
	# + Using one of the two following methods, the
	#   master device ensures that no slaves are active.
	#   See "Termination Conditions"
	#
	#    - Passive (no break) termination: The master
	#      waits for a period of at least 20 milliseconds
	#      to allow all slaves to disconnect.
	#    - Break active: The master receives a "break"
	#      character as soon as a selected slave disconnects.
	#
	# + The master sends the binary name of the desired
	#   slave device. The value of the binary name is
	#   equal to the unit ID plus 128. For example, if a
	#   unit's ID code is 16, its binary name is 10010000.
	#
	# Note: It is important to recognize the difference
	# between a unit ID and binary name. Unit IDs (with
	# ASCII values 0 to 63) are interpreted by the GSIOC
	# as commands rather than IDs. To distinguish unit
	# Ids from commands, the program sets the high bit to
	# create a unit's binary name.
	#
	#
	# Termination Conditions
	# ----------------------
	#
	# The GSIOC can be terminated in one of two ways.
	#
	# + The master usually terminates the master end of
	#   the slave line so that it receives a break character
	#   when no slave device is selected. This method is
	#   called "break active" and is supported by Gilson
	#   software that controls devices along the GSIOC.
	#
	# + If you develop your own software to control
	#   devices along the GSIOC, choose the simpler
	#   "passive" termination. This avoids error conditions
	#   that may occur when some systems detect
	#   a break character. Some old Gilson masters only
	#   support "passive" termination.
	#
	# To reduce noise on long lines or lines that contain
	# many slaves, terminate the slave end of the GSIOC
	# as well.
	#

	def _select (self, id):
		if self._selected == id:
			return defer.succeed(id)

		gsioc_id = id + 128
		d = self._write(chr(gsioc_id))
		#_log("S?  %s [%s]" % (gsioc_id, id))

		def cb (result):
			result = ord(result) if len(result) > 0 else None
			#_log("S.  %s" % result)

			if result != gsioc_id:
				return task.deferLater(reactor, 0.2, self._select, id)

			self._selected = id

			if result is None:
				raise NoDevice(id)

			# flush input
			return id

		return d.addCallback(cb)

	#
	# Immediate Commands
	# ------------------
	#
	# When a master device issues an immediate com-
	# mand to a designated slave, the slave immediately
	# responds to the immediate (high-priority) command.
	#
	# Immediate commands are always in the form of a
	# single character.
	#
	# After a slave device receives an immediate com-
	# mand, it answers the request with the first character
	# of its response. The master checks the ASCII value
	# of the character. If the character's value is less than
	# 128, it responds to the slave with an ACK character
	# (06 hexadecimal). This exchange continues until the
	# slave sends the last character of the response. To
	# indicate that the last character is being sent, the
	# slave adds 128 (80 hexadecimal) to the character's
	# value.
	#
	# In response to an unrecognized immediate com-
	# mand, a slave responds with a pound sign (#), a
	# value of 23 hexadecimal, and adds 128 (80 hexadecimal.)
	#

	def immediate_command (self, id, command):
		if command == "":
			return defer.succeed(None)

		d = defer.Deferred()
		self._queue.append((d, self._run_immediate_command, id, command))

		if self._busy is False:
			self._advance()

		return d
	
	def _run_immediate_command (self, id, command):
		if len(command) > 1:
			raise InvalidImmediateCommand(command)

		#self._log("i>: %s" % command.replace("\r", "\\r").replace("\n", "\\n"), logging.DEBUG)

		def read_char (char, buffer = ""):
			if ord(char) > 128:
				# Converts the last byte into ASCII by subtracting 128
				return buffer + chr(ord(char) - 128)
			else:
				# Acknowledge the previous character
				return self._write('\x06').addCallback(read_char, buffer + char)

		def do_command (result):
			return self._write(command).addCallback(read_char)

		def check (result):
			#self._log("i<: %s" % result.replace("\r", "\\r").replace("\n", "\\n"), logging.DEBUG)

			if result == "#":
				raise InvalidImmediateCommand(command)

			return result

		return self._select(id).addCallback(do_command).addCallback(check)

	#
	# Buffered Commands
	# -----------------
	#
	# A buffered command is defined as a command
	# string of ASCII characters preceded by a line feed
	# (0A hexadecimal) and followed by a carriage return
	# (0D hexadecimal.)
	#
	# After the master device selects a slave device, 
	# it begins the buffered command protocol with a single
	# line feed character.
	#
	# If the slave is ready to accept a buffered command, it
	# echoes the line feed to the master. The master then
	# sends each subsequent character in the ASCII com-
	# mand string. As each character is received by the
	# slave, it is echoed to the master for confirmation.
	# When the master sends a carriage return character,
	# the slave knows that the complete command has
	# been sent.
	#
	# If the slave is busy performing a buffered command
	# when the master begins another buffered command,
	# it responds instead with a # sign (23 hexadecimal).
	# The master can continue to send the line feed char-
	# acter until the slave responds with a line feed char-
	# acter. At that time, the rest of the ASCII command
	# string is sent.
	#

	def buffered_command (self, id, command):
		if command == "":
			return defer.succeed(None)

		d = defer.Deferred()
		self._queue.append((d, self._run_buffered_command, id, command))

		if self._busy is False:
			self._advance()

		return d

	def _run_buffered_command (self, id, command):
		string = iterstr("\n" + command + "\r")
		#self._log("b>: \\n%s\\r" % command, logging.DEBUG)

		def send_char (result, prev_char = None):
			if prev_char is not None:
				if result != prev_char:
					raise BufferedCommandFailed(command)
			else:
				if result == '#':
					# If the response is "#", try again in 20ms.
					# TODO: call any other requests for unbuffered 
					#       commands for other slaves in the meantime?
					d = task.deferLater(reactor, 0.2, self._write, char)
					return d.addCallback(send_char, char)

			try:
				char = string.next()
				# TODO: This may possibly run into call stack overflows...
				# Maybe replace with callLater?
				return self._write(char).addCallback(send_char, char)
			except StopIteration:
				return True

		return self._select(id).addCallback(send_char)


class FIFOStream (Stream):
	def __init__ (self, channel, title, type, unit = None, factor = 1):
		Stream.__init__(self, title, type, unit)

		if not -1 < channel < 9:
			raise ChannelOutOfRange(channel)

		self.channel = str(channel)
		self.factor = factor

	def update (self, protocol):
		def read (result, send_time, buffer = ""):
			if result == "|":
				if len(buffer) > 0:
					try:
						self._update(buffer, now() - send_time)
						return True
					except TypeError, e:
						# Has not been properly reset
						try:
							def cb (result):
								self.update(protocol)

							d = self.reset(protocol, self.sample_interval)
							d.addCallback(cb)
							# TODO: errback to log.
							return d
						except AttributeError:
							# self.sample_interval not set:
							# i.e. self.reset has not been called
							raise FIFONotReset

			else:
				buffer += result
				return protocol.immediate_command(self.channel).addCallback(read, now(), buffer)

		return protocol.immediate_command(self.channel).addCallback(read, now())

	def _update (self, compressed_data, round_trip_time):
		try:
			factor = self.factor
			current_value = self._current_20b_value
			sample_interval = self.sample_interval
			if self._time is not None:
				current_time = self._time
			else:
				current_time = self.time_zero
		except AttributeError:
			raise FIFONotReset

		#self._log(compressed_data)

		try:
			values = _decompress(compressed_data, current_value)
		except TypeError:
			raise

		count = len(values)
		expected_timespan = (now() - current_time - (round_trip_time / 2))

		if not -1 < (expected_timespan / sample_interval) - count < 2:
			sample_interval = (0.75 * (expected_timespan / count)) + (0.25 * self.sample_interval)

		for value in values:
			current_time += sample_interval
			self._push(_20b_to_float(value) * factor, current_time)

		self._current_20b_value = values[-1]

	def reset (self, protocol, sample_interval):
		# Convert sample interval in s to sample rate in 0.01 Hz
		sample_rate = max(min(int(100 / sample_interval), 8000), 1)

		self.time_zero = now()
		self.sample_interval = sample_interval
		self._current_20b_value = None

		return protocol.buffered_command("{:s}{:04d}".format(self.channel, sample_rate))

	def stop (self):
		def _stopped (protocol):
			return defer.succeed(True)

		self.update = _stopped


#
# Data Compression Format
# -----------------------
# 
# The 506C is capable of digitizing analog data. It transfers this data
# to a GSIOC system controller. Because of the large data volumes 
# involved, a data compression technique is used to reduce the data load 
# on the GSIOC. This also helps to conserve storage space. The 
# compression process can be thought of as happening in two steps.
# 
# Raw data is collected which could occupy up to a 32-bit field if 
# stored as a signed integer. The first level of compression involves 
# taking the value of that integer and converting it to a 20-bit 
# floating-point number. This number has the most significant four 
# bits reserved for a binary exponent between 2**7 power and 2**-7 
# power. The lower (the mantissa) representa standard 2's complement 
# integer, between 32768 and -32768. This format is easier to work 
# with than a 32-bit representation, and it eliminates "noise" bits 
# that would interfere with the second level of compression.
# 
# For the second stage of compression, the list of 20-bit floating point 
# numbers is scanned for similarity between neighboring mantissas. 
# Usually there is a fairly high degree of correlation between each 
# number and its successor, unless there is a lot of noise. If the 
# correlation is high, there is a lot of redundancy which can be removed 
# by compression. Since only the lower 16-bits are compared, any change 
# to the exponent field requires that an escape code be sent. This 
# compression scheme uses five different methods as needed to compress 
# the data:
# 
# 1. Runs of identical value.
# 
#    This method is the most obvious, and often the most efficient. 
#    Sixteen codes are used to represent runs from 1 (a single 
#    duplication) to 16 (16 duplications) of the same value. This 
#    works very well on "quiet" data sets with little noise.
#    
# 2. Three values differing by no more than 1 from their predecessor.
# 
#    In this method, each of the three values can be one higher, the 
#    same as, or one lower than the prior value. This means that a 
#    total of 3 x 3 x 3 (or 27) codes must be used to represent these 
#    patterns. This is particularly good at handling noise in the 
#    least significant bit. 
#    
# 3. Single samples with small changes.
# 
#    This method uses a code to send the next value as a change from 
#    the prior value. Thirty seven codes are used to allow changes 
#    from 18 below the prior value to 18 above the prior value to be 
#    sent in one code. This still offers significant compression 
#    even if the data is changing somewhat rapidly.
#    
# 4. Single samples with large changes.
# 
#    In this case, the compression has failed, and the complete 20-bit 
#    value must be sent. One of four different codes is used to signal 
#    the start of this 20-bit transmission, and three more data bytes 
#    follow to complete the value. This code is used at the beginning 
#    of a transfer to set the initial value, and it may be used at 
#    intervals to ensure a known value.
# 
# 5. No value ready. 
# 
#    An additional code is reserved to indicate that no value is 
#    currently available for transmission. This code is sent if 
#    the GSIOC system controller polls an empty device.
# 
# The actual ASCII codes used had to be selected to meet the transmission 
# restrictions imposed by the GSIOC. The codes selected for each of the 
# five cases are listed as follows:
# 
# 1. Codes 36..51
# 
#    The next (code - 35) values = prior value.
#
# 2. Codes 52..78
#
#    1st value = prior value + ((code - 52) div 9) - 1.
#    2nd value = 1st value + (((code - 52) div 3) mod 3) - 1.
#    3rd value = 2nd value + ((code - 52) mod 3) - 1.
# 
# 3. Codes 79..115
# 
#    The value = prior va1ue + (code - 97).
#    
# 4. Codes 116..119 with following three codes.
# 
#    The value = (code - 116) * 262114 +
#                (code2 - 36) * 4096 +
#                (code3 - 36) * 64 +
#                (code4 - 36).
# 
# 5. Code 124
#
#    No new value available. This code would normally be discarded when 
#    data is being stored, so it would not normally be in a data set.
#

def _20b_to_float (value):
	# value is a 20-bit floating-point number

	# Most significant 4 bits are a binary exponent from 6 to -7
	exponent = value >> 16
	# Lower 16 bits are the integer from 32767 to -32768
	mantissa = value - (exponent << 16)

	# Both parts are stored as 2's complement numbers
	m_2c = mantissa - ((mantissa >> 15) << 16)
	e_2c = exponent - ((exponent >> 3) << 4)

	return m_2c * (2 ** e_2c)


def _float_to_20b (value):
	#if not -4194304 < value < 4194176:
	#	raise "RangeError"

	#val_expanded = value * 2**8
	#exponent_expanded = int(min(15, max(0, math.log(val_expanded, 2))))
	#mantissa = int(val_expanded / (2 ** exponent_expanded))
	#return 

	raise NotImplemented

def _add (value, diff):
	# Add / subtract a small difference (< 25 in the decompression algorithm)
	# maintaining 2's complement in the lower 16 bits.

	# See _20b_to_float
	exponent = value >> 16
	mantissa = value - (exponent << 16)

	new_value = mantissa + diff
	if new_value < 0:
		new_value += 65536

	return new_value + (exponent << 16)

def _decompress (compressed_data, current_value = None):
	chars = iterstr(compressed_data)
	values = []

	try:
		while 1:
			code = ord(chars.next())

			if 35 < code < 52:
				values.extend([current_value] * (code - 35))
			elif 51 < code < 79:
				value_1 = _add(current_value, ((code - 52) / 9) - 1)
				value_2 = _add(value_1, (((code - 52) / 3) % 3) - 1)
				current_value = _add(value_2, ((code - 52) % 3) - 1)
				values.extend((value_1, value_2, current_value))
			elif 78 < code < 116:
				current_value = _add(current_value, code - 97)
				values.append(current_value)
			elif 115 < code < 120:
				code2 = ord(chars.next())
				code3 = ord(chars.next())
				code4 = ord(chars.next())
				current_value = \
					((code - 116) * 262114) + \
					((code2 - 36) * 4096) + \
					((code3 - 36) * 64) + \
					((code4 - 36))
				values.append(current_value)
			elif code == 124:
				return

	except TypeError:
		# Called with current_value = None without first having been zeroed.
		raise

	except StopIteration:
		return values

def _encode_single (twenty_bit_number):
	code1 = twenty_bit_number // 262144
	twenty_bit_number -= code1 * 262144

	code2 = twenty_bit_number // 4096
	twenty_bit_number -= code2 * 4096

	code3 = twenty_bit_number // 64
	twenty_bit_number -= code3 * 64

	code4 = twenty_bit_number

	return \
		chr(code1 + 116) + \
		chr(code2 + 36) + \
		chr(code3 + 36) + \
		chr(code4 + 36)

