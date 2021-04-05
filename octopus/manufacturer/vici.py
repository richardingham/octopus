"""

"""

# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory

# Package Imports
from octopus.machine import Machine, Property, ui
from octopus.protocol.basic import QueuedLineReceiver
from octopus.util import now

__all__ = ["MultiValve"]


class LineReceiver(QueuedLineReceiver):
    timeoutDuration = 4.5
    delimiter = b"\r"


class MultiValve(Machine):

    protocolFactory = Factory.forProtocol(LineReceiver)
    name = "Valco Multiposition Valve"

    def setup(self):

        # Number of positions
        self.num_positions = 0

        def _set_position(pos):
            return self.move(pos)

        # setup variables
        self.position = Property(title="Position", type=int, setter=_set_position)

        self.ui = ui(properties=[self.position])

    _move_commands = {
        "c": "CW",
        "cw": "CW",
        "clockwise": "CW",
        "a": "CC",
        "cc": "CC",
        "counterclockwise": "CC",
        "anticlockwise": "CC",
        "f": "GO",
        "fastest": "GO",
    }

    @defer.inlineCallbacks
    def _getPosition(self):
        result = yield self.protocol.write("CP")
        try:
            defer.returnValue(int(result.split("=")[1]))
        except ValueError:
            return

    @defer.inlineCallbacks
    def move(self, position, direction="f"):
        if direction not in self._move_commands:
            raise "Invalid direction"

        command = self._move_commands[direction]

        # Make sure position is between 1 and NP
        position = ((int(position) - 1) % self.num_positions) + 1

        if position == self.position.value:
            current_position = yield self._getPosition()
            if position == current_position:
                defer.returnValue("OK")

        yield self.protocol.write("%s%d" % (command, position), expectReply=False)
        new_position = yield self._getPosition()

        if new_position is None:
            # If there was an error in the move command, this will have been received
            # by the CP command due to the expectReply = False.
            # Read the current position again
            new_position = yield self._getPosition()

        if new_position != position:
            raise Exception("Move Failed")
        else:
            self.position._push(new_position)
            defer.returnValue("OK")

    def advance(self, positions):
        return self.move(int(self.position) + positions)

    def start(self):
        # Discover the number of positions
        def interpretPositions(result):
            self.num_positions = int(result.split("=")[1])

        # Discover the current positions
        def interpretPosition(result):
            self.position._push(int(result.split("=")[1]))

        return defer.gatherResults(
            [
                self.protocol.write("NP").addCallback(interpretPositions),
                self.protocol.write("CP").addCallback(interpretPosition),
            ]
        )

    def reset(self):
        return defer.gatherResults([self.position.set(1)])
