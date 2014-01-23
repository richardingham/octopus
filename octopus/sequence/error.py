
class Error (Exception):
	"""Base class for exceptions in this module."""
	pass

class NotRunning (Error):
	"""Exception raised if an attempt is made to stop a step
	which has not started running yet."""
	pass

class AlreadyRunning (Error):
	"""Exception raised if an attempt is made to start a step
	which is currently running."""
	pass

class NotPaused (Error):
	"""Exception raised if an attempt is made to resume a step
	which is not paused."""
	pass

class Stopped (Exception):
	"""Exception raised if stop() is called on a step."""
	pass
