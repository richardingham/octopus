# System Imports
from math import ceil
import operator

# Package Imports
from ..util import now, timerange, EventEmitter

# Sibling Imports
import errors


def _upper_bound (list, time):
	# Return the index of the first item in {list} which
	# is greater than or equal to {time}.
	# http://stackoverflow.com/q/2236906/
	return next((i for i, t in enumerate(list) if t >= time), None)


def _lower_bound (list, time):
	l = len(list)

	# Return the index of the last item in {list} which
	# is less than or equal to {time}.
	try:
		return l - 1 - next(
			(i for i, t in enumerate(reversed(list)) if t <= time)
		)
	except StopIteration:
		return None


def _interp (x, x0, y0, x1, y1):
	try:
		return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
	except ZeroDivisionError:
		return y1


def _prepare (start, interval):
	if interval is not None and interval < 0:
		interval = 0

	if start is not None:
		if start < 0:
			start = now() + start

		if interval is None:
			interval = now() - start

	return start, interval


def _get (x_vals, y_vals, x_max, x_min, start, interval):

	# Return all data
	if start is None and interval is None:
		return zip(x_vals, y_vals)

	if interval is None:
		interval = 0

	# Request range is outside data range
	if start > x_max:
		if interval is 0:
			return [(start, y_vals[-1])]
		else:
			return [(start, y_vals[-1]), (start + interval, y_vals[-1])]
	if start + interval < x_min:
		try:
			if interval is 0:
				return [(start, y_vals[0])]
			else:
				return [(start, y_vals[0]), (start + interval, y_vals[0])]
		except IndexError:
			if interval is 0:
				return [(start, 0)]
			else:
				return [(start, 0), (start + interval, 0)]

	# Collect data from archive
	i_start = _lower_bound(x_vals, start)
	i_end   = _upper_bound(x_vals, start + interval)

	if i_end is not None:
		i_end += 1 # Return the interval length of data

	vals = zip(x_vals[i_start:i_end], y_vals[i_start:i_end])

	# Fill in the start and end points if necessary.
	try:
		if start < x_min:
			vals.insert(0, (start, y_vals[0]))
	except IndexError:
		pass

	try:
		if start + interval > x_max:
			vals.append((start + interval, y_vals[-1]))
	except IndexError:
		pass

	return vals


def _at (val, time):
	if len(val) is 1:
		return val[0][1]
	elif len(val) is 0:
		return 0
	else:
		a, b = val[0:2]
		return _interp(time, a[0], a[1], b[0], b[1])


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

	def get (self, start = None, interval = None):
		start, interval = _prepare(start, interval)

		# Nothing in archive
		if self._prev_x is None:
			return []

		return _get(self._x, self._y, self._prev_x, self._x[0], start, interval)

	def at (self, time):
		val = self.get(time, 0)

		if len(val) is 0:
			return ""
		else:
			return val[0][1]


class StringArchive (Archive):

	def __init__ (self, variable):
		Archive.__init__(self)
		self._variable = variable

	def push (self, x, y):
		pass

	def at (self, time):
		return "StringArchive.at not implemented" # _at(self.get(time, 0), time)


_default_alias_counters = {}
def _default_alias (object):
	class_name = object.__class__.__name__

	if class_name not in _default_alias_counters:
		_default_alias_counters[class_name] = 1
	else:
		_default_alias_counters[class_name] += 1
	
	return "{:s}_{:d}".format(class_name, _default_alias_counters[class_name])


class BaseVariable (EventEmitter):
	alias = ""

	@property
	def value (self):
		try:
			return self._value
		except AttributeError:
			return None

	@property
	def type (self):
		try:
			return self._type
		except AttributeError:
			return type(None)

	def get_value (self):
		return self._value

	def __str__ (self):
		return str(self.get_value())

	def __int__ (self):
		return int(self.get_value())

	def __float__ (self):
		return float(self.get_value())

	def __nonzero__ (self):
		return bool(self.get_value())

	def __repr__ (self):
		return "<{class_name} at Ox{reference:x}: {var_alias} ({var_type}) = {var_value}>".format(
			class_name = self.__class__.__name__, 
			reference = id(self),
			var_alias = self.alias,
            var_type = self.type.__name__,
			var_value = self.value
		)


