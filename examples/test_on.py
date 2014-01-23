from octopus.runtime import *
from octopus.sequence.util import Trigger
from twisted.internet import reactor


def fn ():
	print "fn called"
	return sequence(
		log("fn called"),
		set(v, False)
	)

v = variable(False, "v", "v")
v2 = variable(False, "v", "v")

o1 = Trigger(v == True, fn)
o2 = Trigger(v2 == True, log("o2 triggered"), max_calls = 1)

s = sequence(
	log("Loading o"),
	wait("8s"),
	set(v2, True),
	wait("1s")
)

s.dependents.add(o1)
s.dependents.add(o2)

reactor.callLater(2, v.set, True)
reactor.callLater(4, v.set, True)
reactor.callLater(6, v.set, True)

run(s)

