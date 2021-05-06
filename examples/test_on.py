from octopus.sequence.runtime import *
from octopus.sequence.util import Trigger


async def set_v ():
    await log("fn called"),
    await v.set(False)

v = variable(False, "v", "v")
v2 = variable(False, "v", "v")

o1 = Trigger(v == True, set_v)
o2 = Trigger(v2 == True, log("o2 triggered"), max_calls = 1)

@add_dependents(o1, o2)
async def main_sequence():
    await log("Loading o")
    await wait("8s")
    await v2.set(True)
    await wait("1s")

loop = asyncio.get_event_loop()
loop.call_later(2, v.set, True)
loop.call_later(4, v.set, True)
loop.call_later(6, v.set, True)

run(main_sequence)

