import twisted.python.log
import sys
twisted.python.log.startLogging(sys.stdout)

from twisted.internet import defer
defer.Deferred.debug = True

from octopus.sequence.runtime import *

s = sequence(
	log("one"),
	sequence(
		log("two"),
		log("three"),
	),
	wait("3s"),
	log("four"),
)

run(s)


