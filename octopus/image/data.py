# Twisted Imports
from twisted.internet import defer

# System Imports
import StringIO
import urllib
from time import time as now

# Package Imports
from ..data.errors import Immutable
from ..data.data import BaseVariable


class BaseImage (BaseVariable):

	@property
	def value (self):
		return self._value

	def get_value (self):
		return self._value

	@property
	def type (self):
		return Image

	def serialize (self):
		if self.alias is None:
			return "[Image]"
		else:
			return str(self.alias)

	def __init__ (self):
		self.alias = None
		self.title = ""

	def setLogFile (self, logFile):
		pass

	def stopLogging (self):
		pass

	def __str__ (self):
		output = StringIO.StringIO()
		img = self.get_value()
		img.scale(0.25).getPIL().save(output, format = "PNG")
		encoded = "data:image/png;base64," + urllib.quote(output.getvalue().encode('base64'))

		return encoded

	def __repr__ (self):
		return "<%s at %s>" % (
			self.__class__.__name__, 
			hex(id(self))
		)


class Image (BaseImage):

	def __init__ (self, title, fn):
		self.alias = None
		self.title = title
		self._image_fn = fn
		self._value = None

	@defer.inlineCallbacks
	def refresh (self):
		self._value = yield defer.maybeDeferred(self._image_fn)
		self.emit("change", value = None, time = now())

	def set (self, value):
		raise Immutable


class DerivedImage (BaseImage):

	def __init__ (self):
		self.alias = None
		self._value = None

	def set (self, value):
		self._value = value
		self.emit("change", value = None, time = now())

	_push = set

