
class RuntimeProtocol (object):
	def __init__ (self, transport):
		self.transport = transport

	def send (self, topic, payload, context):
		self.transport.send('runtime', topic, payload, context)

	def receive (self, topic, payload, context):
		if topic == 'getruntime': return self.getRuntime(payload, context)
		if topic == 'packet':     return self.receivePacket(payload, context)

	def getRuntime (self, payload, context):
		try:
			name = self.transport.options["type"]
		except KeyError:
			name = "octopus"

		try:
			capabilities = self.transport.options["capabilities"]
		except KeyError:
			capabilities = []

		self.send('runtime', {
			"type": name,
			"version": self.transport.version,
			"capabilities": capabilities
		}, context)

	def receivePacket (self, payload, context):
		self.send('error', Error('Packets not supported yet'), context)

class Error (Exception):
	pass
