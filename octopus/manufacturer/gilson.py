
# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver

# System Imports
from collections import namedtuple

# Package Imports
from ..machine import Machine, Component, Property, Stream, ui
from ..util import now
from ..protocol import basic, gsioc

from gilson_components import layout

#__all__ = ["UVVis151"]

class Error (Exception):
	"Base class for exceptions in this module"
	pass


class GSIOC (Machine):
	protocolFactory = Factory.forProtocol(gsioc.Receiver)
	name = "GSIOC Connection"

	def setup (self):
		def connected (result):
			reactor.callLater(0.5, self._connect_wait.callback, True)
			return result

		# Put in a delay to allow the GSIOC to intialise
		self._connect_wait = defer.Deferred()

		self.ready.addCallback(connected)

	def gsioc (self, id):
		d = defer.Deferred()

		def send_slave (result):
			d.callback(self.protocol.slave(id))

		# Wait until GSIOC has connected
		self._connect_wait.addCallback(send_slave)
		return d


def _iter_ci_FIFO (s):
	for i in xrange(0, len(s), 7):
		yield s[i:i + 6]

def _set_output (machine, i):
	i = str(i)

	def set_output (value):
		if value == "open":
			machine.protocol.buffered_command("D" + i)
		else:
			machine.protocol.buffered_command("C" + i)

	return set_output

