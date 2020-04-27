from ..protocol.sketch import SketchProtocol
from ..protocol.experiment import ExperimentProtocol
from ..protocol.block import BlockProtocol
from ..protocol.runtime import RuntimeProtocol

# This is the class all runtime implementations can extend to easily wrap
# into any transport protocol.
class BaseTransport (object):
	def __init__ (self, options = None):
		self.options = options or {}
		self.version = '0.1'
		self.runtimeProtocol = RuntimeProtocol(self)
		self.sketchProtocol = SketchProtocol(self)
		self.experimentProtocol = ExperimentProtocol(self)
		self.blockProtocol = BlockProtocol(self)

		self.sketches = {}

	def send (self, protocol, topic, payload, context):
		"""Send a message back to the user via the transport protocol.
		Each transport implementation should provide their own implementation
		of this method.
		The context is usually the context originally received from the
		transport with the request. For example, a specific socket connection.
		@param [str] Name of the protocol
		@param [str] Topic of the message
		@param [dict] Message payload
		@param [Object] Message context, dependent on the transport
		"""

		raise NotImplementedError

	def receive (self, protocol, topic, payload, context):
		"""Handle incoming message
		This is the entry-point to actual protocol handlers. When receiving
		a message, the runtime should call this to make the requested actions
		happen
		The context is originally received from the transport. For example,
		a specific socket connection. The context will be utilized when
		sending messages back to the requester.
		@param [str] Name of the protocol
		@param [str] Topic of the message
		@param [dict] Message payload
		@param [Object] Message context, dependent on the transport
		"""

		# Find locally stored sketch by ID
		try:
			sketch = self.sketches[payload['sketch']]
		except KeyError:
			sketch = None

		# Block actions
		if protocol == 'block':
			return self.blockProtocol.receive(topic, payload, sketch, context)

		# Experiment actions
		if protocol == 'experiment':
			try:
				if sketch.experiment.id == payload['experiment']:
					experiment = sketch.experiment
				else:
					experiment = None
			except (AttributeError, KeyError):
				experiment = None

			return self.experimentProtocol.receive(topic, payload, sketch, experiment, context)

		# Sketch actions
		if protocol == 'sketch':
			return self.sketchProtocol.receive(topic, payload, sketch, context)

	def disconnected (self, context):
		"""Handle client disconnection
		@param [Object] Message context, dependent on the transport
		"""

		for id, sketch in self.sketches.items():
			sketch.unsubscribe(context)
