# Sibling Imports
from data import Image

# Package Imports
from ..machine import Machine, ui


class CameraViewer (Machine):

	protocolFactory = None
	name = "Monitor a webcam"

	def setup (self):
		# setup variables
		self.image = Image(title = "Image", fn = self._get_image)

		self.ui = ui(
			properties = [self.image]
		)

	def show (self):
		self._get_image().show()

	def _get_image (self):
		return self.protocol.image()
