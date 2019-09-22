from ...workspace import Workspace, Event, UnknownEventError

class BlockProtocol (object):
	def __init__ (self, transport):
		self.transport = transport

	def send (self, topic, payload, context):
		self.transport.send('block', topic, payload, context)

	def receive (self, topic, payload, sketch, context):
		try:
			if topic == 'transaction':
				for event in payload['events']:
					self.receive(event['event'], event['data'], sketch, context)
				return

			if topic == 'cancel':
				return sketch.runtimeCancelBlock(payload['id'])

			# Block commands
			try:
				event = Event.fromPayload(topic, payload)
				return sketch.processEvent(event, context)

			except UnknownEventError:
				pass

		except Error as e:
			return self.send('error', e, context)


class Error (Exception):
	pass