class Variable (BaseVariable):
	length = 30 # in seconds
	
	def __init__ (self, type, value = None):
		self.alias = _default_alias(self)

		self._time = None
		self._value = None
		self._type = type

		self._x = []
		self._y = []

		if type in (int, float, long, complex):
			self._archive = Archive()
		else:
			self._archive = StringArchive(self)

		self._log_file = None

		if value is not None:
			self._push(value)

	def truncate (self):
		"""
		Empty the variable of all stored data.
		"""

		if self._value is None:
			self._x = []
			self._y = []
		else:
			self._time = now()

			self._x = [self._time]
			self._y = [self._value]

		self._archive.truncate()

		# Trigger clear event
		self.emit("clear", time = self._time, value = self._value)

	def set (self, value):
		self._push(value)

	def get (self, start = None, interval = None):	
		"""
		Returns the value of the variable over a particular time period.

		Returns a list of (time, value) pairs between 
		[time = start and time = start + interval] (inclusive).

		start: earliest time to return data.
		interval: time-span requested.

		If interval = None, then data are returned from start
		up to the current time.

		If start < 0, then this number of seconds is subtracted
		from the current time.
		"""

		if start is None and interval is None:
			return self._archive.get()

		if start < self._x[0]:
			return self._archive.get(start, interval)

		start, interval = _prepare(start, interval)

		return _get(self._x, self._y, self._time, self._x[0], start, interval)

	def at (self, time):
		return _at(self.get(time, 0), time)

	def _push (self, value, time = None):
		if value is None:
			return

		if type(value) != self._type:
			value = self._type(value)

		if time is None:
			time = now()
		elif time < self._time:
			raise Exception("Cannot insert values earlier than latest value")

		# Only store changes
		if self._value == value \
		and len(self._x) > 2 \
		and self._y[-2] == value:
			self._x[-1] = time
			changed = False
		else:
			self._x.append(time)
			self._y.append(value)

			changed = True

			# Trim old data
			mid = len(self._x) / 2
			if time - self._x[mid] > self.length:
				self._y = self._y[mid:]
				self._x = self._x[mid:] 

		self._value = value
		self._time  = time

		self._archive.push(time, value)
		self._log(time, value)
		
		# Trigger change event
		if changed:
			self.emit("change", time = time, value = value)

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

	def get (self, start, interval = None):
		start, interval = _prepare(start, interval)

		if interval == 0:
			return [(start, self._value)]

		return [
			(start, self._value), 
			(start + interval, self._value)
		]

	def at (self, time):
		return self._value

	def serialize (self):
		return str(self._value)


class Expression (BaseVariable):
	pass

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
	(" & ", operator.__and__), (" | ", operator.__or__),
	(" and ", lambda a, b: a and b), (" or ", lambda a, b: a or b),
)