class ControlModule506C (Machine):
	protocolFactory = Factory.forProtocol(gsioc.Receiver)
	name = "Gilson 506C Control Module"

	A = 1
	B = 2
	C = 4
	D = 8

	input_map = {
		"@": 0, "A": A, "B": B, "C": A | B, "D": C,
		"E": A | C, "F": B | C, "G": A | B | C, "H": D,
		"I": A | D, "J": B | D, "K": A | B | D, "L": C | D,
		"M": A | C | D, "N": B | C | D, "O": A | B | C | D
	}

	analogue_sample_frequency = 0.1
	analogue_sample_interval = 0.5
	contact_input_sample_interval = 0.5
	contact_output_sample_interval = 0.5

	def setup (self, **kwargs):

		self.analogue1 = gsioc.FIFOStream(channel = 0, title = "Analogue Input A", type = float, unit = "mV", factor = 0.01)
		self.analogue2 = gsioc.FIFOStream(channel = 1, title = "Analogue Input B", type = float, unit = "mV", factor = 0.01)
		self.analogue3 = gsioc.FIFOStream(channel = 2, title = "Analogue Input C", type = float, unit = "mV", factor = 0.01)
		self.analogue4 = gsioc.FIFOStream(channel = 3, title = "Analogue Input D", type = float, unit = "mV", factor = 0.01)

		self.input1 = Property(title = "Contact Input A", type = str)
		self.input2 = Property(title = "Contact Input B", type = str)
		self.input3 = Property(title = "Contact Input C", type = str)
		self.input4 = Property(title = "Contact Input D", type = str)

		self.output1 = Property(title = "Contact Output A", type = str, options = ("open", "closed"), setter = _set_output(self, 1))
		self.output2 = Property(title = "Contact Output B", type = str, options = ("open", "closed"), setter = _set_output(self, 2))
		self.output3 = Property(title = "Contact Output C", type = str, options = ("open", "closed"), setter = _set_output(self, 3))
		self.output4 = Property(title = "Contact Output D", type = str, options = ("open", "closed"), setter = _set_output(self, 4))
		self.output5 = Property(title = "Contact Output E", type = str, options = ("open", "closed"), setter = _set_output(self, 5))
		self.output6 = Property(title = "Contact Output F", type = str, options = ("open", "closed"), setter = _set_output(self, 6))

		self.ui = ui(
			traces = [{
				"title": "Analogue Inputs",
				"unit":  self.analogue1.unit,
				"traces": [self.analogue1, self.analogue2, self.analogue3, self.analogue4],
				"colours": ["#FF1300", "#FFB100", "#1435AD", "#00C322"]
			}],
			properties = [
				self.input1,
				self.input2,
				self.input3,
				self.input4,
				self.output1,
				self.output2,
				self.output3,
				self.output4,
				self.output5,
				self.output6
			]
		)

	def start (self):

		# Reset Analogue Input FIFO buffers
		self.analogue1.reset(self.protocol, self.analogue_sample_frequency)
		self.analogue2.reset(self.protocol, self.analogue_sample_frequency)
		self.analogue3.reset(self.protocol, self.analogue_sample_frequency)
		self.analogue4.reset(self.protocol, self.analogue_sample_frequency)

		def monitorAnalogueInputs ():
			self.analogue1.update(self.protocol)
			self.analogue2.update(self.protocol)
			self.analogue3.update(self.protocol)
			self.analogue4.update(self.protocol)

		self._tick(monitorAnalogueInputs, self.analogue_sample_interval)

		# Reset Contact Event FIFO
		def resetContactInputs ():
			def interpret (result):
				if len(result) != 4:
					return

				self.input1._push("closed" if result[0] == "C" else "open")
				self.input2._push("closed" if result[1] == "C" else "open")
				self.input3._push("closed" if result[2] == "C" else "open")
				self.input4._push("closed" if result[3] == "C" else "open")

			self._last_contact_update = now()
			self.protocol.buffered_command("9")
			self.protocol.immediate_command("*").addCallback(interpret)

		def interpretContactInputs (result):
			if result[0] == "|":
				return # Buffer is empty

			if len(result) % 7 > 0:
				raise Exception("Malformed contact event FIFO: " + str(result))

			for entry in _iter_ci_FIFO(result):
				try:
					state = self.input_map[result[0]]
					time = self._last_contact_update + (int(result[1:6], 16) * 0.01)
				except IndexError, KeyError:
					raise Exception("Malformed contact event FIFO: " + str(result))

				self.input1._push("closed" if state & self.A else "open", time)
				self.input2._push("closed" if state & self.B else "open", time)
				self.input3._push("closed" if state & self.C else "open", time)
				self.input4._push("closed" if state & self.D else "open", time)

		def interpretContactOutputs (result):
			if len(result) != 6:
					return

			self.output1._push("closed" if result[0] == "C" else "open")
			self.output2._push("closed" if result[1] == "C" else "open")
			self.output3._push("closed" if result[2] == "C" else "open")
			self.output4._push("closed" if result[3] == "C" else "open")
			self.output5._push("closed" if result[4] == "C" else "open")
			self.output6._push("closed" if result[5] == "C" else "open")

		def monitorContactInputs ():
			self.protocol.immediate_command("9").addCallback(interpretContactInputs)

		def monitorContactOutputs ():
			self.protocol.immediate_command("?").addCallback(interpretContactOutputs)

		self._tick(resetContactInputs, 45 * 3600) # Event buffer runs out after ~46h
		self._tick(monitorContactInputs, self.contact_input_sample_interval)
		self._tick(monitorContactOutputs, self.contact_output_sample_interval)

	def stop (self):
		self._stopTicks()


