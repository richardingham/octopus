from twisted.internet import reactor
from twisted.python import log
from octopus.sequence.shortcuts import *
from octopus.sequence.experiment import Experiment

s = wait(2)
e = Experiment(s)
reactor.callLater(0.5, e.pause)
reactor.callLater(1, e.resume)
reactor.callLater(1.5, e.stop)
reactor.callLater(0, e.run)

s1 = wait(2)
e1 = Experiment(s1)
reactor.callLater(2.5, s1.abort)
reactor.callLater(2, e1.run)

s2 = wait(2)
e2 = Experiment(s2)
reactor.callLater(3.5, s2.cancel)
reactor.callLater(3, e2.run)

reactor.callLater(4, reactor.stop)
reactor.run()
