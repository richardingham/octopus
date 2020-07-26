# Sibling Imports
from .data import ImageProperty

# Package Imports
from ..machine import Machine


class CameraViewer (Machine):

    protocolFactory = None
    name = "Monitor a webcam"

    def setup (self):
        # setup variables
        self.image = ImageProperty(title = "Image", fn = self._get_image)

    # def show (self):
    #     self._get_image().show()

    def _get_image (self):
        return self.protocol.image()
