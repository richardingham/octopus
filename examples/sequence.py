from twisted.python import log
import sys
log.startLogging(sys.stdout)

from twisted.internet import defer
defer.Deferred.debug = True

from octopus.runtime import *

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


