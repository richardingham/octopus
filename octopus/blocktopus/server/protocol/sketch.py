from ...sketch import Sketch

from twisted.internet import reactor

from octopus.constants import State


class SketchProtocol(object):
    def __init__(self, transport):
        self.transport = transport

    def send(self, topic, payload, context):
        self.transport.send("sketch", topic, payload, context)

    def receive(self, topic, payload, sketch, context):
        try:
            if topic == "load":
                return self.loadSketch(payload, context)

            if sketch is None:
                raise Error("[%s:%s] No Sketch specified" % ("sketch", topic))

            if topic == "rename":
                return sketch.renameSketch({"title": payload["title"]}, context)

        except Error as e:
            return self.send("error", e, context)

    def loadSketch(self, payload, context):
        if "sketch" not in payload:
            raise Error("No sketch ID provided")

        id = payload["sketch"]

        def _onEvent(protocol, topic, payload):
            # is id already in the data?
            payload["sketch"] = id
            self.transport.send(protocol, topic, payload, context)

        def _sendData(sketch):
            blockStates = {
                block.id: block.state.name.lower()
                for block in sketch.workspace.allBlocks.values()
                if block.state is not State.READY
            }

            sketchData = {
                "sketch": sketch.id,
                "title": sketch.title,
                "events": sketch.workspace.toEvents(),
                "state": sketch.workspace.state.name.lower(),
                "block-states": blockStates,
            }

            if sketch.experiment is not None:
                sketchData["experiment"] = sketch.experiment.id
                sketchData["log-messages"] = sketch.experiment.logMessages

            self.send("load", sketchData, context)

        try:
            sketch = self.transport.sketches[id]
        except KeyError:
            pass
        else:
            sketch.subscribe(context, _onEvent)
            return _sendData(sketch)

        def _done(data):
            self.transport.sketches[id] = sketch
            sketch.subscribe(context, _onEvent)
            return _sendData(sketch)

        def _error(failure):
            self.send("error", str(failure), context)

        sketch = Sketch(id)

        @sketch.on("closed")
        def onSketchClosed(data):
            # This must be performed later to avoid an exception
            # in sketches.items() in disconnected()
            def _del():
                del self.transport.sketches[id]

            reactor.callLater(0, _del)

        return sketch.load().addCallbacks(_done, _error)


class Error(Exception):
    pass
