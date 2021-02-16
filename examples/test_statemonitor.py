from octopus.sequence.runtime import *
from octopus.sequence.control import StateMonitor

v = variable(0, "i", "i")
test = (((v >= 4) & (v <= 6)) | ((v >= 9) & (v <= 14))) == False

d = StateMonitor()
d.add(test)
d.trigger_step = sequence(
    log("Triggered"),
    wait(4),
    log("Still Triggered"),
)
d.reset_step = sequence(log("Reset"), wait(4), log("... not triggered again"))

s = sequence(
    log("Running"),
    loop_while(v < 20, [increment(v), wait(1), log("v = " + v)]),
    log("Stopping experiment"),
)
s.dependents.add(d)

run(s)
