# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.internet.interfaces import IAddress
from twisted.python import log

# Zope Imports
from zope.interface import implementer

# Phidget Imports
from Phidgets.PhidgetException import PhidgetErrorCodes, PhidgetException

# System Imports
import time
import logging

# Compatibility Imports
from __future__ import print_function


@implementer(IAddress)
class PhidgetAddress (object):
	compareAttributes = ('device_class', 'id')

	def __init__ (self, id):
		self.id = id

	def __repr__ (self):
		return "{!s}({!s})".format(self.__class__.__name__, self.id)


class PhidgetTransport (object):
	def __init__ (self, protocol):
		self.protocol = protocol

	def loseConnection (self):
		try:
			self.protocol.closePhidget()
		except (AttributeError, PhidgetException):
			pass


class Phidget (object):
	def __init__ (self, id):
		self.id = id
		self.name = "phidget({!s})".format(id)

	def connect (self, protocolFactory):
		d = defer.Deferred()
		addr = PhidgetAddress(self.id)
		protocol = protocolFactory.buildProtocol(addr)
		protocol.transport = PhidgetTransport(protocol)

		@defer.inlineCallbacks
		def check_attached ():
			tries = 0

			while tries < 20:
				if protocol.isAttached():
					serial = protocol.getSerialNum()
					name = protocol.getDeviceName()

					log.msg(
						"Phidget Device '{!s}', Serial Number: {!s} connected".format(
						name, serial
					), logging.INFO)

					defer.returnValue(protocol)
				else:
					tries += 1
					yield task.deferLater(reactor, 0.5, lambda: True)

			raise Exception("Attachment to phidget timed out")

		try:
			protocol.openPhidget(self.id)

			# Blocks to allow time for phidget to initialise
			time.sleep(0.00125)

			check_attached().addCallbacks(d.callback, d.errback)
		except PhidgetException as e:
			d.errback(e)

		return d
