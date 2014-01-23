# Twisted Imports
from twisted.internet import reactor, defer, error, protocol
from twisted.python import failure
from twisted.protocols.basic import LineOnlyReceiver

# Package Imports
from ..machine import Machine, Component, Stream, Property
from ..util import ui, now

# Sibling Imports
import dasnet

# System Imports
import logging

class Factory (protocol.Factory):
    protocol = dasnet.SingleControllerReceiver

class SeriesDPump (Machine):

	title = "ISCO Series D Pump"
	protocolFactory = Factory()
	
	def setup (self, unit_id, pumps = 1, mode = "continuous"):

		if mode == "continuous constant pressure":
			if not (pumps == 2 or pumps == 4):
				raise Exception("NEed two or four pumps")

		elif mode == "continuous constant flow":
			if not (pumps == 2 or pumps == 4):
				raise Exception("NEed two or four pumps")
			

		elif mode == "modifier addition":
			raise Exception("Mode not supported")
		elif mode == "continuous modifier addition":
			raise Exception("Mode not supported")
		elif mode == "independent":
			raise Exception("Mode not supported")
		else:
			raise Exception("Mode not supported")

		self._unit_id = unit_id
		self._mode = mode
		self._pumps = pumps


	def start (self):
		self.protocol.unit_id = self._unit_id

		def identify (result):
			pumps = result.split(";")
			if len(pumps) - 1 != self._pumps:
				#error
			
		self.protocol.command("IDENTIFY").addCallback(identify)
