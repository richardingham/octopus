# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory
from twisted.python import log

# Package Imports
from ..machine import Machine, Stream, Property, ui
from ..protocol.basic import VariableDelimiterQueuedLineReceiver


__all__ = ["RegloSingleChannel"]


class RegloSingleChannel (Machine):

	protocolFactory = Factory.forProtocol(VariableDelimiterQueuedLineReceiver)
	name = "Ismatec CP Single-Channel Peristaltic Pump"

	# The setup function is run when the machine is created, and sets up all of
	# the properties and variables that are part of the machine.

	# Tubing diameter should be passed in in mm.
	def setup (self, tubing_diameter):
		self.pumpNumber = 0
		self.tubing_diameter = tubing_diameter

		@defer.inlineCallbacks
		def set_power (power):
			command = 'H' if power is 'on' else 'I'
			result = yield self.transport.write('{:s}{:s}'.format(self.pumpNumber, command), length = 1)

			if result == '*':
				defer.returnValue('OK')

			# Reset overload state
			if result == '#':
				yield self.transport.write('{:s}-'.format(self.pumpNumber), length = 1)
				result = yield self.transport.write('{:s}{:s}'.format(self.pumpNumber, command), length = 1)

			if result == '*':
				defer.returnValue('OK')

			raise Error('Could not switch pump ' + power)

		def set_rate (rate):
			# The pump wants flow rate in mL/min, in 4 characters, zero-padded.
			# May need some error handling here.
			rate = ('0000' + str(rate / 1000))[-4:]
			return self.transport.write('{:s}!{:s}'.format(self.pumpNumber, command), length = 1)

		@defer.inlineCallbacks
		def set_direction (direction):
			command = 'K' if direction is 'anticlockwise' else 'J'
			result = yield self.transport.write('{:s}{:s}'.format(self.pumpNumber, command), length = 1)

			if result == '*':
				self.direction._push(direction)
				defer.returnValue('OK')

			raise Error('Could not set pump direction to ' + direction)

		# setup variables
		self.power = Property(title = "Power", type = str, options = ('on', 'off'), setter = set_power)
		self.rate = Property(title = "Flow rate", type = float, unit = "uL/min", setter = set_rate)
		self.direction = Property(title = "Direction", type = str, options = ('clockwise', 'anticlockwise'), setter = set_direction)

		# no setter function -> read-only.
		self.dispensed = Property(title = "Dispensed Volume", type = float, unit = 'mL')

		self.ui = ui(
			traces = [],
			properties = [self.power, self.rate, self.direction]
		)

	# The start function is called once the serial connection has been established.
	# We must establish that the machine is actually there, and start collecting data.
	@defer.inlineCallbacks
	def start (self):

		# Send parameters with '\r\n' delimiter.
		self.protocol.delimiter = '\r\n'

		# Check pump version
		result = yield self.transport.write('{:s}#'.format(self.pumpNumber, diameter), end_delimiter = '\r\n')
		# expected response is 'REGLO DIGITAL 301 XXX' where XXX is the pump head number.

		if result[0:18] != 'REGLO DIGITAL 301 ':
			raise Error('Unsupported pump type: ' + result)

		def interpret_power (result):
			# The response is either '+' or '-', for on or off.
			if result == '+':
				self.power._push('on')
			elif result == '-':
				self.power._push('off')
			elif result == '#':
				self.power._push('overload')

		def interpret_rate (result):
			# The response is in the format '58.3 ml/min' or '58.5 ul/min' or '600RSV/min' if in revolutions mode.
			# It should not be in revolutions mode, so we will not handle that.

			if result[-7:] == 'RSV/min':
				return

			rate, unit = result.split(' ')

			if unit == 'ml/min':
				rate = float(rate) / 1000
			elif unit == 'ul/min':
				rate = float(rate)
			else:
				raise Error('Unknown rate unit: ' + unit)

			self.rate._push(rate)

		def interpret_dispensed (result):
			# The response is in the format '58.3 ml' or '58.5 ul' or '600RSV/min' if in revolutions mode.
			# It should not be in revolutions mode, so we will not handle that.

			if result[-7:] == 'RSV/min':
				return

			volume, unit = result.split(' ')

			if unit == 'ml':
				volume = float(volume)
			elif unit == 'ul':
				volume = float(volume) * 1000
			else:
				raise Error('Unknown volume unit: ' + unit)

			self.dispensed._push(volume)

		def monitor ():
			# log.err errback prevents any errors from interrupting the updates (they are written to the log instead).
			return defer.gatherResults([
				self.transport.write('{:s}E'.format(self.pumpNumber), length = 1).addCallback(interpret_power).addErrback(log.err),
				self.transport.write('{:s}:'.format(self.pumpNumber), end_delimiter = '\r\n').addCallback(interpret_dispensed).addErrback(log.err),
				self.transport.write('{:s}!'.format(self.pumpNumber), end_delimiter = '\r\n').addCallback(interpret_rate).addErrback(log.err)
			])

			# NB there is unfortunately no (documented) way to read the roller direction.

		# Get first batch of data
		yield monitor()

		# monitor() will run every second.
		self._tick(monitor, 1)

	@defer.inlineCallbacks
	def reset (self):
		# The reset function is called at the start of an experiment, to set the default parameters.

		# Set default values
		result = yield self.transport.write('{:s}0'.format(self.pumpNumber), length = 1)

		if result != '*':
			raise Error('Could not set default values.')

		# Set flow rate mode
		result = yield self.transport.write('{:s}M'.format(self.pumpNumber), length = 1)

		if result != '*':
			raise Error('Could not set flow rate mode.')

		# Set titrated volume to 0
		result = yield self.transport.write('{:s}W'.format(self.pumpNumber), length = 1)

		if result != '*':
			raise Error('Could not zero volume.')

		# Set tubing diameter
		# The machine accepts tubing diameter parameter in 1/100 mm
		diameter = ('0000' + str(int(tubing_diameter * 100)))[-4:]
		result = yield self.transport.write('{:s}+{:s}'.format(self.pumpNumber, diameter), length = 1)

		if result != '*':
			raise Error('Could not set tubing diameter.')

		defer.returnValue("OK")

	# Stop function just stops sending more commands to the machine.
	def stop (self):
		self._stopTicks()

	# We also want pause and resume functions.
	# For a pump this will start and stop the pump.
	def pause (self):
		self._pauseState = self.power.value
		return self.power.set("off")

	def resume (self):
		return self.power.set(self._pauseState)


class Error (Exception):
	pass
