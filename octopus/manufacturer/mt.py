# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory

# Package Imports
from ..machine import Machine, Stream, Property, ui
from ..protocol.basic import QueuedLineReceiver

# System Imports
import json, re

__all__ = ["SICSBalance"]

class ProtocolFactory (Factory):
    protocol = QueuedLineReceiver

_SICS_status_text = {
	"+": "overload",
	"-": "underload",
	"I": "busy",
	"S": "ok",
}

def _SICS_interpret_weight (result, self):
	result = result.split()

	if len(result) > 1:
		try:
			status = _SICS_status_text[result[1]]
		except KeyError:
			pass
		else:
			self.status._push(status)

			if status == "ok":
				unit = result[3]

				if unit == "g":
					self.weight._push(float(result[2]))

class SICSBalance (Machine):

	protocolFactory = ProtocolFactory()
	name = "MT Balance (SICS)"

	def setup (self):

		# setup variables
		self.weight = Stream(title = "Weight", type = float, unit = "g")
		self.status = Property(
			title = "Status", 
			type = str, 
			options = ("ok", "busy", "overload", "underload")
		)

		self.ui = ui(
			traces = [],
			properties = [
				self.weight
			]
		)

	def start (self):
		# setup monitor on a tick to update variables

		def monitor_weight ():
			self.protocol.write("SI").addCallback(_SICS_interpret_weight, self)

		self._tick(monitor_weight, 1)

	def stop (self):
		self._stopTicks()

	def getStableWeight (self):
		result = defer.Deferred()

		d = self.protocol.write("S")
		d.addCallback(_SICS_interpret_weight, self)
		d.chainDeferred(result)

		return result

	def tare (self):
		return self.protocol.write("Z", expectReply = False, wait = 5)

class ICIR (Machine):

	protocolFactory = ProtocolFactory()
	name = "MT iC IR Connector"

	def setup (self, stream_names = None):

		streams = []
		self._streams = {}

		# setup variables
		for i in stream_names:
			safe_name = re.sub(r"[^a-zA-Z0-9_]", "", i)
			if not re.match(r"^[a-zA-Z]", safe_name):
				safe_name = "stream_" + safe_name

			stream = Stream(title = i, type = float, unit = "mAU")
			streams.append(stream)
			self._streams[name] = stream

			setattr(self, safe_name, stream)

		self.ui = ui(
			traces = [],
			properties = streams
		)

	def start (self):
		# setup monitor on a tick to update variables

		def interpret_data (result):
			data = json.loads(result)

			if data["time"] is None:
				return

			time = data["time"] / 1000

			for i in range(len(data["streams"])):
				datum = data["streams"][i]
				name = datum["name"]
				value = float(datum["value"]) * 1000

				try:
					self._streams[name]._push(value, time)
				except KeyError:
					try:
						self._streams["stream_%s" % name]._push(time, value)
					except KeyError:
						pass

		def monitor_data ():
			self.protocol.write("requestData").addCallback(interpret_data)

		self._tick(monitor_data, 1)

	def stop (self):
		self._stopTicks()