class SampleInjector233 (Machine):

	protocolFactory = Factory.forProtocol(basic.QueuedLineReceiver)
	name = "Gilson Sampling Injector"

	_layouts = {}
	_current_position = (0, 0, 0)

	# Positions determined by manual calibration of our device.
	# Testing recommended in case of non-calibrated machine!
	_default_locations = {
		"zero":           (0, 350, 0),
		"inject:1":       (2460, 516, 515),
		"inject:2":       (3866, 516, 515),
		"wash:a:deep":    (140, 400, 750),
		"wash:a:shallow": (70, 400, 400),
		"wash:a:drain":   (0, 400, 350)
	}

	def add_layout (self, name, layout):
		self._layouts[name] = layout

	def remove_layout (self, name):
		if name in self._layouts:
			del self._layouts[name]

	def clear_layouts (self):
		self._layouts = {}

	def setup (self):

		def set_position (location):
			if location in self._default_locations:
				x, y, z = self._default_locations[location]
			elif ":" in location:
				name, pos = location.split(":")

				if name not in self._layouts:
					raise Exception ("Unknown layout: %s" % name)

				x, y, z = self._layouts[name].xyz(pos)
			else:
				raise Exception ("Invalid location: %s" % location)


			# Move to z_up
			self.protocol.buffered_command("z0")
			self.protocol.buffered_command("W")

			# Move to x,y
			self.protocol.buffered_command("x{:d}".format(x))
			self.protocol.buffered_command("y{:d}".format(y))
			self.protocol.buffered_command("W")

			# Move to z_down
			self.protocol.buffered_command("z{:d}".format(z))
			self.protocol.buffered_command("W")

			# Time for both Z movements
			z_time = (self._current_position[2] / 1250. + z / 900.)

			# Time for XY movement
			xy_time = max(
				abs(self._current_position[0] - x) / 2500.,
				abs(self._current_position[1] - y) / 2500.
			)

			# Start checking a bit before anticipated
			# completion time
			expected_time = max(0, z_time + xy_time - 0.5)

			self._current_position = (x, y, z)
			finished = defer.Deferred()

			def check_finished ():
				def cb (result):
					if result[1] == "1":
						finished.errback()
					elif result[0] == "1":
						reactor.callLater(0.1, check)
					elif result[0] == "0":
						self.position._push(location)
						finished.callback("ok")

				def check ():
					self.protocol.immediate_command("S").addCallback(cb)

				check()

			reactor.callLater(expected_time, check_finished)
			return finished

		def set_valve (valve):
			c = "I{:d}" + ("/" if valve == "switching" else "")
			def set_valve (pos):
				return self.protocol.buffered_command(c.format(1 if pos == "inject" else 0));

			return set_valve

		# setup variables
		self.position = Property(title = "Position", type = str, setter = set_position)
		self.injection = Property(title = "Injection Valve", type = str, options = ("load", "inject"), setter = set_valve("injection"))
		self.switching = Property(title = "Switching Valve", type = str, options = ("load", "inject"), setter = set_valve("switching"))
		#self.status = Property(title = "Status", type = str)

		self.ui = ui(
			properties = [
				self.position,
				self.injection,
				self.switching,
				#self.status
			]
		)

	def start (self):
		def get_param (id):
			def request (result):
				return self.protocol.immediate_command("P")

			return self.protocol.buffered_command("P" + str(id)).addCallback(request)

		def interpretState (result):
			if result[1] == "1":
				self.status._push("error")
			elif result[0] == "1":
				self.status._push("busy")
			elif result[0] == "0":
				self.status._push("idle")

		valve_states = ("load", "inject", "running", "error", "missing")
		def interpretValveState (result):
			if result[0] == "0":
				pass
				# print "Injection Valve on Right"

			self.injection._push(valve_states[int(result[1])])
			self.switching._push(valve_states[int(result[2])])

		def monitor1 ():
			#self.protocol.immediate_command("S").addCallback(interpretState)
			self.protocol.immediate_command("P").addCallback(interpretValveState)

		self._tick(monitor1, 0.5)

	def stop (self):
		self._stopTicks()

	def reset (self):
		return defer.gatherResults([
			self.injection.set("load"),
			self.switching.set("load"),
			self.position.set("zero")
		])

class Pump305 (Machine):

	protocolFactory = Factory.forProtocol(basic.QueuedLineReceiver)
	name = "Gilson 305 HPLC Pump"


	def setup (self):
		pass

	def start (self):
		pass

	def reset (self):
		return defer.success()



class InvalidPistonSize (Error):
	"The requested piston size is not in the configured list."

class InitializationFailed (Error):
	"The requested piston failed to initialise."

class InvalidTarget (Error):
	"The requested target volume is not supported."

class ValveMoveFailed (Error):
	"The requested valve movement failed."


_PistonSize = namedtuple('_PistonSize', ["flow_max", "flow_sanitise"])

