
__version__ = "trunk"

def run (runnable):
	from twisted.internet import reactor

	if reactor.running:
		return runnable.run()

	else:
		def _complete (result):
			reactor.stop()

		def _run ():
			runnable.run().addBoth(_complete)

        reactor.callWhenRunning(_run)
        reactor.run() 
