from octopus.sequence.runtime import *

v = variable(0, "v", "v")

s = sequence(
    loop_while(v < 5, sequence(log("v = " + v), set(v, v + 1))),
    set(v, 0),
    loop_while(v < 2, sequence(log("v = " + v), set(v, v + 1)), min_calls=5),
    log("Done"),
)

run(s)