# http://stackoverflow.com/questions/100003/what-is-a-metaclass-in-python/6581949#6581949
def _def_binary_op (symbol, operatorFn):
	if symbol in (" and ", " or "):
		clsName = symbol[1:-1].capitalize() + "Expression"
		attrName = symbol[1:-1]
		rattrName = None
	else:
		if operatorFn in (operator.__and__, operator.__or__):
			clsName = "Bitwise" + operatorFn.__name__[2:-2].capitalize() + "Expression"
		else:
			clsName = operatorFn.__name__[2:-2].capitalize() + "Expression"
		attrName = operatorFn.__name__
		rattrName = "__r" + operatorFn.__name__[2:]
	
	def init (self, lhs, rhs):
		self.alias = _default_alias(self)

		self._archive_x = None
		self._archive_y = None

		lhs = lhs if isinstance(lhs, BaseVariable) else Constant(lhs)
		rhs = rhs if isinstance(rhs, BaseVariable) else Constant(rhs)
		self._lhs = lhs
		self._rhs = rhs

		if lhs.value is not None and rhs.value is not None:
			try:
				self._value = operatorFn(lhs.value, rhs.value)
			except TypeError:
				if lhs.type is str or rhs.type is str:
					self._value = operatorFn(str(lhs.value), str(rhs.value))
				else:
					raise

			self._type = type(self._value)
		else:
			self._value = None
			self._type = None

		lhs.on("change", self._changed)
		rhs.on("change", self._changed)

	def _changed (self, data):
		try:
			self._value = operatorFn(self._lhs.value, self._rhs.value)
		except TypeError:
			if self._lhs.type is str or self._rhs.type is str:
				self._value = operatorFn(str(self._lhs.value), str(self._rhs.value))
			else:
				raise

		if self._archive_x is not None:
			self._archive_x.append(data['time'])
			self._archive_y.append(self._value)

		self.emit("change", time = data['time'], value = self._value)

	def get_type (self):
		if self._type is None and self._value is not None:
			self._type = type(self._value)

		return self._type
	
	def get (self, start = None, interval = None):
		if self._archive_x is None:
			self.get_archive()

		return _get(self._archive_x, self._archive_y, self._archive_x[-1], self._archive_x[0], start, interval)

	def at (self, time):
		return _at(self.get(time, 0), time)

	def get_archive (self, store = True):
		if self._archive_x is not None:
			return zip(self._archive_x, self._archive_y)

		x = []
		y = []

		try:
			lhsa = self._lhs.get_archive(store = False)
		except AttributeError:
			lhsa = self._lhs.get()

		try:
			rhsa = self._rhs.get_archive(store = False)
		except AttributeError:
			rhsa = self._rhs.get()

		if self._lhs.type is str or self._rhs.type is str:
			def op (l, r):
				return operatorFn(l, r)
		else:
			def op (l, r):
				return operatorFn(str(l), str(r))

		r_max = len(rhsa)
		l_max = len(rhsa)
		r_i = l_i = 0

		while r_i < r_max and l_i < l_max:
			l_t, c_l = lhs[l_i]

			while rhs[r_i][0] < l_t:
				x.append(rhs[r_i][0])
				y.append(op(c_l, rhs[r_i][0]))
				r_i += 1

			r_t, c_r = rhs[r_i]

			while lhs[r_i][0] < r_t:
				x.append(rhs[l_i][0])
				y.append(op(lhs[l_i][0], c_r))
				l_i += 1

		if store:
			self._archive_x = x
			self._archive_y = y

		return zip(x, y)
		
	def serialize (self):
		return "(" + \
			self._lhs.serialize() + symbol \
			+ self._rhs.serialize() + ")"

	cls = type(
		clsName, 
		(Expression,), 
		{ 
			"__init__": init,
			"type": property(get_type),
			"serialize": serialize,
			"_changed": _changed,
			"get_archive": get_archive,
			"get": get,
			"at": at
		}
	)

	def op_fn (self, other):
		return cls(self, other)

	def op_rfn (self, other):
		return cls(other, self)

	setattr(BaseVariable, attrName, op_fn)

	if rattrName is not None:
		setattr(BaseVariable, rattrName, op_rfn)

def _def_unary_op (symbol, operatorFn):
	def init (self, operand):
		self.alias = _default_alias(self)

		self._operand = operand

		if operand.value is not None:
			self._value = operatorFn(operand.value)
			self._type = type(self._value)
		else:
			self._value = None
			self._type = None

		operand.on("change", self._changed)

	def _changed (self, data):
		self._value = operatorFn(self._operand.value)
		self.emit("change", time = data['time'], value = self._value)

	def get_type (self):
		if self._type is None and self._value is not None:
			self._type = type(self._value)

		return self._type
	
	def get (self, start = None, interval = None):
		if self._archive_x is None:
			self.get_archive()

		return _get(self._archive_x, self._archive_y, self._archive_x[-1], self._archive_x[0], start, interval)
	
	def at (self, time):
		return _at(self.get(time, 0), time)

	def get_archive (self, store = True):
		if self._archive_x is not None:
			return zip(self._archive_x, self._archive_y)

		x = []
		y = []

		try:
			opa = self._operand.get_archive(store = False)
		except AttributeError:
			opa = self._operand.get()

		for o_x, o_y in opa:
			x.append(o_x)
			y.append(operatorFn(o_y))

		if store:
			self._archive_x = x
			self._archive_y = y

		return zip(x, y)

	def serialize (self):
		return symbol + self._operand.serialize()

	cls = type(
		op.__name__[2:-2].capitalize() + "Expression", 
		(Expression,), 
		{ 
			"__init__": init,
			"type": property(get_type),
			"serialize": serialize,
			"_changed": _changed,
			"get_archive": get_archive,
			"get": get,
			"at": at
		}
	)

	def op_fn (self, other):
		return cls(self, op)

	setattr(BaseVariable, op.__name__, op_fn)

[_def_unary_op(symbol, op) for symbol, op in _unary_ops]
[_def_binary_op(symbol, op) for symbol, op in _binary_ops]

