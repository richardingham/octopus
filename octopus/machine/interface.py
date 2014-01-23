# System Imports
from collections import OrderedDict

# Sibling Imports
from ..util import Event, now


__all__ = ["InterfaceSection", "InterfaceSectionSet", "Trace", "Property"]

TRACE_TIME = 60


def _prop (p):
	result = {
		"name":  p.alias,
		"title": p.title if hasattr(p, "title") else "",
		"unit":  p.unit if hasattr(p, "unit") else "",
		"type":  p.type.__name__,
		"value": p.value
	}

	return result

def _img (p):
	result = {
		"name":  p.alias,
		"title": p.title,
		"value": p.value
	}

	return result

def _trace (t):
	if "colours" not in t or len(t["colours"]) < len(t["traces"]):
		colours = None # generate_colours(len(t["traces"]))
	else:
		colours = iter(t["colours"])

	interval = t["maxtime"] if "maxtime" in t else TRACE_TIME
	start = now() - interval
	
	def compress (point):
		try:
			return (round(point[0] - start, 1), round(point[1], 2))
		except TypeError:
			return 0

	def _trace (t):
		r = _prop(t)
		r["zero"] = round(start, 1)
		r["max"] = round(interval, 1)
		r["data"] = map(compress, t.get(-interval))
		if colours is not None:
			r["colour"] = colours.next()

		return r

	return {
		"title": t["title"],
		"streams": [_trace(x) for x in t["traces"]],
		"unit": t["unit"],
		"min_display_time": t["mintime"] if "mintime" in t else 60,
		"max_display_time": interval
	}

def _control (c):
	result = {
		"name":     c.alias,
		"type":     c.type,
		"title":    c.title,
		"value":    c.value,
		"unit":     c.unit,
		"variable": c.var_alias
	}

	for key in ("min", "max", "options"):
		if hasattr(c, key):
			result[key] = getattr(c, key)

	return result

class InterfaceSection (object):
	def __init__ (self, properties = None, traces = None, controls = None, title = "", name = None):
		self.name = name or title
		self.title = title
		self.properties = properties or []
		self.controls = controls or []
		self.traces = OrderedDict()

		if traces is not None:
			for t in traces:
				try:
					self.traces[t["name"]] = t
				except KeyError:
					self.traces[t["title"]] = t

	def __getitem__ (self, key):
		if key in ("name", "title", "properties", "controls", "traces"):
			return getattr(self, key)
		else:
			raise KeyError

	def output (self):
		return {
			"name": self.name,
			"title": self.title,
			"traces": [_trace(t) for t in self.traces.itervalues()],
			"properties": [_prop(p) for p in self.properties if p.type not in ("Image",)],
			"images": [_img(p) for p in self.properties if p.type == "Image"],
			"controls": [_control(c) for c in self.controls]
		}


class InterfaceSectionSet (OrderedDict):

	trace_time = 30

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

		for c in section.controls:
			self.controls[c.alias] = c
			c.event += self.event

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

		for c in section.controls:
			del self.controls[p.alias]
			c.event -= self.event

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


class Trace (object):
	pass


class Property (object):
	pass

