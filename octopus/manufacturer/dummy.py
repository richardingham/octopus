# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory

# Package Imports
from ..util import now
from ..machine import Machine, Component, Stream, Property
from ..protocol.basic import QueuedLineReceiver as _qlr

__all__ = ["Dummy"]


class QueuedLineReceiver (_qlr):

	delimiter = b"\n\r"
	out_delimiter = b"\n"

	def sendLine (self, line):
	   """
	   Sends a line to the other end of the connection.

	   @param line: The line to send, not including the delimiter.
	   @type line: C{str}
	   """
	   return self.transport.write(line + self.out_delimiter)


class Dummy (Machine):

	protocolFactory = Factory.forProtocol(QueuedLineReceiver)
	name = "Dummy Machine"

	def setup (self):
		pass

	def start (self):
		pass

	def stop (self):
		pass

	def reset (self):
		return defer.succeed('OK')

	def write (self, msg):
		return self.protocol.write(msg)

	def hope (self, msg):
		return self.protocol.write(msg, expectReply = False)
