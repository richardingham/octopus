from octopus.sequence.runtime import *


def fn():
    return sequence(log("fn called"))


run(sequence(call(fn)))
