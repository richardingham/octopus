
__version__ = "trunk"

def run (runnable, logging = True):
	from twisted.internet import reactor

	if reactor.running:
		return runnable.run()

	else:
		def _complete (result):
			reactor.stop()

		def _run ():
			runnable.run().addBoth(_complete)

		if logging:
			import sys
			from twisted.python import log
			log.startLogging(sys.stdout)
			runnable.log += log

		reactor.callWhenRunning(_run)
		reactor.run() 
