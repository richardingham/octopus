# System Imports
import math

# Sibling Imports
import data

# NumPy
import numpy as np

class _Counter (object):
	def __init__ (self):
		self.counts = {}

	def inc (self, key):
		if key not in self.counts:
			self.counts[key] = 1
		else:
			self.counts[key] += 1

		return self.counts[key]

	def alias (self, name):
		return name + "_" + str(self.inc(name))

_counter = _Counter()

class Function (data.Variable):
	def __init__ (self, expr):
		if not isinstance(expr, data.Variable):
			raise data.InvalidType

		self._expr = expr

		data.Variable.__init__(self, expr.type)

		#if alias is None:
		self.alias = _counter.alias(self.__class__.__name__)
		#else:
		#	_counter.inc(self.__class__.__name__)

	@property
	def value (self):
		return self.get_value()

	def get_value (self):
		raise NotImplementedError

	def get (self, start, interval = None, step = 1):
		start, interval = data._prepare(start, interval)

		x_vals = data.timerange(start, interval, step)
		y_vals = self.interp(start, interval, step)

		try:
			return zip(x_vals.tolist(), y_vals.tolist())
		except TypeError, ValueError:
			return zip(x_vals.tolist(), [None] * len(x_vals))

	def interp (self, start, interval, step):
		raise NotImplementedError

	def serialize (self):
		raise NotImplementedError

class FramedManipulation (Function):
	def __init__ (self, expr, frame = 1.0, title = "", alias = None):
		Function.__init__(self, expr)

		self.title = title
		self.alias = alias
		self._frame = float(frame)

class Differential (FramedManipulation):
	def interp (self, start, interval, step):
		n = max(1, int(self._frame / interval))
		return np.gradient(self._expr.interp(start, interval, step), n)

	def get_value (self):
		return self.get(-5, 5, 0.1).tolist().pop()

	def serialize (self):
		return " Diff (" + self._expr.serialize() + ")"


class SecondDifferential (Differential):
	def interp (self, start, interval, step):
		n = max(1, int(self._frame / interval))
		diff1 = np.gradient(self._expr.interp(start, interval, step), n)
		return np.gradient(diff1, n)

	def serialize (self):
		return " 2ndDiff (" + self._expr.serialize() + ")"


class Max (FramedManipulation):
	def get (self, start, interval, step):
		new_x = data.timerange(start, interval, step)
		m = np.max(self._expr.interp(-self._frame, self._frame, step))
		return np.ones_like(new_x) * m

	def get_value (self):
		return np.max(self._expr.interp(-self._frame, self._frame, 0.1))

	def serialize (self):
		return " Max (" + self._expr.serialize() + ", " + str(frame) + ")"


class Min (FramedManipulation):
	def get (self, start, interval, step):
		new_x = data.timerange(start, interval, step)
		m = np.min(self._expr.interp(-self._frame, self._frame, step))
		return np.ones_like(new_x) * m

	def get_value (self):
		return np.min(self._expr.interp(-self._frame, self._frame, 0.1))

	def serialize (self):
		return " Min (" + self._expr.serialize() + ", " + str(frame) + ")"

class Smooth (FramedManipulation):
	def __init__ (self, expr, window, frame = 1.0, title = "", alias = None):
		FramedManipulation.__init__(self, expr, frame, title, alias)

		self._frame = float(frame)
		self._window_len = len(window)
		self._half_window_len = (self._window_len - 1) / 2
		self._window = window / window.sum() # Normalised

		if int(self._half_window_len) != self._half_window_len:
			raise Exception ("Smooth(): length of supplied window must be 2n+1")

	def get (self, start, interval, step):
		
		new_x = data.timerange(start, interval, step)

		# Get the slice of y according to frame.
		# Need to use raw data
		# TODO: make all manupulations use raw data!
		x = self._expr._x
		y = self._expr._y
		
		if len(y) > self._window_len:
			# Extend the slice so that the window can be applied to the edges.
			s = np.r_[y[self._window_len-1:0:-1], y, y[-1:-self._window_len:-1]]

			y_smooth = np.convolve(self._window, s, mode = 'valid')
			y = y_smooth[self._half_window_len : len(y_smooth) - self._half_window_len]
			
		return np.interp(new_x, x, y)

	def get_value (self):
		try:
			# Cast is required to avoid getting a numpy.float64 result!
			return float(self.get(-self._frame, self._frame, 0.1)[-1])
		except IndexError:
			return None

	def serialize (self):
		return " Smooth (" + self._expr.serialize() + ", " + str(frame) + ")"

## average?

class Square (Function):
	def get (self, start, interval, step):
		return np.square(self._expr.get(start, interval, step))

	def get_value (self):
		return self._expr.value ** 2

	def serialize (self):
		return " Square (" + self._expr.serialize() + ")"


class Sqrt (Function):
	def get (self, start, interval, step):
		return np.sqrt(self._expr.interp(start, interval, step))

	def get_value (self):
		return np.sqrt(self._expr.value)

	def serialize (self):
		return " Sqrt (" + self._expr.serialize() + ")"


class Abs (Function):
	def get (self, start, interval, step):
		return np.absolute(self._expr.interp(start, interval, step))

	def get_value (self):
		return abs(self._expr.value)

	def serialize (self):
		return " Abs (" + self._expr.serialize() + ")"


class Sin (Function):
	def get (self, start, interval, step):
		return np.sin(self._expr.interp(start, interval, step))

	def get_value (self):
		return np.sin(self._expr.value)

	def serialize (self):
		return " Sin (" + self._expr.serialize() + ")"


class Cos (Function):
	def get (self, start, interval, step):
		return np.cos(self._expr.interp(start, interval, step))

	def get_value (self):
		return np.cos(self._expr.value)

	def serialize (self):
		return " Cos (" + self._expr.serialize() + ")"


class Tan (Function):
	def get (self, start, interval, step):
		return np.tan(self._expr.interp(start, interval, step))

	def get_value (self):
		return np.tan(self._expr.value)

	def serialize (self):
		return " Tan (" + self._expr.serialize() + ")"



