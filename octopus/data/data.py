# System Imports
from math import ceil
import operator

# Twisted Imports
from twisted.python.util import unsignedID

# NumPy
import numpy as np

# Package Imports
from ..util import now, timerange

# Sibling Imports
import errors

def _get_first_index (list, time):
	try:
		# Return the index of the first item in {list} which
		# is greater than or equal to {time}.
		# http://stackoverflow.com/q/2236906/
		return next(x[0] for x in enumerate(list) if x[1] >= time)
	except StopIteration:
		return None

def _get_last_index (list, time):
	l = len(list)

	try:
		# Return the index of the last item in {list} which
		# is greater than or equal to {time}.
		return l - 1 - next(
			x[0] for x in enumerate(reversed(list)) if x[1] <= time
		)
	except StopIteration:
		if l is 0:
			return None
		else:
			return 0

def _interp (x, x0, y0, x1, y1):
	try:
		return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
	except ZeroDivisionError:
		return y1

def _prepare (start, interval):
	if start < 0:
		start = now() + start

	if interval is None:
		interval = now() - start

	return start, interval


class Archive (object):
	# Set threshold_factor to None for non-numeric variables
	threshold_factor = 0.05
	min_delta = 10

	def __init__ (self):
		self._prev_x = None
		self._prev_y = None
		self.truncate()

	def truncate (self):
		self._zero = now()

		self._x = [self._prev_x] if self._prev_x is not None else []
		self._y = [self._prev_y] if self._prev_y is not None else []

		self._y_min = 0
		self._y_max = 0
		self._min_since_last = None
		self._max_since_last = None

	def push (self, x, y):
		# Ignore data points at times earlier than the most recent reset.
		if x < self._zero:
			return

		if self.threshold_factor is not None:
			# Update max and min
			if y > self._y_max:
				self._y_max = y
			elif y < self._y_min:
				self._y_min = y

			# The delta must be at least {factor} * absolute spread
			# of values collected so far, and at least {min_delta}.
			threshold = max(
				self.threshold_factor * (self._y_max - self._y_min), 
				self.min_delta
			)

			# Update Min / Max values
			if self._min_since_last is None \
			or y < self._min_since_last[1]:
				self._min_since_last = (x, y)

			if self._max_since_last is None \
			or y > self._max_since_last[1]:
				self._max_since_last = (x, y)

		# Store the values if the delta exceeds the threshold
		if self._prev_y is None \
		or self.threshold_factor is None \
		or abs(self._prev_y - y) > threshold:

			# Add up to one local maximum (or minimum) 
			# to retain concave curve shapes.
			if self.threshold_factor is not None:
				if self._max_since_last[1] > self._prev_y \
				and self._max_since_last[1] > y:
					self._x.append(self._max_since_last[0])
					self._y.append(self._max_since_last[1])
				elif self._min_since_last[1] < self._prev_y \
				and self._min_since_last[1] < y:
					self._x.append(self._min_since_last[0])
					self._y.append(self._min_since_last[1])

				self._min_since_last = (x, y)
				self._max_since_last = (x, y)

			self._x.append(x)
			self._y.append(y)
			self._prev_x = x
			self._prev_y = y

	def get (self, start, interval = None):
		start, interval = _prepare(start, interval)

		# Nothing in archive
		if self._prev_x is None:
			return []

		# Request range is outside archived data range
		if start > self._prev_x:
			return [(start, self._prev_y), (start + interval, self._prev_y)]
		if start + interval < self._zero:
			try:
				return [(start, self._y[0]), (start + interval, self._y[0])]
			except IndexError:
				return [(start, 0), (start + interval, 0)]

		# Collect data from archive
		i_start, i_end = self._get_indices(start, interval)
		vals = zip(self._x[i_start:i_end], self._y[i_start:i_end])

		# Fill in the start and end points.
		try:
			if start < self._zero:
				vals.insert(0, (self._zero, self._y[0]))
			elif start < self._x[i_start]:
				vals.insert(0, (start, _interp(
					start,
					self._x[i_start - 1], self._y[i_start - 1],
					self._x[i_start], self._y[i_start]
				)))
		except IndexError:
			pass

		try:
			if start + interval > self._prev_x:
				vals.append((start + interval, self._prev_y))
			elif start + interval > self._x[i_end]:
				vals.append((start + interval, _interp(
					start,
					self._x[i_end], self._y[i_end],
					self._x[i_end + 1], self._y[i_end + 1]
				)))
		except IndexError:
			pass

		return vals

	def _get_indices (self, start, interval):
		i_start = _get_first_index(self._x, start)
		i_end = _get_first_index(self._x, start + interval)

		return i_start, i_end


