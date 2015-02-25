# Twisted Import
from twisted.internet import defer, threads

# System Imports
import cv2
from cv2 import cv
import SimpleCV


class webcam (object):
	def __init__ (self, device = -1):
		self.device_index = device
		self.name = "webcam(%s)" % device
		self.camera = None

	@defer.inlineCallbacks
	def connect (self, _protocolFactory):
		if self.camera is None:
			self.camera = yield threads.deferToThread(SimpleCV.Camera, self.device_index)
		
		defer.returnValue(self)

	@defer.inlineCallbacks
	def image (self):
		"""
		Get an image from the camera.
		
		Returns a SimpleCV Image.
		"""

		i = yield threads.deferToThread(self.camera.getImage)

		if i is None:
			print "No image"

		defer.returnValue(i)

	def disconnect (self):
		self.camera = None


class webcam_nothread (object):
	def __init__ (self, device = -1):
		self.device_index = device
		self.name = "webcam_nothread(%s)" % device
		self.camera = None

	def connect (self, _protocolFactory):
		if self.camera is None:
			self.camera = SimpleCV.Camera(self.device_index)
		
		return self

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

	@defer.inlineCallbacks
	def connect (self, _protocolFactory):
		if self.camera is None:
			self.camera = yield threads.deferToThread(cv2.VideoCapture, self.device_index)

		defer.returnValue(self)

	@defer.inlineCallbacks
	def image (self):
		"""
		Get an image from the camera.
		
		Returns a SimpleCV Image.
		"""

		try:
			flag, img_array = yield threads.deferToThread(self.camera.read)
		except SystemError:
			return

		if flag is False:
			print "No image"
			return

		defer.returnValue(SimpleCV.Image(
			source = cv.fromarray(img_array),
			cv2image = True)
		)

	def disconnect (self):
		threads.deferToThread(self.camera.release)
