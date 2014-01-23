# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.internet.interfaces import IAddress

# Zope Imports
from zope.interface import implementer

# Phidget Imports
from Phidgets.PhidgetException import PhidgetErrorCodes, PhidgetException

# System Imports
import time
	
@implementer(IAddress)
class PhidgetAddress (object):
	compareAttributes = ('device_class', 'id')

	def __init__ (self, id):
		self.id = id

	def __repr__ (self):
		return "%s(%s)" % (self.__class__.__name, self.id)


class Phidget (object):
	def __init__ (self, id):
		self.id = id
		self.name = "phidget(%s)" % id

	def connect (self, protocolFactory):
		d = defer.Deferred()
		addr = PhidgetAddress(self.id)
		protocol = protocolFactory.buildProtocol(addr)

		def attach_handler (event):
			# Not clear whether this is necessary, or if the devices are filtered...
			serial = event.device.getSerialNum()
			name = event.device.getDeviceName()
			print("Phidget Device '" + str(name) + "', Serial Number: " + str(serial) + " Connected")

			try:
				if serial == self.id:
					d.callback(protocol)
			except defer.AlreadyCalledError:
				pass

		def detach_handler (event):
			print "Detached"
			
		@defer.inlineCallbacks
		def check_attached ():
				tries = 0
				while tries < 20:
						if protocol.isAttached():
								serial = protocol.getSerialNum()
								name = protocol.getDeviceName()
								print("Phidget Device '" + str(name) + "', Serial Number: " + str(serial) + " Connected")

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

			# if protocol.isAttached():
				# d.callback(protocol)
			# else:			
				# protocol.setOnAttachHandler(attach_handler)
				# protocol.setOnDetachHandler(detach_handler)
		except PhidgetException as e:
			d.errback(e)

		return d

