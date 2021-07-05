# System Imports
import os
import cv2
from typing import Optional

# Library imports
import numpy

# Twisted Import
from twisted.internet import reactor, defer, threads, protocol

# Package Imports
from .data import Image, ColorSpace

def y16_to_degree_c(value: int) -> float:
    return (value - 27315) / 100.0

# Lepton access via openCV (works on linux)
# https://github.com/groupgets/purethermal1-uvc-capture/issues/35

# Get camera serial:
# https://stackoverflow.com/questions/58962748/opencv-with-multiple-webcams-how-to-tell-which-camera-is-which-in-code
#  p = subprocess.Popen('udevadm info --name=/dev/video{} | grep ID_SERIAL= | cut -d "=" -f 2'.format(cam_id), stdout=subprocess.PIPE, shell=True)

class cv_flir_lepton(object):
    def __init__(self, device):
        self.device_index = device
        self.name = "cv_flir_lepton(%s)" % device
        self.camera = None

    @defer.inlineCallbacks
    def connect(self, _protocolFactory):
        if self.camera is None:
            # https://flir.custhelp.com/app/answers/detail/a_id/3387
            if os.name == 'nt':
                self.camera = yield threads.deferToThread(cv2.VideoCapture, self.device_index + cv2.CAP_DSHOW)
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('Y','1','6',' '))
                self.camera.set(cv2.CAP_PROP_CONVERT_RGB, 0)
            elif os.name == 'posix':
                self.camera = yield threads.deferToThread(cv2.VideoCapture, self.device_index)
                self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('Y','1','6',' '))
                self.camera.set(cv2.CAP_PROP_CONVERT_RGB, 0)

        defer.returnValue(self)

    @defer.inlineCallbacks
    def image(self):
        """
        Get an image from the camera.
        
        Returns an Image object.
        """

        try:
            flag, img_array = yield threads.deferToThread(self.camera.read)
            img_array = img_array[:120, :] # 122x160 => 120x160 discard 2 last row
            img_array = cv2.resize(img_array[:,:], (640, 480))
        except SystemError:
            return

        if flag is False:
            print ("No image")
            return

        defer.returnValue(Image(img_array, ColorSpace.RADIOMETRIC))

    def disconnect(self):
        threads.deferToThread(self.camera.release)
