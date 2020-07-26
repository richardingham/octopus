
__version__ = "trunk"

def run (runnable, logging = True):
	from twisted.internet import reactor

	if reactor.running:
		return runnable.run()

	else:
		if logging:
			import sys
			from twisted.python import log

			log.startLogging(sys.stdout)
			runnable.on("log", log.msg)

		def _complete (result):
			reactor.stop()

			if logging:
				runnable.off("log", log.msg)

		def _run ():
			runnable.run().addBoth(_complete)

		reactor.callWhenRunning(_run)
		reactor.run()
