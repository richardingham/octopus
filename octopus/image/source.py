# Twisted Import
from twisted.internet import defer, threads

# System Imports
import cv2
from cv2 import cv
from SimpleCV import Camera, Image

class webcam (object):
	def __init__ (self, device = -1):
		self.device_index = device
		self.name = "webcam(%s)" % device
		self.camera = None

	def connect (self, _protocolFactory):
		if self.camera is not None:
			return defer.succeed(self)

		connected = defer.Deferred()

		def ok (result):
			self.camera = result
			connected.callback(self)

		d = threads.deferToThread(Camera, self.device_index)
		d.addCallbacks(ok, connected.errback)

		return connected

	def image (self):
		"""
		Get an image from the camera.
		
		Returns a SimpleCV Image.
		"""

		i = self.camera.getImage()

		if i is None:
			print "No image"

		return i

	def disconnect (self):
		self.camera = None


class cv_webcam (object):
	def __init__ (self, device):
		self.device_index = device
		self.name = "cv_webcam(%s)" % device
		self.camera = None

	def connect (self, _protocolFactory):
		if self.camera is not None:
			return defer.succeed(self)

		connected = defer.Deferred()

		def ok (result):
			self.camera = result
			connected.callback(self)

		d = threads.deferToThread(cv2.VideoCapture, self.device_index)
		d.addCallbacks(ok, connected.errback)

		return connected

	def image (self):
		"""
		Get an image from the camera.
		
		Returns a SimpleCV Image.
		"""

		try:
			flag, img_array = self.camera.read()
		except SystemError:
			return None

		if flag is False:
			print "No image"
			return None

		return Image(source = cv.fromarray(img_array), cv2image = True)

	def disconnect (self):
		self.camera.release()
