# Package Imports
from ..workspace import Block, Disconnected, Cancelled
from .machines import machine_declaration
from .images import _image_block

# Twisted Imports
from twisted.internet import reactor, defer, task

# Octopus Imports
from octopus import data
from octopus.data.errors import Immutable
from octopus.data.data import BaseVariable
from octopus.constants import State
import octopus.transport.basic
from octopus.image.data import Image, ColorSpace
from octopus.image import functions as image_functions

# Python Imports
from time import time as now
from typing import Tuple
import os

# Numpy
import numpy


class connection_cv_flir_lepton(Block):
    def eval(self):
        from octopus.image.flir_lepton import cv_flir_lepton

        return defer.succeed(cv_flir_lepton(int(self.fields['ID'])))


class image_thermalfn(_image_block):
    outputType = float

    _map = {
        "MAX": numpy.max,
        "MIN": numpy.min,
        "MEAN": numpy.mean,
        "MEDIAN": numpy.median
    }

    def _calculate(self, result: Image):
        from octopus.image.flir_lepton import y16_to_degree_c
        
        if result is None:
            return
        
        if result.colorspace != ColorSpace.RADIOMETRIC:
            raise Exception("Thermal function required radiometric image data")

        op = self._map[self.fields['OP']]
        return y16_to_degree_c(op(result.data))

        # Emit a warning if bad op given
