from twisted.internet import reactor

from octopus.runtime import *
from octopus import runtime as r
from octopus.sequence.util import Tick

def fn1 ():
	print "d3 tick."

def fn2 ():
	return log("d4 tick...")

e = r._experiment
d1 = Tick(sequence(
	log("d1 tick...")
), interval = 2)

d2 = Tick(log("d2 tick"), interval = 3)
d3 = Tick(fn1, interval = 1)
d4 = Tick(fn2, interval = 1)

w1 = wait("10s")
w2 = wait("3s")
w3 = wait("3s")
s = sequence(
	log("Starting experiment"),
	w1,
	w2,
	cancel(d1),
	w3,
	log("Stopping experiment")
)
s.dependents.add(d1)
w1.dependents.add(d2)
w2.dependents.add(d3)
w3.dependents.add(d4)

run(s)


