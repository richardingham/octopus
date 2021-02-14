# System Imports
import asyncio

# Zope Imports
from zope.interface import implementer

# Twisted Imports
from twisted.internet import reactor, defer, serialport
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.interfaces import IAddress
from twisted.python.util import FancyEqMixin

class TCPConnection ():
	def __init__ (self, host: str, port: int):
		self.host = host
		self.port = port
		self.name  = f"tcp({host!s}, {port!s})"
	
	async def connect (self, protocol_factory):
		loop = asyncio.get_running_loop()
		self.transport, self.protocol = await loop.create_connection(
			protocol_factory = protocol_factory,
			host = host,
			port = port
		)



#
# Transports have a connect() function, taking a protocolFactory
# object as the single argument. This should return an IProtocol
# object or equivalent (or a deferred).
#

class tcp (object):
	def __init__ (self, host, port):
		self.point = TCP4ClientEndpoint(reactor, host, port)
		self.name  = "tcp({!s}, {!s})".format(host, port)

	def connect (self, factory):
		return self.point.connect(factory)


@implementer(IAddress)
class SerialAddress (FancyEqMixin, object):
	"""
	Object representing a UNIX socket endpoint.

	@ivar name: The filename associated with this socket.
	@type name: C{str}
	"""

	compareAttributes = ('port', )

	def __init__(self, port):
		self.port = port

	def __repr__(self):
		return 'SerialAddress({!r})'.format(self.port)

	def __hash__(self):
		if self.port is None:
			return hash((self.__class__, None))
		else:
			return hash(self.port)


class serial (object):

	PARITY_NONE = serialport.PARITY_NONE
	PARITY_EVEN = serialport.PARITY_EVEN
	PARITY_ODD = serialport.PARITY_ODD
	STOPBITS_ONE = serialport.STOPBITS_ONE
	STOPBITS_TWO = serialport.STOPBITS_TWO
	FIVEBITS = serialport.FIVEBITS
	SIXBITS = serialport.SIXBITS
	SEVENBITS = serialport.SEVENBITS
	EIGHTBITS = serialport.EIGHTBITS

	_factory = serialport.SerialPort
	_serial = None

	def __init__ (self, port, baudrate = 19200, **args):
		self._args = args
		self.port = port
		self.baudrate = baudrate
		self.name = "serial({!s})".format(port)

	def connect (self, factory):
		addr = SerialAddress(self.port)
		protocol = factory.buildProtocol(addr)

		self._serial = self._factory(protocol, self.port, reactor, self.baudrate, **self._args)

		return protocol
