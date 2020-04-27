# Package Imports
from ..workspace import Block, Disconnected, Cancelled
from .machines import machine_declaration

# Twisted Imports
from twisted.internet import reactor, defer, task

# Octopus Imports
from octopus import data
from octopus.data.errors import Immutable
from octopus.data.data import BaseVariable
from octopus.constants import State
import octopus.transport.basic

# Python Imports
from time import time as now
import os

# Numpy
import numpy


class _image_block (Block):
	def _calculate (self, result):
		return result

	def eval (self):
		def calculate (result):
			if result is None:
				return None

			return self._calculate(result)

		self._complete = self.getInputValue('INPUT', None)
		self._complete.addCallback(calculate)
		return self._complete


class image_findcolour (_image_block):
	_map = {
		"RED": lambda r, g, b: r - g,
		"GREEN": lambda r, g, b: g - r,
		"BLUE": lambda r, g, b: b - r,
	}

	def _calculate (self, result):
		if result is None:
			return None

		op = self._map[self.fields['OP']]
		return op(*result.splitChannels())

		# Emit a warning if bad op given


class image_threshold (_image_block):
	def _calculate (self, result):
		return result.threshold(int(self.fields['THRESHOLD']))


class image_erode (_image_block):
	def _calculate (self, result):
		return result.erode()


class image_invert (_image_block):
	def _calculate (self, result):
		return result.invert()


class image_colourdistance (Block):
	def _calculate (self, input, colour):
		return input.colorDistance(color = colour)

	def eval (self):
		def calculate (results):
			input, colour = results

			if input is None or colour is None:
				return None

			return self._calculate(input, colour)

		self._complete = defer.gatherResults([
			self.getInputValue('INPUT', None),
			self.getInputValue('COLOUR', (0, 0, 0))
		]).addCallback(calculate)

		return self._complete


class image_huedistance (image_colourdistance):
	def _calculate (self, input, colour):
		return input.hueDistance(colour)


class image_crop (_image_block):
	def _calculate (self, result):
		x = int(self.fields['X'])
		y = int(self.fields['Y'])
		w = int(self.fields['W'])
		h = int(self.fields['H'])

		if result is None:
			return None

		return result.crop(x, y, w, h)


class image_intensityfn (_image_block):
	outputType = float

	_map = {
		"MAX": numpy.max,
		"MIN": numpy.min,
		"MEAN": numpy.mean,
		"MEDIAN": numpy.median
	}

	def _calculate (self, result):
		if result is None:
			return

		op = self._map[self.fields['OP']]
		return int(op(result.getGrayNumpy()))

		# Emit a warning if bad op given


class image_tonumber (_image_block):
	outputType = int

	_map = {
		"CENTROIDX": lambda blob: blob.centroid()[0],
		"CENTROIDY": lambda blob: blob.centroid()[1],
		"SIZEX": lambda blob: blob.minRectWidth(),
		"SIZEY": lambda blob: blob.minRectHeight(),
	}

	def _calculate (self, result):
		try:
			blobs = result.findBlobs(100) # min_size
			blob = blobs.sortArea()[-1]
		except AttributeError:
			return None

		op = self._map[self.fields['OP']]
		return op(blob)

		# Emit a warning if bad op given


class machine_imageprovider (machine_declaration):
	def getMachineClass (self):
		from octopus.image.provider import ImageProvider
		return ImageProvider


class machine_singletracker (machine_declaration):
	def getMachineClass (self):
		from octopus.image import tracker
		return tracker.SingleBlobTracker


class machine_multitracker (machine_declaration):
	def getMachineClass (self):
		from octopus.image import tracker
		return tracker.MultiBlobTracker

	def getMachineParams (self):
		import json
		try:
			return {
				"count": json.loads(self.mutation)['count']
			}
		except (ValueError, KeyError):
			return {}


class connection_cvcamera (Block):
	def eval (self):
		if os.name == 'nt':
			from octopus.image.source import webcam_nothread
			cv_webcam = webcam_nothread
		else:
			from octopus.image.source import cv_webcam

		return defer.succeed(cv_webcam(int(self.fields['ID'])))
