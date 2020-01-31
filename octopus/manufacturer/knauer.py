# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory

# System Imports
from time import time as now

# Package Imports
from ..machine import Machine, Property, Stream, ui
from ..protocol.basic import QueuedLineReceiver

__all__ = ["K120", "S100"]


class K120LineReceiver (QueuedLineReceiver):
	delimiter = b"\r"

	# Knauer pump K120 returns "S" then two bytes (no delimiter)
	# in response to a "S?" query. Induce a lineReceived in this case:
	def dataReceived (self, data):
		r = QueuedLineReceiver.dataReceived(self, data)

		try:
			if r is None \
			and self._current.line == "S?" \
			and len(self._buffer) >= 3:
				line = self._buffer[:3]
				self._buffer = self._buffer[3:]
				self.lineReceived(line)

		except AttributeError:
			pass

		return r

	def unexpectedMessage (self, line):
		if line == "H":
			print ("Pump stopped due to an external stop signal")
		elif line == "R":
			print ("External stop signal removed")
		elif line == "E1":
			print ("Motor blocked error")
		elif line == "E2":
			print ("Manual stop attempt ignored")


class K120 (Machine):
	"""
	Control class for a Knauer WellChrom K120 HPLC pump.

	Serial port settings:
	Baud rate 9600, 8 bit, no parity

	Requires a crossover serial cable.
	"""

	protocolFactory = Factory.forProtocol(K120LineReceiver)
	name = "Knauer K120 HPLC Pump"

	def setup (self):
		def set_power (power):
			return self.protocol.write("M%d" % int(power == "on"))

		def set_target (target):
			d = defer.Deferred()

			def interpret (response):
				if response == "OK":
					d.callback("OK")
				else:
					d.errback(Exception("Flow rate too high: %s" % response))

			self.protocol.write("F%d" % int(target)).addCallback(interpret)

			return d

		# setup variables
		self.status = Property(title = "Status", type = str)
		self.power = Property(title = "Power", type = str, options = ("on", "off"), setter = set_power)
		self.target = Property(title = "Flow rate target", type = int, unit = "uL/min", min = 0, max = 50000, setter = set_target)
		self.rate = Stream(title = "Flow rate", type = int, unit = "uL/min")

		self.ui = ui(
			properties = [self.rate]
		)

	def start (self):

		# Check that the version is correct.
		def interpret_version (result):
			if result not in ["V03.30", "V3.1"]:
				raise Exception("Incompatible pump version: {:s}".format(result))

		d = self.protocol.write("V?").addCallback(interpret_version)

		# setup monitor on a tick to update variables

		def interpretFlowrate (result):
			if result[0] != "F":
				print ("Knauer Error: F? = {:s}".format(result)) 
				return

			target = float(result[1:]) * 1000

			self.target._push(target) # uL/min
			self.rate._push(target if self.power.value == "on" else 0)

		def interpretStatus (result):
			power, error = ord(result[1]), ord(result[2])

			# Two bytes are sent back in binary form.
			#
			# The first is the status byte: 1 = on, 0 = off
			# (allegedly: it turns out to be 48 and 16...)
			#
			# The second is the latest error code:
			# 0 = no error, 1 = motor blocked, 2 = stop via keypad
			# N.B. I have not been able to make the pump send one of
			# these errors so this may not work correctly!

			if power == 48:
				self.power._push("on")
			elif power == 16:
				self.power._push("off")

			if error == 0:
				self.status._push("ok")
			elif error == 1:
				self.status._push("motor-blocked")
			elif error == 2:
				self.status._push("manual-stop")

		def monitor ():
			self.protocol.write("S?").addCallback(interpretStatus)
			self.protocol.write("F?").addCallback(interpretFlowrate)

		self._tick(monitor, 1)

		return d

	def stop (self):
		self._stopTicks()

	def reset (self):
		return defer.gatherResults([
			self.power.set("off"),
			self.target.set(0)
		])

	def pause (self):
		self._pauseState = self.power.value
		return self.power.set("off")

	def resume (self):
		return self.power.set(self._pauseState)

	def allowKeypad (self, allow):
		return self.protocol.write("S%d" % int(not allow))

class S100LineReceiver (QueuedLineReceiver):
	delimiter = "\r"

class S100 (Machine):
	"""
	Control class for a Knauer Smartline S100 HPLC pump.

	Serial port settings:
	Baud rate 9600, 8 bit, no parity

	Requires a crossover serial cable.
	"""

	protocolFactory = Factory.forProtocol(S100LineReceiver)
	name = "Knauer S100 HPLC Pump"

	def setup (self):
	
		def set_power (power):
			cmd = "ON" if power == "on" else "OFF"
			return self.protocol.write(cmd)

		def set_target (target):
			target = int(target)
			return self.protocol.write("FLOW:%d" % target)

		# setup variables
		self.status = Property(title = "Status", type = str)
		self.power = Property(title = "Power", type = str, options = ("on", "off"), setter = set_power)
		self.target = Property(title = "Flow rate target", type = int, unit = "uL/min", min = 0, max = 50000, setter = set_target)
		self.pressure = Stream(title = "Pressure", type = int, unit = "mbar")
		self.rate = Stream(title = "Flow rate", type = int, unit = "uL/min")

		self.ui = ui(
			traces = [{
				"title": "Pressure",
				"unit":  self.pressure.unit,
				"traces": [self.pressure],
				"colours": ["#0c4"]
			}],
			properties = [self.rate]
		)

	def start (self):

		# Check that the version is correct.
		def interpret_version (result):
			result = result[9:].split(",")
			
			try:
				if result[1] != "KNAUER" or result[-2:] != ["1", "03"]:
					raise Exception("Incompatible version: %s" % \
						".".join(result[-2:]))
			except IndexError:
				raise Exception("Incompatible version: %s" % result)

		d = self.protocol.write("IDENTIFY?").addCallback(interpret_version)

		# setup monitor on a tick to update variables

		def interpretStatus (result):
			if result[:7] == "STATUS:":
				status = result[7:].split(",")
				on = int(status[0])

				self.power._push("on" if on else "off")
				self.target._push(float(status[1]))
				self.rate._push(float(status[1]) if on else 0)
				#self.pressure._push(float(status[2])) # 0.1 bar
				#self.pressure._push(float(status[2]) / 10) # bar
				self.pressure._push(float(status[2]) * 100) # mbar

				if int(status[5]):
					self.status._push("overpressure")
				elif int(status[6]):
					self.status._push("underpressure")
				elif int(status[7]):
					self.status._push("overcurrent")
				elif int(status[8]):
					self.status._push("undercurrent")
				elif on:
					self.status._push("running")
				else:
					self.status._push("idle")

		def monitor ():
			self.protocol.write("STATUS?").addCallback(interpretStatus)

		self._tick(monitor, 1)

		return d

	def stop (self):
		self._stopTicks()

	def reset (self):
		return defer.gatherResults([
			self.power.set("off"),
			self.target.set(0)
		])

	def pause (self):
		self._pauseState = self.power.value
		return self.power.set("off")

	def resume (self):
		return self.power.set(self._pauseState)

