from octopus.runtime import *
from octopus.sequence.control import Bind

v = variable(0, "i", "i")
d = variable(False, "b", "b")

d_ctrl = Bind(d, v, lambda x: x > 5)

s = sequence(
	log("Running"),
	loop_while(v < 20, [
		increment(v),
		wait(1),
		log("v = " + v + "; d = " + d)
	]),
	log("Stopping experiment")
)
s.dependents.add(d_ctrl)

run(s)