_default_alias_counters = {}
def _default_alias (object):
	class_name = object.__class__.__name__

	if class_name not in _default_alias_counters:
		_default_alias_counters[class_name] = 1
	else:
		_default_alias_counters[class_name] += 1
	
	return "{:s}_{:d}".format(class_name, _default_alias_counters[class_name])


class Variable (object):

	def get_value (self):
		return self._value
	value = property(get_value)

	def get_type (self):
		return self._type
	type = property(get_type)

	def serialize (self):
		if self.alias is None:
			return "[Variable]"
		else:
			return str(self.alias)

	def __init__ (self, type):
		self.alias = _default_alias(self)

		self._time = None
		self._value = None
		self._type = type
		self._length = 30 # in seconds

		self._x = []
		self._y = []
		self._archive = Archive()

		self._log_file = None

	def truncate (self):
		"""
		Empty the variable of all stored data.
		"""

		self._x = [self._time] if self._time is not None else []
		self._y = [self._value] if self._value is not None else []
		self._archive.truncate()

	def set (self, value):
		self._push(value)

	def get (self, start, interval = None, step = 1):
		"""
		Returns the value of the variable over a particular time period.
		
		Returns a list of (time, value) pairs between 
		[time = start and time = start + interval] (inclusive).
		
		start: earliest time to return data.
		interval: time-span requested.
		"""

		start, interval = _prepare(start, interval)

		try:
			if start > self._x[0]:
				return zip(
					timerange(start, interval, step).tolist(),
					self.interp(start, interval, step).tolist()
				)

			else:
				return self._archive.get(start, interval)

		except IndexError:
			return []

	def interp (self, start, interval = None, step = 1):
		"""
		Retrieve data for calculations.
		
		To perform calculations, there must be consistent time steps between
		each data point (defined by the step parameter).

		To acheive this the numpy.interp function is used on the variable's
		data. For optimal calculations the length of time that high-resolution
		data are kept (by default: 60 s) is increased if larger intervals are
		requested. Note that this will increase the memory consumption.
		
		Numpy.interp only works with variables that can be converted to a float.
		If interp fails, zero is returned over the timeperiod.
		"""

		start, interval = _prepare(start, interval)

		# Increase amount of high-resolution data kept, as long as it is
		# the most recent data being requested.
		if self._length is not None \
		and self._length < interval \
		and abs(start + interval - now()) < 1:
			self._length = interval

		new_x = timerange(start, interval, step)

		try:
			if start < self._x[0]:
				try:
					x_vals, y_vals = zip(*self._archive.get(start, self._x[0] - start))
				except ValueError:
					x_vals = y_vals = []	

				x_vals = list(x_vals) + self._x
				y_vals = list(x_vals) + self._y

				return np.interp(new_x, x_vals, y_vals)
			else:
				return np.interp(new_x, self._x, self._y)

		except ValueError:
			return np.zeros_like(new_x)

	def _push (self, value, time = None):
		if type(value) != self._type:
			value = self._type(value)

		if time is None:
			time = now()

		self._value = value
		self._time  = time
		self._x.append(time)
		self._y.append(value)
		self._archive.push(time, value)
		self._log(time, value)

		# Trim off any old data
		if self._length is not None and time - self._x[0] > self._length * 2:
			min_time = time - (self._length * 2)

			remove = 0
			for x in self._x:
				if x > min_time:
					break

				remove += 1

			if remove > 0:
				self._y = self._y[remove:]
				self._x = self._x[remove:]


	def _log (self, time, value):
		if self._log_file is not None:
			self._log_file.write(time, value)

	def setLogFile (self, logFile):
		if self._log_file is not None:
			self._log_file.close()

		self._log_file = logFile

		if self._value is not None:
			self._log_file.write(now(), self._value)

	def stopLogging (self):
		if self._log_file is not None:
			self._log_file.close()

		self._log_file = None		
	###

	def __str__ (self):
		return str(self.get_value())

	def __int__ (self):
		return int(self.get_value())

	def __float__ (self):
		return float(self.get_value())

	def __nonzero__ (self):
		return bool(self.get_value())

	def __repr__ (self):
		return "<{class_name} at {reference}: {var_alias} ({var_type}) = {var_value}>".format(
			class_name = self.__class__.__name__, 
			reference = hex(unsignedID(self)),
			var_alias = self.alias,
            var_type = self.type.__name__,
			var_value = self.value
		)