class _syringe_piston (Component):

	piston_ids = ("L", "R")

	piston_sizes = {
		None:  _PistonSize(  0, lambda x: 0), 
		100:   _PistonSize(  6, lambda x: round(max(0.001, min(x,  6)), 3)), 
		250:   _PistonSize( 15, lambda x: round(max(0.001, min(x, 15)), 3)), 
		500:   _PistonSize( 30, lambda x: round(max(0.001, min(x, 30)), 3)), 
		1000:  _PistonSize( 60, lambda x: round(max(0.01, min(x,  60)), 2)), 
		5000:  _PistonSize(120, lambda x: round(max(0.01, min(x, 120)), 2)), 
		10000: _PistonSize(240, lambda x: round(max(0.02, min(x, 240)), 2)), 
		25000: _PistonSize(240, lambda x: round(max(0.04, min(x, 240)), 2)), 
		39000: _PistonSize(39000, lambda x: int(max(1, min(x, 39000))))
	}

	status_text = {
		"N": "ready",
		"R": "running",
		"O": "error",
		"I": "uninitialized",
		"M": "missing",
		"H": "paused",
		"W": "waiting"
	}

	def __init__ (self, machine, id, size):
		if id not in (0, 1):
			raise Error ("Piston id must be 0 or 1")

		if size not in self.piston_sizes:
			raise InvalidPistonSize(size)

		self._i = id
		self._id = self.piston_ids[id]
		self._size = size
		self._machine = machine
		self._rate = self.piston_sizes[size].flow_max / 4.

		self.title = self._id + " Piston"

		self.status = Property(title = self._id + " Syringe Status", type = str)
		self.target = Property(title = self._id + " Syringe Target Volume", type = float, unit = "uL", setter = self.set_target)
		self.volume = Stream(title = self._id + " Syringe Volume", type = float, unit = "uL")

	def set_target (self, target, timely_start = False):
		"""
		Move to a target volume by aspirating or dispensing
		the appropriate volume.

		@param target: The desired volume of aspirated liquid in uL.
		@param timely_start: Synchronise with other syringe.
		"""

		if self._size is None:
			raise Error ("Syringe " + self._id + " not installed")

		finished = defer.Deferred()
		current_target = self.target.value

		target = min(max(target, 0), self._size)
		movement = target - current_target

		# For 100, 250 uL pistons, the pump expects the volume parameter
		# as a 5-character float. For all others, as a 5-char integer.
		if self._size in (100, 250):
			command = "{:s}{:s}{:05.1f}"
		else:
			command = "{:s}{:s}{:05d}"
			movement = int(movement)

		# Send the command, e.g. "AL00100", followed by a go command, e.g. "BL"
		self._machine.protocol.buffered_command(command.format(
			"D" if movement < 0 else "A",
			self._id, 
			abs(movement)
		))

		if timely_start:
			self._machine.protocol.buffered_command("T{:s}".format(self._id))

		self._machine.protocol.buffered_command("B{:s}".format(self._id))
		self.target._push(target)

		def check_finished (delay):
			def cb (result):
				status = result[6 * self._i]
				
				if status == "N":
					# Movement complete, now idle
					monitor.stop()
					finished.callback(None)
				elif status == "R":
					# Keep checking rapidly if it is still running
					reactor.callLater(0.1, check)
				elif status == "W" or status == "H":
					# Less frequent checks if the syringe is waiting
					reactor.callLater(delay, check)
				else:
					# Error returned
					monitor.stop()
					finished.errback(None)

			def check ():
				self._machine.protocol.immediate_command("M").addCallback(cb)

			check()

		def monitor_movement ():
			def cb (result):
				self.update(result[0 + 6 * self._i : 6 + 6 * self._i])

			return self._machine.protocol.immediate_command("M").addCallback(cb)

		expected_time = max(round((abs(movement) / 1000 / self._rate) * 60, 1) - 0.5, 0)
		reactor.callLater(expected_time, check_finished, expected_time)

		monitor = task.LoopingCall(monitor_movement)
		monitor.start(1, now = True)

		return finished

	def set_rate (self, rate):
		"""
		Set the syringe piston flow rate.
		
		@param rate: The desired flow rate in mL/min
		"""

		if self._size is None:
			raise Error ("Syringe " + self._id + " not installed")

		# Return a flow rate within the allowed bounds
		rate = self.piston_sizes[self._size].flow_sanitise(rate)
		self._rate = rate

		# It seems that the specified flow rate can be only 5 characters long
		if self._size is 39000:
			rate = "{:05d}".format(rate)
		else:
			rate = "{:05.3f}".format(rate)[:5]

		print "set rate: S" + self._id + rate

		return self._machine.protocol.buffered_command(
			"S" + self._id + rate
		)

	def aspirate (self, volume, timely_start = False):
		"""
		Aspirate a volume of solution.
		
		@param volume: The volume to aspirate in uL.
		@param timely_start: Synchronise with other syringe.
		"""

		return self.set_target(self.target.value + volume, timely_start)

	def dispense (self, volume, timely_start = False):
		"""
		Dispense a volume of solution.
		
		@param volume: The volume to dispense in uL.
		@param timely_start: Synchronise with other syringe.
		"""

		return self.set_target(self.target.value - volume, timely_start)

	def initialize (self):
		"Initialise syringe."

		# An error will be returned if the pump doesn't recognise the size
		def cb (result):
			if result[1] == "1":
				raise InitializationFailed
			else:
				self.target._push(0)
				return self._machine.protocol.buffered_command(
					"O{:s}".format(self._id)
				)
				# TODO: monitor / update whilst initializing, return when done...

		def initialisation_failed (failure):
			failure.trap(InitializationFailed)

			print "Syringe Initialisation failed. Trying again"
			return task.deferLater(reactor, 1, self.initialize)

		# Send commands to initialise the syringe
		if self._size is not None:
			self._machine.protocol.buffered_command(
				"P{:s}{:05d}".format(self._id, self._size)
			)

			d = self._machine.protocol.immediate_command("S")
			d.addCallback(cb)
			d.addErrback(initialisation_failed)

			return d
		else:
			return defer.succeed(None)

	def update (self, status):
		self.status._push(self.status_text[status[0]])
		self.volume._push(float(status[1:]))

