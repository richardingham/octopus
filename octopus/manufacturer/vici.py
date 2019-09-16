"""

"""

# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory

# Package Imports
from ..machine import Machine, Property, ui
from ..protocol.basic import QueuedLineReceiver
from ..util import now

__all__ = ["MultiValve"]

class LineReceiver (QueuedLineReceiver):
	timeoutDuration = 4.5
	delimiter = "\r"

class MultiValve (Machine):

	protocolFactory = Factory.forProtocol(LineReceiver)
	name = "Valco Multiposition Valve"

	def setup (self):

		# Number of positions
		self.num_positions = 0

		def _set_position (pos):
			return self.move(pos)

		# setup variables
		self.position = Property(title = "Position", type = int, setter = _set_position)

		self.ui = ui(
			properties = [self.position]
		)

	_move_commands = {
		"c": "CW",
		"cw": "CW",
		"clockwise": "CW",
		"a": "CC",
		"cc": "CC",
		"counterclockwise": "CC",
		"anticlockwise": "CC",
		"f": "GO",
		"fastest": "GO"
	}

	def move (self, position, direction = "f"):
		if direction not in self._move_commands:
			raise "Invalid direction"

		command = self._move_commands[direction]

		# Make sure position is between 1 and NP
		position = ((int(position) - 1) % self.num_positions) + 1

		d = defer.Deferred()

		def interpret (result):
			new_position = int(result.split("=")[1])
			self.position._push(new_position)

			if new_position != position:
				d.errback(Exception("Move Failed"))
			else:
				d.callback("OK")

		self.protocol.write("%s%d" % (command, position), expectReply = False)
		self.protocol.write("CP").addCallback(interpret)

		return d

	def advance (self, positions):
		return self.move(int(self.position) + positions)

	def start (self):
		# Stop people using the panel
		d = self.protocol.write("SD1")

		# Discover the number of positions
		def interpretPositions (result):
			self.num_positions = int(result.split("=")[1])

		# Discover the current positions
		def interpretPosition (result):
			self.position._push(int(result.split("=")[1]))

		return defer.gatherResults([
			d,
			self.protocol.write("NP").addCallback(interpretPositions),
			self.protocol.write("CP").addCallback(interpretPosition)
		])

	def reset (self):
		return defer.gatherResults([
			self.position.set(0)
		])
