# Sibling Imports
from data import Image

# Package Imports
from ..machine import Machine, ui


class ImageProvider (Machine):
	protocolFactory = None
	name = "Provide an image from a webcam"
	update_frequency = 1

	def setup (self):
		# setup variables
		self.image = Image(title = "Tracked", fn = self._getImage)

		self.ui = ui(
			properties = [self.image]
		)

	def _getImage (self):
		return self.protocol.image()

	def start (self):
		def monitor ():
			self.image.refresh()

		self._tick(monitor, self.update_frequency)

	def stop (self):
		self._stopTicks()

	def disconnect (self):
		self.stop()

		try:
			self.protocol.disconnect()
		except AttributeError:
			pass

