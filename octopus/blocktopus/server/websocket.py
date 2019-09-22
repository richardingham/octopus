from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from autobahn.websocket.compress import PerMessageDeflateOffer, PerMessageDeflateOfferAccept
from twisted.python import log
from twisted.internet import reactor

import json

from .transport.base import BaseTransport


class WebSocketRuntime (BaseTransport):
	def __init__ (self):
		BaseTransport.__init__(self, options = {
			"capabilities": [
				'protocol:sketch',
				'protocol:block',
				'protocol:experiment',
			]
		})

	def send (self, protocol, topic, payload, context):
		if isinstance(payload, Exception):
			payload = {
				"type": payload.__class__.__name__,
				"message": payload.message
			}

		response = {
			"protocol": protocol,
			"command": topic,
			"payload": payload,
		}

		if topic == "error":
			log.err("Response Error: " + str(payload))
		# log.msg("Response", response)

		context.sendMessage(json.dumps(response).encode('utf-8'))


class OctopusEditorProtocol (WebSocketServerProtocol):
	def onConnect (self, request):
		return 'octopus'

	def onOpen (self):
		self.subscribedExperiments = {}
		self.sendPing()

	def onClose (self, wasClean, code, reason):
		self.factory.runtime.disconnected(self)

	def onMessage (self, payload, isBinary):
		if isBinary:
			raise ValueError("WebSocket message must be UTF-8")

		cmd = json.loads(payload)

		# log.msg("Command", cmd)

		self.factory.runtime.receive(
			cmd['protocol'],
			cmd['command'],
			cmd["payload"],
			self
		)

	def subscribeExperiment (self, experiment):
		self.subscribedExperiments[experiment.id] = {
			"experiment": experiment,
			"streams": [],
			"properties": []
		}

	def chooseExperimentProperties (self, experiment, properties):
		self.subscribedExperiments[experiment.id]['properties'] = properties

	def chooseExperimentStreams (self, experiment, streams):
		self.subscribedExperiments[experiment.id]['streams'] = streams

	def getExperimentProperties (self, experiment):
		try:
			return self.subscribedExperiments[experiment.id]['properties']
		except KeyError:
			return []

	def getExperimentStreams (self, experiment):
		try:
			return self.subscribedExperiments[experiment.id]['streams']
		except KeyError:
			return []
