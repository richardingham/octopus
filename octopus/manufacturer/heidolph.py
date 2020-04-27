# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory

# Package Imports
from ..util import now
from ..machine import Machine, Component, Stream, Property
from ..protocol.basic import QueuedLineReceiver


#
# Brainboxes Settings for Heidolph Hei-End
# ----------------------------------------
#
# Baud rate 9600 bps
# Data bits 7         Parity       Even
# Stop bits 1         Flow control None
#
# Protocol type   Raw TCP
#


class HeidolphLineReceiver (QueuedLineReceiver):

	delimiter = b"\n\r"

	def sendLine (self, line):
	   """
	   Sends a line to the other end of the connection.

	   @param line: The line to send, not including the delimiter.
	   @type line: C{str}
	   """
	   return self.transport.write(line + b"\n")


class _heater (Component):
	def __init__ (self, set_power, set_temp, set_delta):
		self.power = Property(title = "Hotplate Power", type = str, options = ("on", "off"), setter = set_power)
		self.target = Property(title = "Hotplate Target Temperature", type = int, unit = "C", setter = set_temp)
		self.safetydelta = Property(title = "Hotplate Safety Delta", type = int, unit = "C", setter = set_delta)
		
		self.mediumtemp = Stream(title = "Medium Temperature", type = float, unit = "C")
		self.mediumsafetytemp = Stream(title = "Medium (Safety) Temperature", type = float, unit = "C")
		self.hotplatetemp = Stream(title = "Hotplate Temperature", type = float, unit = "C")
		self.hotplatesafetytemp = Stream(title = "Hotplate (Safety) Temperature", type = float, unit = "C")

class _stirrer (Component):
	def __init__ (self, set_power, set_speed):
		self.power = Property(title = "Stirrer Power", type = str, options = ("on", "off"), setter = set_power)
		self.target = Property(title = "Stirrer Target Speed", type = int, unit = "rpm", setter = set_speed)
		
		self.speed = Stream(title = "Stirrer Speed", type = int, unit = "rpm")

def _set_heater_power (machine):
	def set_power (power):
		machine.heater.power._push(power)

		if power == "on":
			return machine.protocol.write("START_1", expectReply = False)
		else:
			return machine.protocol.write("STOP_1", expectReply = False)

	return set_power

def _set_stirrer_power (machine):
	def set_power (power):
		machine.stirrer.power._push(power)

		if power == "on":
			return machine.protocol.write("START_2", expectReply = False)
		else:
			return machine.protocol.write("STOP_2", expectReply = False)

	return set_power

def _set_heater_target (machine):
	def set_target (target):
		return machine.protocol.write("OUT_SP_1 %d" % target, expectReply = False)

	return set_target

def _set_heater_delta (machine):
	def set_delta (delta):
		return machine.protocol.write("OUT_SP_2 %d" % delta, expectReply = False)

	return set_delta

def _set_stirrer_target (machine):
	def set_target (target):
		return machine.protocol.write("OUT_SP_3 %d" % target, expectReply = False)

	return set_target

class HeiEnd (Machine):

	protocolFactory = Factory.forProtocol(HeidolphLineReceiver)
	name = "Heidolph Hei-End Stirrer Hotplate"

	def setup (self):

		# setup variables
		self.heater = _heater(_set_heater_power(self), _set_heater_target(self), _set_heater_delta(self))
		self.stirrer = _stirrer(_set_stirrer_power(self), _set_stirrer_target(self))

	def start (self):
		# setup monitor on a tick to update variables

		to_monitor = []

		def addMonitor (command, fn, variable):
			def interpret (result):
				variable._push(fn(result), now())
			
			to_monitor.append(( command, interpret ))

		addMonitor("IN_PV_1", lambda x: float(x) if x != 999.9 else 0, self.heater.mediumtemp)
		addMonitor("IN_PV_2", lambda x: float(x) if x != 999.9 else 0, self.heater.mediumsafetytemp)
		addMonitor("IN_PV_3", float, self.heater.hotplatetemp)
		addMonitor("IN_PV_4", float, self.heater.hotplatesafetytemp)
		addMonitor("IN_PV_5", int, self.stirrer.speed)

		addMonitor("IN_SP_1", float, self.heater.target)
		addMonitor("IN_SP_2", float, self.heater.safetydelta)
		addMonitor("IN_SP_3", float, self.stirrer.speed)

		def interpretStatus (result):
			if result == 2:
				self.heater.power._push("off")
				self.stirrer.power._push("off")
			elif result == 0:
				self.heater.power._push("manual")
				self.stirrer.power._push("manual")

		def monitor ():
			for cmd, fn in to_monitor:
				self.protocol.write(cmd).addCallback(fn)

			self.protocol.write("STATUS").addCallback(interpretStatus)

		self._monitor = self._tick(monitor, 1)

	def stop (self):
		if self._monitor:
			self._monitor.stop()

	def reset (self):
		return defer.succeed('OK')



__all__ = ["HeiEnd"]
