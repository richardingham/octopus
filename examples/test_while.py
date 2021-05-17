from octopus.sequence.runtime import *

v = variable(0, "v", "v")

async def main_sequence():
    while v < 5:
        await log("v = " + v)
        await v.set(v + 1)

    await v.set(0)

    _calls = 0
    min_calls = 5
    while v < 2 or _calls < min_calls:
        _calls += 1
        await log("v = " + v)
        await v.set(v + 1)

    await log("Done")


run(main_sequence)

