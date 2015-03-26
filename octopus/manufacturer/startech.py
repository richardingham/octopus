# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory
from twisted.python import log

# Package Imports
from ..machine import Machine, Stream, Property, ui
from ..util import now
from ..protocol.basic import VaryingDelimiterQueuedLineReceiver

__all__ = ["PowerRemoteControl"]


class PowerRemoteControl (Machine):

	protocolFactory = Factory.forProtocol(VaryingDelimiterQueuedLineReceiver)
	name = "StarTech Power Remote Control AC Switch"

	def setup (self):
		self.bankNumber = 1

		def _setPort (portNumber):
			@defer.inlineCallbacks
			def setPort (value):
				if value == "on":
					cmd = "ON"
				else:
					cmd = "OF"

				result = yield self.protocol.write(
					"{:s} {:d} {:d}".format(cmd, self.bankNumber, portNumber),
					end_delimiter = '\n\n\r>\x08>'
				)

				error_test = result.split('\r\n')[1].strip()[0:6]
				if error_test not in ('Usage: ', 'Bad Com'):

					success_test = result.split('\r\n\x08 ')[1].split()

					if success_test[1] == value\
					and success_test[3] == str(portNumber):
						getattr(self, 'port' + str(portNumber))._push(value)
						defer.returnValue('OK')

				raise Exception('Could not set power {:s} for port {:d}'.format(value, portNumber))

			return setPort

		# setup variables
		self.port1 = Property(title = "Port 1 Power", type = str, options = ("on", "off"), setter = _setPort(1))
		self.port2 = Property(title = "Port 2 Power", type = str, options = ("on", "off"), setter = _setPort(2))
		self.port3 = Property(title = "Port 3 Power", type = str, options = ("on", "off"), setter = _setPort(3))
		self.port4 = Property(title = "Port 4 Power", type = str, options = ("on", "off"), setter = _setPort(4))
		self.port5 = Property(title = "Port 5 Power", type = str, options = ("on", "off"), setter = _setPort(5))
		self.port6 = Property(title = "Port 6 Power", type = str, options = ("on", "off"), setter = _setPort(6))
		self.port7 = Property(title = "Port 7 Power", type = str, options = ("on", "off"), setter = _setPort(7))
		self.port8 = Property(title = "Port 8 Power", type = str, options = ("on", "off"), setter = _setPort(8))

		self.current = Stream(title = "Current", type = float)

		self.ui = ui(
			traces = [],
			properties = [
				self.port1,
				self.port2,
				self.port3,
				self.port4,
				self.port5,
				self.port6,
				self.port7,
				self.port8
			]
		)

	@defer.inlineCallbacks
	def start (self):
		self.protocol.delimiter = '\r'
		self.protocol.end_delimiter = '\x08>'
		self.protocol.character_delay = 0.001

		result = yield self.protocol.write('\r', end_delimiter = '\r\n>')
		if not (result == '' or result.split('\r\n')[-2].strip() != 'Serial Command Mode.....connected'):
			raise Exception('Failed to connect')

		# Remove any timers
		yield self.protocol.write('TQ 1 0')

		def interpret_status (result):
			body = result.split('\r\n\x08 ')[1].split('\n\r')

			for row in body[3:11]:
				row = row.split()
				prop = getattr(self, 'port' + row[0])
				prop._push('on' if row[1] == 'ON' else 'off')

			self.current._push(body[0].split('current: ')[1])

		def monitor ():
			return self.protocol.write("ST 1")\
				.addCallback(interpret_status)\
				.addErrback(log.err)

		yield self.protocol.write("ST 1").addCallback(interpret_status)

		self._tick(monitor, 1)

	def stop (self):
		self._stopTicks()

	def reset (self):
		return self.protocol.write('OF 1 0')
