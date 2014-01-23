from twisted.internet import reactor

from octopus.runtime import *
from octopus import runtime as r
from octopus.sequence.util import Runnable, Pausable, Cancellable, Dependent


class MyD (Dependent):

	def __init__ (self, i):
		Dependent.__init__(self)
		self.i = i

	def _run (self):
		print "Dep %d Run" % self.i

	def _pause (self):
		print "Dep %d Pause" % self.i

	def _resume (self):
		print "Dep %d Resume" % self.i

	def _cancel (self, abort = False):
		print "Dep %d Cancel" % self.i

	def _reset (self):
		print "Dep %d Reset" % self.i

e = r._experiment
d1 = MyD(1)
d2 = MyD(2)

s = sequence(
	log("Starting experiment"),
	wait("5m"),
	log("Stopping experiment")
)
s.dependents.add(d1)
s.dependents.add(d2)

reactor.callLater(2, e.pause)
reactor.callLater(4, e.resume)
reactor.callLater(6, s[1].delay, 7)
reactor.callLater(7, d2.cancel)
reactor.callLater(8, s[1].cancel)

run(s)


