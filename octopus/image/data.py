# System Imports
from io import BytesIO
from time import time as now
import base64
from urllib.parse import quote

# Library Imports
import cv2
import numpy

# Twisted Imports
from twisted.internet import defer

# Package Imports
from ..data.errors import Immutable
from ..data.data import BaseVariable


class ColorSpace:
    """
    **SUMMARY**
    The colorspace  class is used to encapsulate the color space of a given image.
    This class acts like C/C++ style enumerated type.
    See: http://stackoverflow.com/questions/2122706/detect-color-space-with-opencv
    """
    UNKNOWN = 0
    BGR = 1
    GRAY = 2
    RGB = 3
    HLS = 4
    HSV = 5
    XYZ  = 6
    YCrCb = 7
    

class Image:
    data = None
    size: int = 0
    channels: int = 0
    colorspace = None

    def __init__ (self, data: numpy.ndarray, colorspace):
        self.data = data
        self.height = data.shape[0]
        self.width = data.shape[1]
        self.colorspace = colorspace

        try:
            self.channels = data.shape[2]
        except IndexError:
            self.channels = 1


class BaseImageProperty (BaseVariable):

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
        self._value = None

    def setLogFile (self, logFile):
        pass

    def stopLogging (self):
        pass

    def __str__ (self):
        img = self.get_value()

        if img is None:
            return ''

        scaled_x = int(img.width / 4)
        scaled_y = int(img.height / 4)
        scaled = cv2.resize(img.data, (scaled_x, scaled_y))

        # Encode
        is_success, buffer = cv2.imencode(".png", scaled)
        io_buf = BytesIO(buffer)

        encoded = "data:image/png;base64," + quote(base64.b64encode(io_buf.getvalue()).decode())

        return encoded

    def __repr__ (self):
        return "<%s at %s>" % (
            self.__class__.__name__, 
            hex(id(self))
        )


class ImageProperty (BaseImageProperty):

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


class DerivedImageProperty (BaseImageProperty):

    def __init__ (self):
        self.alias = None
        self._value = None

    def set (self, value):
        self._value = value
        self.emit("change", value = None, time = now())

    _push = set

