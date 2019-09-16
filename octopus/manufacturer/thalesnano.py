# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.internet.protocol import Factory
from twisted.python import log

# Package Imports
from ..machine import Machine, Stream, Property, ui
from ..util import now
from ..protocol.basic import QueuedLineReceiver

__all__ = ["HCube"]

class LineReceiver (QueuedLineReceiver):
	delimiter = "\r"

class HCube (Machine):

	protocolFactory = Factory.forProtocol(LineReceiver)
	name = "H-Cube hydrogenation reactor"

	_messages = ["", "OK", "Switch on the pump.", "Switch off the pump.", "Building pressure...", "Building temperature...",
		"Resetting system...", "Stabilizing...", "Stable.", "", "", "", "", "Initializing..", "Close H2 valve..", "Starting HPLC pump..",
		"Waiting for user..", "Change screen..", "Starting controllers..","Building pressures..", "Setting H2 valve..", "Setting H2 valve..",
		"Starting controllers..", "Waiting for temperature..", "", "Resetting system..", "Closing H2 valve..", "Opening system valve..",
		"Opening system valve..", "Resetting system..", "Resetting system..", "", "Initializing..", "Setting valves..", "Setting valves..",
		"", "Initializing..", "Setting valves..", "Exhausting H2..", "Exhausting H2..", "", "Initializing..", "Closing H2 valve..",
		"Opening ws valve..", "Opening ws valve..", "Close WS valve..", "Close WS valve..", ""
	]

	def setup (self):

		# state
		self.state = Property(title = "State", type = str)
		self.message = Property(title = "Info Message", type = str)

		# valves
		#self.system_valve = Property(title = "System Valve Position", type = str)
		#self.hydrogen_valve = Property(title = "Hydrogen Valve Position", type = str)
		#self.water_valve = Property(title = "Water Separator Valve Position", type = str)

		# pressures
		@defer.inlineCallbacks
		def set_system_pressure (target):
			#round to nearest 10
			target = int(10 * round(float(target) / 10))
			result = yield self.protocol.write("PS=%d" % target)

			if result == "?3":
				raise Exception("Unable to set pressure when running")
			else:
				# result is system pressure
				defer.returnValue("OK")

		self.system_pressure_target = Property(title = "Set System Pressure", type = int, unit = "", min = 0, max = 100, setter = set_system_pressure)
		self.system_pressure = Stream(title = "System Pressure", type = int, unit = "")
		self.inlet_pressure = Stream(title = "Inlet Pressure", type = int, unit = "")
		self.hydrogen_pressure = Stream(title = "Hydrogen Pressure", type = int, unit = "")

		# column temperature
		@defer.inlineCallbacks
		def set_column_temperature (temp):
			# round to nearest 5
			temp = int(5 * round(float(temp) / 5))
			result = yield self.protocol.write("TC=%d" % temp)

			if result == "OK":
				defer.returnValue("OK")
			elif result != "?3":
				raise Exception("Unable to set temperature")

			# Can't set the temperature directly when running
			# Have to increment it in stages
			curr_temp = self.column_temperature_target.value

			# lower temperature in increments
			if temp < curr_temp:
				while curr_temp > temp:
					result = yield self.protocol.write("BC=10", wait = 0.5)

					if result != "OK":
						raise Exception("Unable to lower temperature")

					result = yield self.protocol.write("TC1?")
					curr_temp = int(result)

			elif temp > curr_temp:
				while curr_temp < temp:
					result = yield self.protocol.write("BC=09", wait = 0.5)

					if result != "OK":
						raise Exception("Unable to raise temperature")

					result = yield self.protocol.write("TC1?")
					curr_temp = int(result)

			defer.returnValue("OK")

		self.column_temperature_target = Property(title = "Set Column Temperature", type = int, unit = "", min = 0, max = 100, setter = set_column_temperature)
		self.column_temperature = Stream(title = "Column Temperature", type = int, unit = "")

		# hydrogen
		modes = { "controlled": "00", "full": "01", "off": "02" }

		@defer.inlineCallbacks
		def set_hydrogen_mode (mode):
			if mode == "full":
				try:
					yield set_system_pressure(0)
				except Exception:
					raise Exception("Unable to set mode when running")

			try:
				result = yield self.protocol.write("HM=" + modes[mode])
			except KeyError:
				raise Exception("Invalid mode parameter: %s" % mode)

			if result == "OK":
				defer.returnValue("OK")
			elif result == "?3":
				raise Exception("Unable to set mode when running")
			else:
				raise Exception("Unable to set mode")

		self.hydrogen_mode = Property(title = "Hydrogen Mode", type = str, options = ("controlled", "full", "off"), setter = set_hydrogen_mode)

		# Bubble detection
		self.gas_liquid_ratio = Property(title = "Gas / liquid ratio", type = int, unit = "")

		self.ui = ui(
			traces = [{
				"title": "Pressures",
				"unit": self.system_pressure.unit,
				"traces": [self.system_pressure, self.inlet_pressure, self.hydrogen_pressure]
			}],
			properties = [
				self.system_pressure_target, 
				self.column_temperature_target, 
				self.column_temperature, 
				self.hydrogen_mode
			]
		)

	def start (self):
		# setup monitor on a tick to update variables

		states = ["starting", "running", "stopping", "ready", "startup", "shutdown", "checking"]
		hydrogen_modes = ["controlled", "full", "off"]

		def interpret_to_list (sensor, values):
			def interpret (result):
				try:
					sensor._push(values[int(result)])
				except IndexError:
					raise Exception("Unknown response to %s parameter: %s" % (sensor.title, result))

			return interpret

		def interpret_message (result):
			try:
				self.message._push(self._messages[int(result) - 155])
			except IndexError:
				raise Exception("Unknown response to message parameter: %s" % result)

		def interpret_sensor (sensor):
			def interpret (result):
				sensor._push(result)

			return interpret

		commands = {
			# state
			"GP06?": interpret_to_list(self.state, states),
			"GP07?": interpret_message,

			# pressures
			"PS0?": interpret_sensor(self.system_pressure),
			"PS1?": interpret_sensor(self.system_pressure_target),
			"PI?": interpret_sensor(self.inlet_pressure),
			#"PH?": interpret_sensor(self.hydrogen_pressure),

			# temperatures
			"TC0?": interpret_sensor(self.column_temperature),
			"TC1?": interpret_sensor(self.column_temperature_target),

			# hydrogen
			"GL0?": interpret_sensor(self.gas_liquid_ratio),
			"HM?": interpret_to_list(self.hydrogen_mode, hydrogen_modes),
		}

		def monitor_state ():
			for cmd, cb in commands.items():
				self.protocol.write(cmd).addCallbacks(cb, log.err)

		self._tick(monitor_state, 1)

	@defer.inlineCallbacks
	def start_hydrogenation (self):
		result = yield self.protocol.write("BC=00", wait = 0.5)

		if result == "?2":
			state = yield self.protocol.write("GP06?")
			if state == "0":
				pass
			elif state == "1":
				defer.returnValue("OK")
			else:
				raise Exception("Stop hydrogenation command failed")
		elif result != 'OK':
			raise Exception("Start hydrogenation command failed")

		tries = 0
		while True:
			state, code, screen = yield defer.gatherResults([
				self.protocol.write("GP06?"),
				self.protocol.write("GP07?"),
				self.protocol.write("GP08?")
			])

			if state == "1":
				# already running
				break
			elif state == "0" and code == "171" and screen == "14":
				# If start pump window appears, press ok.
				result = yield self.protocol.write("BC=21", wait = 0.5)
				if result == 'OK':
					break
				else:
					raise Exception("Confirm pump started command failed")
			elif tries < 5:
				# wait 0.5s then try again
				tries += 1
				yield task.deferLater(reactor, 0.5, lambda: True)
			else:
				raise Exception("Unable to start hydrogenation")

		# wait for stability
		while True:
			result = yield self.protocol.write("GP07?")

			if 157 <= result <= 162:
				yield task.deferLater(reactor, 5, lambda: True)
			else:
				break

		defer.returnValue("OK")

	def stop_keep_hydrogen (self):
		return self._stop_hydrogenation(True)

	def stop_release_hydrogen (self):
		return self._stop_hydrogenation(False)

	@defer.inlineCallbacks
	def _stop_hydrogenation (self, keep_hydrogen):
		command = "BC=02" if keep_hydrogen else "BC=01"

		result = yield self.protocol.write(command, wait = 0.5)

		if result == '?2':
			state = yield self.protocol.write("GP06?")
			if state in ("0", "1", "5"):
				raise Exception("Stop hydrogenation command failed")
			elif state in ("2", "3"):
				defer.returnValue("OK")
			else:
				pass
		elif result != 'OK':
			raise Exception("Stop hydrogenation command failed")

		while True:
			state = yield self.protocol.write("GP06?")

			if state == "3":
				defer.returnValue("OK")
			elif state == "2":
				yield task.deferLater(reactor, 5, lambda: True)
			else:
				raise Exception("Unable to stop hydrogenation")


	def shutdown (self):
		# only in ready state
		d = defer.Deferred()

		def stop (result):
			if result == "OK":
				reactor.callLater(5, self.stop)
			else:
				defer.errback(Exception("Unable to shut down H-Cube"))

		self.protocol.write("BC=06")\
			.addCallbacks(stop, d.errback)

		return d

	def stop (self):
		self._stopTicks()

	def reset (self):
		return defer.succeed('OK')