class SyringePump402 (Machine):

	protocolFactory = Factory.forProtocol(basic.QueuedLineReceiver)
	name = "Gilson Piston Pump 402"

	initialise_on_start = True
	
	valve_positions = {
		"N": "needle",
		"R": "reservoir",
		"X": "moving",
		"O": "error",
		"M": "missing"
	}

	def setup (self, syringe_sizes):
		if all(s is None for s in syringe_sizes):
			raise InvalidPistonSize(syringe_sizes)

		self.piston1 = _syringe_piston(self, 0, syringe_sizes[0])
		self.piston2 = _syringe_piston(self, 1, syringe_sizes[1])

		def _set_valve_position (id):
			command = ("VL", "VR")[id]

			def start_checking (result, position, finished):
				return task.deferLater(
					reactor, 0.5, check_finished, 
					position, finished
				)

			def check_finished (position, finished):
				
				def cb (result):
					status = result[id]

					if status == "N" or status == "R": 
						# Workaround...
						if id is 0:
							self.valve1._push(position)
						elif id is 1:
							self.valve2._push(position)

						finished.callback(None)
					elif status == "X": # Still running
						reactor.callLater(0.1, check)
					else: # Error condition
						finished.errback(ValveMoveFailed())

				def check ():
					self.protocol.immediate_command("V").addCallback(cb)

				check()

			def setter (position):
				finished = defer.Deferred()

				self.protocol.buffered_command(
					command + ("R" if position == "reservoir" else "N")
				).addCallback(
					start_checking, position, finished
				).addErrback(finished.errback)

				return finished

			return setter

		self.valve1 = Property(
			title = "L Valve Position", type = str, 
			options = ("reservoir", "needle"),
			setter = _set_valve_position(0)
		)
		self.valve2 = Property(
			title = "R Valve Position", type = str, 
			options = ("reservoir", "needle"),
			setter = _set_valve_position(1)
		)

		self.ui = ui(
			properties = [
				self.piston1.status,
				self.piston1.volume,
				self.valve1,
				self.piston2.status,
				self.piston2.volume,
				self.valve2
			]
		)

	def start (self):
		if self.initialise_on_start:
			self.piston1.initialize()
			self.piston2.initialize()

		def interpret_status (result):
			self.piston1.update(result[0:6])
			self.piston2.update(result[6:12])

		def interpret_valves (result):
			self.valve1._push(self.valve_positions[result[0]])
			self.valve2._push(self.valve_positions[result[1]])

		self.protocol.immediate_command("M").addCallback(interpret_status)
		self.protocol.immediate_command("V").addCallback(interpret_valves)

	def stop (self):
		pass

	def reset (self):
		return defer.succeed(None)

	def pause (self):
		return self.protocol.buffered_command("HB")

	def resume (self):
		return self.protocol.buffered_command("BB")


