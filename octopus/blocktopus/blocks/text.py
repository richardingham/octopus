from ..workspace import Block
from twisted.internet import defer


class text(Block):
    def eval(self):
        return defer.succeed(self.getFieldValue("TEXT"))


class text_join(Block):
    def eval(self):
        def concatenate(results):
            return "".join(map(str, results))

        d = []
        i = 0

        while True:
            if "ADD" + str(i) in self.inputs:
                d.append(self.getInputValue("ADD" + str(i)))
                i += 1
            else:
                break

        self._complete = defer.gatherResults(d).addCallback(concatenate)
        return self._complete
