# System Imports
from collections import OrderedDict, defaultdict

# Sibling Imports
from ..util import Event, now


__all__ = ["InterfaceSection", "InterfaceSectionSet", "Trace", "Property"]

TRACE_TIME = 60

_alias_counters = defaultdict(lambda: 0)
def _alias (name):
	_alias_counters[name] += 1
	return "{:s}{:d}".format(name, _alias_counters[name])

class InterfaceSection (object):
	def __init__ (self, items = None, title = "", name = None):
		self.name = name or title
		self.title = title
		self.items = items or []

		self.map = {}
		for i in items:
			self.map[i.name] = i

	def __getitem__ (self, key):
		if key in ("name", "title", "properties", "traces"):
			return getattr(self, key)
		else:
			raise KeyError

	def output (self):
		return {
			"name": self.name,
			"title": self.title,
			"items": [i.serialize() for i in self.items]
		}


class InterfaceSectionSet (OrderedDict):

	event = Event()
	
	def __init__ (self, *args, **kwargs):
		OrderedDict.__init__(self, *args, **kwargs)

		self.controls   = {}
		self.properties = {}

	def __setitem__ (self, name, section):
		assert(isinstance(section, InterfaceSection))

		if name in self:
			self._delitem(name)

		section.name = name
		OrderedDict.__setitem__(self, name, section)

		for p in section.properties:
			self.properties[p.alias] = p

		for t in section.traces.itervalues():
			for s in t["traces"]:
				self.properties[s.alias] = s

	def __delitem__ (self, name):
		self._delitem(name)
		OrderedDict.__delitem__(self, name)

	def _delitem (self, name):
		section = self[name]

		for p in section.properties:
			del self.properties[p.alias]

		for t in section.traces.itervalues():
			for s in t["traces"]:
				try:
					del self.properties[s.alias]
				except NameError:
					pass

	def output (self):
		return [x.output() for x in self.itervalues()]

	def remove_listeners (self):
		for c in self.controls.itervalues():
			c.event -= self.event


def fromDict (dict):
	section = InterfaceSection()
	try:
		for trace in dict["traces"]:
			Trace(trace)
			
	except (KeyError, TypeError):
		pass
		
	

class Trace (object):
	title = None
	colours = None
	variables = None
	mintime = 60
	maxtime = TRACE_TIME

	def __init__ (self, **kwargs):
		self.name = _alias("t")

		for key, value in kwargs.iteritems():
			if hasattr(self, key):
				setattr(self, key, value)

	def serialize (self):
		interval = self.maxtime
		start = now() - interval
		colours = iter(self.colours) if self.colours is not None else None
		
		def compress (point):
			try:
				return (round(point[0] - start, 1), round(point[1], 2))
			except TypeError:
				return 0

		def variable (t):
			r = {
				"name":  t.alias,
				"title": t.title if hasattr(t, "title") else "",
				"unit":  t.unit if hasattr(t, "unit") else "",
				"zero": round(start, 1),
				"max": round(interval, 1),
				"data": map(compress, t.get(-interval))
			}

			if colours is not None:
				r["colour"] = colours.next()

			return r

		return {
			"name": self.name,
			"title": self.title,
			"streams": [variable(v) for v in self.variables],
			"min_display_time": self.mintime,
			"max_display_time": self.maxtime
		}


class Property (object):
	def __init__ (self, variable):
		self.name = variable.alias
		self.variable = variable

	def serialize (self):
		p = self.variable

		result = {
			"name":  p.alias,
			"title": p.title if hasattr(p, "title") else "",
			"unit":  p.unit if hasattr(p, "unit") else "",
			"type":  p.type.__name__,
			"value": p.value
		}

		if not p.immutable:
			result["edit"] = True
			result["disabled"] = False

			if p.type in (int, float, long):
				type = "number"
			elif p.type is boolean:
				type = "switch"
			elif p.type is str:
				type = "string"

			if hasattr(p, "min") and p.min is not None:
				result["min"] = p.min
			if hasattr(p, "max") and p.max is not None:
				result["max"] = p.max
			if hasattr(p, "options") and p.options is not None:
				result["options"] = p.options
				type = "select"

			result["control_type"] = type

		else:
			result["edit"] = False

		return result

class Image (Property):
	def serialize (self):
		p = self.variable
		return {
			"name":  p.alias,
			"title": p.title,
			"value": p.value,
			"type":  "image",
			"edit":  False
		}

class Button (object):
	"""A push button control (not associated with a variable)."""

	type = "button"

	action = None
	"""A function to perform when the button is pressed."""

	args = []
	"""Arguments to be passed to the action function when it is called."""

	kwargs = {}
	"""Keywords to be passed to the action function when it is called."""

	def __init__ (self, title, action = None, *args, **kwargs):
		self.name = _alias("b")

		self.title = title
		self.action = action
		self.args = args
		self.kwargs = kwargs

	def serialize (self):
		return {
			"name": self.name,
			"title": self.title,
			"disabled": False
		}

	def update (self, value):
		try:
			if not self._disabled:
				return self.action(*self.args, **self.kwargs)
		except TypeError:
			pass