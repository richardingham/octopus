# System Imports
import StringIO
import urllib

# Package Imports
from ..data.errors import Immutable

class Image (object):

	@property
	def value (self):
		output = StringIO.StringIO()
		img = self._image_fn()
		img.scale(0.25).getPIL().save(output, format = "PNG")
		encoded = "data:image/png;base64," + urllib.quote(output.getvalue().encode('base64'))

		return encoded

	@property
	def type (self):
		return "Image"

	def serialize (self):
		if self.alias is None:
			return "[Image]"
		else:
			return str(self.alias)

	def __init__ (self, title, fn):
		self.alias = None
		self.title = title
		self._image_fn = fn

	def set (self, value):
		raise Immutable

	def setLogFile (self, logFile):
		pass

	def stopLogging (self):
		pass

	def __str__ (self):
		return "Image"

	def __repr__ (self):
		return "<%s at %s>" % (
			self.__class__.__name__, 
			hex(id(self))
		)
