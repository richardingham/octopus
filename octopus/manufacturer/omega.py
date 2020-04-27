# Twisted Imports
from twisted.internet import defer
from twisted.internet.protocol import Factory
from twisted.python import log

# Package Imports
from ..machine import Machine, Stream, ui
from ..util import now
from ..protocol.basic import VaryingDelimiterQueuedLineReceiver

__all__ = ["HH306A"]


# Connection: 9600, 8N1
class HH306A (Machine):

    protocolFactory = Factory.forProtocol(VaryingDelimiterQueuedLineReceiver)
    name = "Omega HH306A Thermometer Data Logger"

    def setup (self):

        # setup variables
        self.temp1 = Stream(title = "Temperature 1", type = float, unit = "C")
        self.temp2 = Stream(title = "Temperature 2", type = float, unit = "C")

        self.ui = ui(
            traces = [],
            properties = [
                self.temp1,
                self.temp2
            ]
        )

    @defer.inlineCallbacks
    def start (self):
        # Set protocol defaults
        self.protocol.send_delimiter = ''
        self.protocol.start_delimiter = '\x02'
        self.protocol.end_delimiter = '\x03'

        # Check that the correct device is connected
        model_no = yield self.protocol.write(
            "K",
            length = 3,
            start_delimiter = '',
            end_delimiter = '\r'
        )

        if model_no != "306":
            raise Exception("HH306A: Expected model '306', received '{:s}'".format(model_no))

        data = yield self.protocol.write("A", length = 8)
        info = [(ord(data[0]) & (1 << i)) > 0 for i in range(8)]

        # Check if in MAX/MIN mode:
        if info[1] or info[2]:
            yield self.protocol.write("N", expect_reply = False)

        # Check if displaying time:
        if info[3]:
            yield self.protocol.write("T", expect_reply = False)

        # Check if in HOLD mode:
        if info[5]:
            yield self.protocol.write("H", expect_reply = False)

        def interpret_data (result):
            byte_2 = ord(result[0])
            byte_3 = ord(result[1])

            showing_time = byte_2 & 8 > 0
            in_f = byte_2 & 128 == 0

            t1_sign = -1 if (byte_3 & 2 > 0) else 1
            t1_factor = 1.0 if (byte_3 & 4 > 0) else 0.1

            t1 = (
                (int(hex(ord(result[2]))[2:].strip('b')) * 100) +
                int(hex(ord(result[3]))[2:].strip('b'))
            ) * t1_factor * t1_sign

            if not showing_time:
                t2_sign = -1 if (byte_3 & 16 > 0) else -1
                t2_factor = 1.0 if (byte_3 & 32 > 0) else 0.1
                t2 = (
                (int(hex(ord(result[6]))[2:].strip('b')) * 100) +
                int(hex(ord(result[7]))[2:].strip('b'))
            ) * t2_factor * t2_sign

                if in_f:
                    t2 = round((t2 - 32.0) * 5.0 / 9.0, 1)

                self.temp2._push(t2)

            if in_f:
                t1 = round((t1 - 32.0) * 5.0 / 9.0, 1)

            self.temp1._push(t1)

        def monitor ():
            return self.protocol.write(
                "A",
                length = 8
            ).addCallback(interpret_data).addErrback(log.err)

        yield monitor()

        self._tick(monitor, 1)

    def stop (self):
        self._stopTicks()
