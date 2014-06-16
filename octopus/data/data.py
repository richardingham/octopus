# System Imports
from math import ceil
import operator

# Twisted Imports
from twisted.python.util import unsignedID

# Package Imports
from ..util import now, timerange

# Sibling Imports
import errors

def _upper_bound (list, time):
	# Return the index of the first item in {list} which
	# is greater than or equal to {time}.
	# http://stackoverflow.com/q/2236906/
	return next(x[0] for x in enumerate(list) if x[1] >= time, None)


def _lower_bound (list, time):
	l = len(list)

	# Return the index of the last item in {list} which
	# is less than or equal to {time}.
	return l - 1 - next(
		x[0] for x in enumerate(reversed(list)) if x[1] <= time,
		None if l == 0 else 0
	)

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
		i_start = _lower_bound(self._x, start)
		i_end   = _lower_bound(self._x, start + interval)
		vals = zip(self._x[i_start:i_end], self._y[i_start:i_end])

		# Fill in the start and end points if necessary.
		try:
			if start < self._zero:
				vals.insert(0, (self._zero, self._y[0]))
		except IndexError:
			pass

		try:
			if start + interval > self._prev_x:
				vals.append((start + interval, self._prev_y))
		except IndexError:
			pass

		return vals


_default_alias_counters = {}
def _default_alias (object):
	class_name = object.__class__.__name__

	if class_name not in _default_alias_counters:
		_default_alias_counters[class_name] = 1
	else:
		_default_alias_counters[class_name] += 1
	
	return "{:s}_{:d}".format(class_name, _default_alias_counters[class_name])



class BaseVariable (object):
	alias = ""

	@property
	def value (self):
		return self._value

	@property
	def type (self):
		return self._type

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

class Variable2 (BaseVariable):
	length = 30 # in seconds
	
	def __init__ (self, type, value = None):
		self.alias = _default_alias(self)

		self._time = None
		self._value = None
		self._type = type

		self._x = []
		self._y = []
		self._archive = Archive()

		self._log_file = None
		
		if value is not None:
			self._push(value)

	def truncate (self):
		"""
		Empty the variable of all stored data.
		"""
		
		# Trigger clear event

		self._x = [self._time] if self._time is not None else []
		self._y = [self._value] if self._value is not None else []
		self._archive.truncate()

	def set (self, value):
		self._push(value)

	def at (self, time):
		return self.get(time, 0)

	def get (self, start, interval = None):	
		"""
		Returns the value of the variable over a particular time period.
		
		Returns a list of (time, value) pairs between 
		[time = start and time = start + interval] (inclusive).
		
		start: earliest time to return data.
		interval: time-span requested.
		
		If interval = 0, a single data point (not a tuple)
		is returned, rather than a list. 
		
		If interval = None, then data are returned from start
		up to the current time.
		
		If start < 0, then this number of seconds is subtracted
		from the current time.
		"""

		if start < self._x[0]:
			return self._archive.get(start, interval)
		
		start, interval = _prepare(start, interval)
		
		i_start = _lower_bound(self._x, start)
		i_end   = _lower_bound(self._x, start + interval)
		
		# If asked for a single point, do a linear interpolation
		if interval == 0:
			return _interp(
				start, 
				self._x[i_start], 
				self._y[i_start], 
				self._x[i_end],
				self._y[i_end]
			)
		
		# Return a slice of (x, y) tuples between the two times.
		else:
			return zip(self._x[i_start:i_end], self._y[i_start:i_end])
	
	def _push (self, value, time = None):
		if type(value) != self._type:
			value = self._type(value)

		if time is None:
			time = now()

		self._value = value
		self._time  = time

		# Only store changes
		if self._y[-1] == value:
			self._x[-1] = time
		else:
			self._x.append(time)
			self._y.append(value)
			
			# Trigger change event (time, value)

			# Trim old data
			mid = len(self._x) / 2
			if time - self._x[mid] > self.length:
				self._y = self._y[mid:]
				self._x = self._x[mid:] 

		self._archive.push(time, value)
		self._log(time, value)

	# Todo: Put these in event watchers in the experiment.
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

class Constant (BaseVariable):
	def __init__ (self, value):
		self._value = value
		self._type = type(value)

	def set (self, value):
		raise NotImplementedError

	def _push (self, value):
		raise NotImplementedError

	def get (self, start, interval = None):
		start, interval = _prepare(start, interval)

		if interval == 0:
			return self._value

		return [
			(start, self._value), 
			(start + interval, self._value)
		]

	def serialize (self):
		return str(self._value)


class Expression (BaseVariable):
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
