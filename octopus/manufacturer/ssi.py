# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory

# Package Imports
from ..machine import Machine, Property, Stream, ui
from ..protocol import QueuedLineReceiver
from ..util import now

__all__ = ["Series1"]

class ProtocolFactory (Factory):
    protocol = QueuedLineReceiver

def _psi2bar (psi):
	return round(psi * 0.06895, 2)

HEAD_STANDARD = 0
HEAD_MACRO = 1

class Series1 (Machine):

	protocolFactory = ProtocolFactory()
	name = "Scientific Systems Inc. Series 1+ HPLC Pump"

	def setup (self):
		def set_power (power):
			if power is "on":
				return self.protocol.write("RU")
			else:
				return self.protocol.write("ST")

		def set_target (target):
			if self._pump_head is None:
				return
			
			target = max(target, 0)
				
			if self._pump_head is HEAD_STANDARD:
				target = int(min(target, 9.99) * 100)				
			elif self._pump_head is HEAD_MACRO:
				target = int(min(target, 40) * 10)

			return self.protocol.write("FL%d" % target)
	
		# setup variables
		self.status = Property(title = "Status", type = str)
		self.power = Property(title = "Power", type = str, options = ("on", "off"), setter = set_power)
		self.target = Property(title = "Flow rate target", type = float, unit = "mL/min", setter = set_target)
		self.rate = Stream(title = "Flow rate", type = float, unit = "mL/min")
		self.pressure = Stream(title = "Pressure", type = float, unit = "bar")

		self._pump_head = None
		self._has_pressure = False
		
		self.ui = ui(
			properties = [self.rate]
		)

	def start (self):

		# Check that the version is correct.
		def interpret_version (result):
			print "SSI Pump %s" % result
			#if result != "V3.1":
			#	raise "Incompatible pump version"

		self.protocol.write("ID").addCallback(interpret_version)
	
		# Discover the head size
		def interpret_setup (result):
			result = result.strip("/").split(",")

			try:
				if result[0] is "Er":
					raise Exception ("Error")
				
				self._pump_head = int(result[5])
				self.power._push("on" if int(result[6]) else "off")
				self._has_pressure = not bool(result[7])

			except IndexError:
				raise Exception ("Unknown pump version")

		self.protocol.write("CS").addCallback(interpret_setup)

		# Setup monitor on a tick to update variables
		def interpretFlowrate (result):
			result = result.strip("/").split(",")

			if self._has_pressure:
				self.pressure._push(_psi2bar(float(result[1])))

			self.rate._push(float(result[2]))

		def interpretFault (result):
			result = result.strip("/").split(",")

			if int(result[1]):
				self.status._push("stall")
			elif int(result[2]):
				self.status._push("overpressure")
			elif int(result[3]):
				self.status._push("underpressure")
			else:
				self.status._push("ok")

		def monitor ():
			return defer.gatherResults([
				self.protocol.write("CC").addCallback(interpretStatus)
				self.protocol.write("RF").addCallback(interpretFault)
			])

		self._tick(monitor, 1)

	def stop (self):
		self._stopTicks()

	def reset (self):
		return defer.gatherResults([
			self.protocol.write("RE"),
			self.power.set("off"),
			self.target.set(0)
		])

	def pause (self):
		self._pauseState = self.power.value
		return self.power.set("off")

	def resume (self):
		return self.power.set(self._pauseState)

	def allowKeypad (self, allow):
		if allow:
			return self.protocol.write("KE")
		else:
			return self.protocol.write("KD")			
