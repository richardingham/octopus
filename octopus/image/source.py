# System Imports
import cv2
import json
from typing import Optional

# Library imports
import numpy

# Twisted Import
from twisted.internet import reactor, defer, threads, protocol
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.interfaces import IAddress

# Package Imports
from .data import Image, ColorSpace

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
        
        Returns an Image object.
        """

        try:
            flag, img_array = yield threads.deferToThread(self.camera.read)
        except SystemError:
            return

        if flag is False:
            print ("No image")
            return

        defer.returnValue(Image(img_array, ColorSpace.BGR))

    def disconnect (self):
        threads.deferToThread(self.camera.release)


class _camera_proxy_protocol (protocol.Protocol):
    _state: str
    _buffer: bytes = b''
    _image_callback: Optional[defer.Deferred] = None
    _camera_id: Optional[bytes] = None

    def setCameraId(self, camera_id: int):
        self._camera_id = str(camera_id).encode()
        self.requestFormat()

    # def connectionMade(self):
    #     if self._camera_id is not None:
    #         self.requestFormat()

    def dataReceived(self, data: bytes):
        """
        Byte 1: command
        Byte 2-5: length
        Byte 6+: data
        """

        self._buffer += data

        if len(self._buffer) > 5:
            command = chr(self._buffer[0])
            length = int.from_bytes(self._buffer[1:5], byteorder = 'big')

            if len(self._buffer) >= length + 5:

                data = self._buffer[5 : 5 + length]
                self._buffer = self._buffer[5 + length : ]

                if command == 'F':
                    self.formatReceived(data)
                elif command == 'I':
                    self.imageReceived(data)
    
    def formatReceived (self, data: bytes):
        image_format = json.loads(data.decode())

        if image_format['channels'] == 1:
            self._image_shape = (image_format['height'], image_format['width'])
        else:
            self._image_shape = (
                image_format['height'], 
                image_format['width'],
                image_format['channels']
            )

        self._image_colorspace = image_format['colorspace']
    
    def imageReceived (self, data: bytes):
        try:
            img_data = numpy.reshape(
                numpy.frombuffer(data, dtype = numpy.uint8), 
                newshape = self._image_shape
            )
            self._image_callback.callback(img_data)
        except (AttributeError, defer.AlreadyCalledError) as e:
            # No callback, or callback already done. (Unexpected image data).
            pass
        except Exception as e:
            try:
                self._image_callback.errback(e)
            except defer.AlreadyCalledError:
                pass

    def requestFormat (self):
        self.transport.write(b'F' + self._camera_id + b'\n')

    def requestImage (self):
        self._image_callback = defer.Deferred()
        self.transport.write(b'I' + self._camera_id + b'\n')
        return self._image_callback


class camera_proxy (object):
    def __init__ (self, host, port, camera_id):
        self.point = TCP4ClientEndpoint(reactor, host, port)
        self.name = f"camera_proxy({host!s}, {port!s})"
        self.camera_id = camera_id

    @defer.inlineCallbacks
    def connect (self, _protocolFactory):
        self._protocol = yield self.point.connect(
            protocol.Factory.forProtocol(_camera_proxy_protocol)
        )
        self._protocol.setCameraId(self.camera_id)
        # yield self._protocol._get_format_information()

        defer.returnValue(self)

    @defer.inlineCallbacks
    def image (self):
        """
        Get an image from the camera.
        
        Returns a SimpleCV Image.
        """

        try:
            img_array = yield self._protocol.requestImage()
        except Exception as e:
            print('Exception fetching image', e)
            return

        defer.returnValue(Image(img_array, ColorSpace.BGR))

    def disconnect (self):
        threads.deferToThread(self.camera.release)