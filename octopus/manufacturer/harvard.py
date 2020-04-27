# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory
from twisted.python import log

# Package Imports
from ..machine import Machine, Stream, Property, ui
from ..util import now
from ..protocol.basic import VaryingDelimiterQueuedLineReceiver

# Python Imports
import re

__all__ = ["PHD2000Infuser"]


_rate_unit_factors = {
	"ul/mn": 1,
	"ml/mn": 1000,
	"ul/hr": 1. / 60,
	"ml/hr": 1000. / 60
}

_status_map = {
	':': 'stopped',
	'>': 'infusing',
	'<': 'refilling',
	'/': 'pause-interval',
	'*': 'interrupted',
	'^': 'trigger-wait'
}

_prompt_re = re.compile('^[0-9]{1,2}[:<>\/\*\^]')

class PHD2000Protocol (VaryingDelimiterQueuedLineReceiver):
	start_delimiter = b'\n'
	delimiter = b'\r'
	character_delay = 0.002

	def length (self, buffer: bytes):
		parts = buffer.decode('ascii').split('\n', 1)
		match = _prompt_re.match(parts[-1])

		if match is None:
			if len(parts) > 1 and len(parts[-1]) > 3:
				raise ValueError
			else:
				return None

		if len(parts) == 1:
			return match.end(0)
		else:
			return len(parts[0]) + 1 + match.end(0)

	def processLine (self, line: str):
		parts = line.split('\n', 1)

		if len(parts) == 1:
			line = ''
			status = parts[0]
		else:
			line = parts[0].strip(' ')
			status = parts[1]

		if line == '?':
			line = 'bad-command-error'
		elif line == 'OOR':
			line = 'out-of-range-error'
		elif line == 'NA':
			line = 'not-applicable-error'

		try:
			status = _status_map[status[-1:]]
		except KeyError:
			status = None

		return line, status


class PHD2000Infuser (Machine):

	protocolFactory = Factory.forProtocol(PHD2000Protocol)
	name = "PHD 2000 Infuser Only Pump"

	# syringe_diameter is in mm.
	def setup (self, syringe_diameter):
		self.pumpNumber = str(0)
		self.syringeDiameter = syringe_diameter
		self._dispensed_accumulator = 0
		self._pump_paused = False

		@defer.inlineCallbacks
		def set_rate (rate):
			if rate < 0.0001:
				rate = 0
				self._pump_paused = True
				yield self.protocol.write(self.pumpNumber + "STP")

			else:
				dispensed, status = yield self.protocol.write(self.pumpNumber + "DEL")

				# Can only RUN if a rate has been set.
				# By sending RUN before RAT, we avoid resetting the dispensed counter.
				if status != "infusing" and self._pump_paused:
					yield self.protocol.write(self.pumpNumber + "RUN")
					self._pump_paused = False

				# Set the rate
				result, status = yield self.protocol.write(
					self.pumpNumber +
					"RAT {:.4f}".format(rate)[:10] + " UM",
				)

				if result == "out-of-range-error":
					raise Error("Requested target volume out of range")

				# Run if not running already
				if status != "infusing":
					yield self.protocol.write(self.pumpNumber + "RUN")
					self._dispensed_accumulator += float(dispensed)


			self.rate._push(rate)
			defer.returnValue("OK")

		@defer.inlineCallbacks
		def set_target (target):
			# Stop the pump
			yield self.protocol.write(self.pumpNumber + "STP")

			yield self.protocol.write(self.pumpNumber + "MOD VOL")

			# Set the property
			result, status = yield self.protocol.write(
				self.pumpNumber +
				"TGT {:.4f}".format(target)[:10]
			)

			if result == "out-of-range-error":
				raise Error("Requested target volume out of range")

			# Only start if the rate > 0
			if self.rate.value > 0:
				yield self.protocol.write(self.pumpNumber + "RUN")

			defer.returnValue("OK")


		# setup variables
		self.status = Property(title = "Status", type = str)
		self.rate = Property(title = "Flow rate", type = float, unit = "uL/min", setter = set_rate)
		self.target_volume = Property(title = "Target Volume", type = float, unit = "mL", setter = set_target)
		self.dispensed = Stream(title = "Volume dispensed", type = float, unit = "mL")

		self.ui = ui(
			traces = [],
			properties = [self.rate, self.dispensed]
		)

	@defer.inlineCallbacks
	def start (self):
		def interpret_rate (result):
			line, status = result

			if status is None:
				return

			self.status._push(status)

			if status == "infusing":
				try:
					unit = _rate_unit_factors[line[7:12]]
				except KeyError:
					raise Error('Invalid unit string: ' + line[7:12])

				self.rate._push(unit * float(line[0:6]))
			else:
				self.rate._push(0)

		def interpret_delivered (result):
			# Units in mL
			self.dispensed._push(float(result[0]) + self._dispensed_accumulator)

		def interpret_target (result):
			# Units in mL
			self.target_volume._push(float(result[0]))

		def monitor ():
			return defer.gatherResults([
				self.protocol.write(self.pumpNumber + "RAT").addCallback(interpret_rate).addErrback(log.err),
				self.protocol.write(self.pumpNumber + "DEL").addCallback(interpret_delivered).addErrback(log.err),
				self.protocol.write(self.pumpNumber + "TGT").addCallback(interpret_target).addErrback(log.err)
			])

		# Check version
		version, status = yield self.protocol.write(self.pumpNumber + "VER")
		if version[0:5] != "PHD1.":
			raise Error("Unsupported PHD pump version: " + version)

		# Set diameter
		yield self.protocol.write(
			self.pumpNumber + "DIA {:.4f}".format(self.syringeDiameter)[:6]
		)

		# Get first batch of data
		yield monitor()

		self._tick(monitor, 1)

	@defer.inlineCallbacks
	def reset (self):
		# Stop Pump
		yield self.protocol.write(self.pumpNumber + "STP")

		# Set pump into pump mode
		yield self.protocol.write(self.pumpNumber + "MOD PMP")

		# Zero rate
		yield self.protocol.write(self.pumpNumber + "RAT 0.0000 UM")

		# Clear delivered volume
		yield self.protocol.write(self.pumpNumber + "CLD")
		self.dispensed._push(0)

		# Set Diameter
		yield self.protocol.write(
			self.pumpNumber + "DIA {:.4f}".format(self.syringeDiameter)[:6]
		)

		defer.returnValue("OK")

	def stop (self):
		self._stopTicks()


class Error (Exception):
	pass