class Constant (Variable):
	def __init__ (self, value):
		self._value = value
		self._type = type(value)

	def set (self, value):
		raise NotImplementedError

	def _push (self, value):
		raise NotImplementedError

	def get (self, start, interval = None, step = 1):
		start, interval = _prepare(start, interval)

		return [(start, self._value), (start + interval, self._value)]

	def interp (self, start, interval = None, step = 1):
		start, interval = _prepare(start, interval)
		new_x = timerange(start, interval, step)

		try:
			return np.ones_like(new_x) * self._value
		except TypeError:
			return np.zeros_like(new_x)

	def serialize (self):
		return str(self._value)


class Expression (Variable):
	def set (self, value):
		raise NotImplementedError

	def _push (self, value):
		raise NotImplementedError


# Variable should emulate a numerical variable
_unary_ops = (
	(" not ", operator.__not__), (" abs ", operator.__abs__),
	(" -", operator.__neg__), (" +", operator.__pos__))
_binary_ops = (
	(" < ", operator.__lt__), (" <= ", operator.__le__), (" == ", operator.__eq__), 
	(" != ", operator.__ne__), (" > ", operator.__gt__), (" >= ", operator.__ge__),
	(" + ", operator.__add__), (" - ", operator.__sub__), (" / ", operator.__div__), 
	(" / ", operator.__truediv__), (" // ", operator.__floordiv__), 
	(" * ", operator.__mul__), (" % ", operator.__mod__),
	("**", operator.__pow__),
	(" and ", operator.__and__), (" or ", operator.__or__)
)

# http://stackoverflow.com/questions/100003/what-is-a-metaclass-in-python/6581949#6581949
def _def_binary_op (symbol, operator):
	def init (self, lhs, rhs):
		self.alias = _default_alias(self)

		self._lhs = lhs if isinstance(lhs, Variable) else Constant(lhs)
		self._rhs = rhs if isinstance(rhs, Variable) else Constant(rhs)
		self._type = None

	def get_value (self):
		try:
			return operator(self._lhs.value, self._rhs.value)
		except TypeError:
			if self._lhs.type is str or self._rhs.type is str:
				return operator(str(self._lhs.value), str(self._rhs.value))
			raise

	def get_type (self):
		if self._type is None:
			self._type = type(self.get_value())

		return self._type

	def get (self, start, interval = None, step = 1):
		start, interval = _prepare(start, interval)

		x_vals = timerange(start, interval, step)
		y_vals = self.interp(start, interval, step)

		return zip(x_vals.tolist(), y_vals.tolist())

	def interp (self, start, interval = None, step = 1):
		start, interval = _prepare(start, interval)

		l = self._lhs.interp(start, interval, step)
		r = self._rhs.interp(start, interval, step)

		try:
			return operator(l, r)

		# Try a cast to string if the operator fails.
		except TypeError:
			if self._lhs.type is str or self._rhs.type is str:
				return operator(str(l), str(r))

			raise

	def serialize (self):
		return "(" + \
			self._lhs.serialize() + symbol \
			+ self._rhs.serialize() + ")"

	cls = type(
		operator.__name__[2:-2].capitalize() + "Expression", 
		(Expression,), 
		{ 
			"__init__": init,
			"get_value": get_value,
			"get_type": get_type,
			"value": property(get_value),
			"type": property(get_type),
			"get": get,
			"interp": interp,
			"serialize": serialize
		}
	)

	def op_fn (self, other):
		return cls(self, other)

	def op_rfn (self, other):
		return cls(other, self)

	setattr(Variable, operator.__name__, op_fn)
	setattr(Variable, "__r" + operator.__name__[2:], op_rfn)

def _def_unary_op (symbol, operator):
	def init (self, operand):
		self.alias = _default_alias(self)

		self._operand = operand
		self._type = None

	def get_value (self):
		return operator(self._operand.value)

	def get_type (self):
		if self._type is None:
			self._type = type(self.get_value())

		return self._type

	def get (self, start, interval = None, step = 1):
		start, interval = _prepare(start, interval)

		x_vals = timerange(start, interval, step)
		y_vals = self.interp(start, interval, step)

		return zip(x_vals.tolist(), y_vals.tolist())

	def interp (self, start, interval = None, step = 1):
		start, interval = _prepare(start, interval)

		return operator(self._operand.get(start, interval, step))	

	def serialize (self):
		return symbol + self._operand.serialize()

	cls = type(
		op.__name__[2:-2].capitalize() + "Expression", 
		(Expression,), 
		{ 
			"__init__": init,
			"get_value": get_value,
			"get_type": get_type,
			"value": property(get_value),
			"type": property(get_type),
			"get": get,
			"interp": interp
		}
	)

	def op_fn (self, other):
		return cls(self, op)

	setattr(Variable, op.__name__, op_fn)

[_def_unary_op(symbol, op) for symbol, op in _unary_ops]
[_def_binary_op(symbol, op) for symbol, op in _binary_ops]
