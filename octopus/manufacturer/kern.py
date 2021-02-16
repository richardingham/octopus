# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory

# Package Imports
from ..machine import Machine, Stream, ui
from ..util import now
from ..protocol.basic import QueuedLineReceiver

__all__ = ["PCB"]


class PCB(Machine):

    protocolFactory = Factory.forProtocol(QueuedLineReceiver)
    name = "Kern PCB Balance"

    def setup(self):

        # setup variables
        self.weight = Stream(title="Weight", type=float, unit="g")

        self.ui = ui(traces=[], properties=[self.weight])

    def start(self):
        # setup monitor on a tick to update variables

        def interpret_weight(result):
            if result == "           Error":
                # raise some error
                return

            if result[1] == "-":
                result = -float(result[2:12].strip())
            else:
                result = float(result[1:12].strip())

            self.weight._push(result, now())

        def monitor_weight():
            self.protocol.write("w").addCallback(interpret_weight)

        self._tick(monitor_weight, 1)

    def stop(self):
        self._stopTicks()

    def reset(self):
        return defer.succeed("OK")

    def getStableWeight(self):
        d = defer.Deferred()

        def interpret(result):
            result = result.strip()

            if result == "Error":
                raise Exception("Error fetching stable weight")
            else:
                return result

        self.protocol.write("s").addCallback(interpret).chainDeferred(d)

        return d

    def tare(self):
        return self.protocol.write("t", expectReply=False, wait=5)