def _set_lamp (machine):
	def set_lamp (power):
		return machine.protocol.buffered_command("L%d" % (1 if power == "on" else 0));

	return set_lamp

def _set_wavelength (machine):
	def set_wavelength (wavelength):
		return machine.protocol.buffered_command("P0=%s" % wavelength);

	return set_wavelength

def _set_sensitivity (machine, i):
	def set_sensitivity (AU):
		return machine.protocol.buffered_command("P%s=%s" % (i, AU));

	return set_sensitivity

class UVVis151 (Machine):

	protocolFactory = Factory.forProtocol(basic.QueuedLineReceiver)
	name = "Gilson 151 UV/VIS Spectrometer"

	analogue_sample_frequency = 0.1
	analogue_sample_interval = 0.5

	default_wavelength = 254

	def setup (self):

		# setup variables
		self.power = Property(title = "Lamp Power", type = str, options = ("on", "off"), setter = _set_lamp(self))
		self.wavelength = Property(title = "Wavelength", type = int, min = 170, max = 700, unit = "nm", setter = _set_wavelength(self))
		self.sensitivity1 = Property(title = "Sensitivity 1", type = float, min = 0.001, max = 2., unit = "AUFS", setter = _set_sensitivity(self, 1))
		self.sensitivity2 = Property(title = "Sensitivity 2", type = float, min = 0.001, max = 2., unit = "AUFS", setter = _set_sensitivity(self, 2))

		self.detection1 = gsioc.FIFOStream(channel = 0, title = "Detection at Sensitivity 1", type = float)
		self.detection2 = gsioc.FIFOStream(channel = 1, title = "Detection at Sensitivity 2", type = float)
		self.transmittance = gsioc.FIFOStream(channel = 2, title = "Transmittance", type = float, unit = "%", factor = 0.1)

		self.ui = ui(
			traces = [{
				"title": "Detection",
				"unit":  self.detection1.unit,
				"traces": [self.detection1, self.detection2],
				"colours": ["#000", "#07F"]
			}, {
				"title": "Transmittance",
				"unit":  self.transmittance.unit,
				"traces": [self.transmittance],
				"colours": ["#0c4"]
			}],
		)

	def start (self):
		def get_param (id):
			def request (result):
				return self.protocol.immediate_command("P")

			return self.protocol.buffered_command("P" + str(id)).addCallback(request)

		def interpretLampStatus (result):
			if len(result) == 9:
				self.power._push("on")
			else:
				self.power._push("off")

		def interpretWavelength (result):
			if result[0:1] == "00=":
				self.wavelength._push(int(result[2:]))

		def monitorStatus ():
			pass
			# i = monitors.__iter__()
			#self.protocol.immediate_command("L").addCallback(interpretLampStatus)
			#get_param(0).addCallback(interpretWavelength)

		def monitorData ():
			self.detection1.update(self.protocol)
			self.detection2.update(self.protocol)
			self.transmittance.update(self.protocol)

		def reset ():
			self.detection1.reset(self.protocol, self.analogue_sample_frequency)
			self.detection2.reset(self.protocol, self.analogue_sample_frequency)
			self.transmittance.reset(self.protocol, self.analogue_sample_frequency)

		# Reset the buffers every minute.
		self._tick(reset, 60)
		self._tick(monitorData, self.analogue_sample_interval)

		# Temp: Get wavelength at startup
		get_param(0).addCallback(interpretWavelength)

	def stop (self):
		self._stopTicks()

	def reset (self):
		return defer.gatherResults([
			self.wavelength.set(self.default_wavelength)
		])

	def zero (self):
		return self.protocol.buffered_command("Z")
