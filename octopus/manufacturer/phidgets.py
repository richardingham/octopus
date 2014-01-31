# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory
from twisted.python import log

# Phidgets Imports
from Phidgets.PhidgetException import PhidgetErrorCodes, PhidgetException
from Phidgets.Devices import TemperatureSensor as ts
from Phidgets.Devices import PHSensor as ph
from Phidgets.Devices import InterfaceKit as ifk

# Package Imports
from ..machine import Machine, Component, ComponentList, Stream, Property, ui

__all__ = ["InterfaceKit", "TemperatureSensor", "PHSensor"]

class InterfaceKit (Machine):

	protocolFactory = Factory.forProtocol(ifk.InterfaceKit)
	name = "Phidgets Interface Kit"

	def setup (self):
		self.ui = ui()

	def start (self):
		self.name = self.protocol.getDeviceName()

	def input (self, id):
		ifk = self

		class Slave (object):
			def state (self):
				try:
					return ifk.protocol.getInputState(id)
				except PhidgetException:
					return None

			def connect (self, protocolFactory):
				return defer.succeed(self)
		
		return Slave()

	def output (self, id):
		ifk = self

		class Slave (object):
			def state (self):
				try:
					return ifk.protocol.getOutputState(id)
				except PhidgetException:
					return None

			def set (self, value):
				try:
					return ifk.protocol.setOutputState(id, bool(value))
				except PhidgetException:
					return None

			def connect (self, protocolFactory):
				return defer.succeed(self)
		
		return Slave()

	def sensor (self, id):
		ifk = self

		class Slave (object):
			def value (self):
				try:
					return ifk.protocol.getSensorValue(id)
				except PhidgetException:
					return None

			def connect (self, protocolFactory):
				return defer.succeed(self)
		
		return Slave()


class ThermocoupleType (object):
	E = ts.ThermocoupleType.PHIDGET_TEMPERATURE_SENSOR_E_TYPE
	J = ts.ThermocoupleType.PHIDGET_TEMPERATURE_SENSOR_J_TYPE
	K = ts.ThermocoupleType.PHIDGET_TEMPERATURE_SENSOR_K_TYPE
	T = ts.ThermocoupleType.PHIDGET_TEMPERATURE_SENSOR_T_TYPE

class TemperatureSensor (Machine):

	types = ThermocoupleType

	protocolFactory = Factory.forProtocol(ts.TemperatureSensor)
	name = "Phidgets Thermocouple Controller"

	def setup (self, inputs):

		self._inputs = inputs
		self.thermocouples = ComponentList()
		self.precision = 1

		class Thermocouple (Component):
			def __init__ (self, index):
				self.title = "Thermocouple %s" % index
				self.temperature = Stream(title = "Temperature %s" % index, type = float, unit = "C")

		# Setup thermocouple inputs.
		for input in self._inputs:
			if input is not None:

				# The position on the sensor, i.e. 0-3 for a
				# four-port thermocouple sensor
				index = input["index"]

				# Minimum temperature change to record
				if "min_change" not in input:
					input["min_change"] = 0.5

				t = Thermocouple(index)

				input["stream"] = t.temperature
				self.thermocouples.append(t)				

		self.ui = ui(
			traces = [{
				"title": "Temperature",
				"unit":  "C",
				"traces": [t.temperature for t in self.thermocouples]
			}],
			properties = [] #[t.temperature for t in self.thermocouples]
		)

	def start (self):
		input_count = self.protocol.getTemperatureInputCount()
		self.name = self.protocol.getDeviceName()

		if input_count < len(self._inputs):
			raise Exception("Connected sensor only has %s inputs" % input_count)

		inputs = {}

		# Initialise the inputs. If an initialisation fails, ignore that input.
		for input in self._inputs:
			try:
				i = input["index"]
				self.protocol.setThermocoupleType(i, input["type"])
				self.protocol.setTemperatureChangeTrigger(i, input["min_change"])
				inputs[i] = input["stream"]

			except (TypeError, PhidgetException):
				log.err()

		# Function to record changes
		def update_value ():
			try:
				for input in self._inputs:
					index = input["index"]
					temp = self.protocol.getTemperature(index)

					if abs(inputs[index].value - temp) > input["min_change"]:
						inputs[index]._push(round(e.temperature, self.precision))

			except (KeyError, AttributeError, PhidgetException):
				pass

		self._tick(update_value, 0.1)

	def stop (self):
		self._stopTicks()


class PHSensor (Machine):

	protocolFactory = Factory.forProtocol(ph.PHSensor)
	name = "Phidgets PH Sensor"

	def setup (self, min_change = 0.5):

		self.precision = 2
		self._min_change = min_change

		def set_temperature (temp):
			try:
				self.protocol.setTemperature(temp)
			except AttributeError:
				pass

			self.temperature._push(temp)

		self.ph = Stream(title = "pH", type = float, unit = "")
		self.temperature = Property(title = "Probe Temperature", type = float, unit = "C", setter = set_temperature)

		self.ui = ui(
			traces = [{
				"title": "pH",
				"unit":  "",
				"traces": [self.ph]
			}],
			properties = [self.temperature]
		)

	def start (self):
		try:
			self.name = self.protocol.getDeviceName()

			def update_value ():
				try:
					value = round(self.protocol.getPH(), self.precision)
				except PhidgetException:
					return

				if self.ph.value is None \
				or abs(value - self.ph.value) > self._min_change:
					self.ph._push(value)

			self._tick(update_value, 0.1)

		except AttributeError:
			self.name = "PH sensor (via interface kit)"

			def update_value ():
				sensor_value = self.protocol.value()

				if sensor_value is None:
					return

				value = 7 - (2.5 - (sensor_value / 200.)) / (0.257179 + 0.000941468 * self.temperature.value)
				value = round(value, self.precision)

				if self.ph.value is None \
				or abs(value - self.ph.value) > self._min_change:
					self.ph._push(value)

			self._tick(update_value, 0.1)

	def stop (self):
		self._stopTicks()

	def reset (self):
		self.temperature.set(20)
		return defer.succeed(None)
