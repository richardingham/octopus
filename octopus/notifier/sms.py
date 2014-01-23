# Twisted Imports
from twisted.internet import reactor, defer
from twisted.web.client import Agent
from twisted.web.http_headers import Headers
from twisted.internet.ssl import ClientContextFactory
from twisted.python import log

# System Imports
from urllib import urlencode

# Sibling Imports
import util as notifier_util

class WebClientContextFactory(ClientContextFactory):
	def getContext(self, hostname, port):
		return ClientContextFactory.getContext(self)

class ClockworkSMS (object):
	def __init__ (self, api_key):
		contextFactory = WebClientContextFactory()
		self.agent = Agent(reactor, contextFactory)
		self._api_key = api_key

	def notify (self, destination, message):

		destinations = destination.split(",")

		if len(destinations) > 50:
			log.msg("Max 50 SMS recipients allowed") 

		params = {
			"key": self._api_key,
			"to": destination,
			"content": message.encode("utf_8", "replace")
		}

		uri = "https://api.clockworksms.com/http/send.aspx?{:s}"

		d = self.agent.request(
			"GET",
			uri.format(urlencode(params)),
			Headers({
				'User-Agent': ['octopus'],
			}),
			None
		)

		def handle_response(response):
			d = defer.Deferred()
			response.deliverBody(notifier_util.SimpleReceiver(d))

			return d

		d.addCallback(handle_response)

		return d
