import twisted.python.log
import sys
twisted.python.log.startLogging(sys.stdout)

from twisted.internet import defer
defer.Deferred.debug = True

from octopus.sequence.runtime import *


async def sequence_1():
    await log("one")

    async def sequence_2():
        await log("two")
        await log("three")

    await sequence_2()
    await wait("3s")
    await log("four")


run(sequence_1)
