from octopus.sequence.runtime import *
from octopus.sequence.control import StateMonitor

v = variable(0, "i", "i")
d_test = (((v >= 4) & (v <= 6)) | ((v >= 9) & (v <= 14))) == False

async def d_trigger():
    await log("Triggered")
    await wait(4)
    await log("Still Triggered")

async def d_reset():
    await log("Reset")
    await wait(4)
    await log("... not triggered again")

d = StateMonitor()
d.add(d_test)
d.trigger_step = d_trigger
d.reset_step = d_reset

async def main_sequence():
    async with d:
        await log("Running"),
        while v < 20:
            await increment(v)
            await wait(1)
            await log("v = " + v)

        await log("Stopping experiment")

run(main_sequence)


