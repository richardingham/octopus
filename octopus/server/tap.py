# labspiral/tap.py
from twisted.application import internet, service
from twisted.internet import interfaces
from twisted.python import usage
import server

class Options (usage.Options):
	optParameters = [
		['wampport', None, 9000, "Listening port for WAMP websockets"],
		['pbport', None, 8789, "Listening port for Perspective Broker"],
		['port', None, 8001, "Listening port for web connections"],
		['scripts', None, None, "Pre-programmed scripts to list"]
	]

	optFlags = [['ssl', 's']]

def makeService(config):
    return server.makeService(config)
