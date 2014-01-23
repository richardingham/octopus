
def names (layout_name, rack):
	return ["{:s}:{:d}".format(layout_name, i) for i in rack.vials()]

class OutOfRange (Exception):
	pass

class Layout (object):
	name = "Layout"

	def __init__ (self, **kwargs):
		for k, v in kwargs.iteritems():
			if hasattr (self, k):
				setattr(self, k, v)

	def xyz (self, i):
		raise NotImplemented

	def vials (self):
		raise NotImplemented

class NullLayout (Layout):
	def xyz (self, i):
		return (0, 0, 0)

	def vials (self):
		return []

class GridLayout (Layout):
	z_down = 0

	x_count = 1

	x_zero = 0
	y_zero = 0

	dx = 1
	dy = 1

	max = 50

	def xyz (self, i):
		if i > self.max or x < 1:
			raise OutOfRange
		
		x = self.x_zero + (i % self.x_count) * self.dx
		y = self.y_zero + (i // self.x_count) * self.dy

		return (x, y, self.z_down)

	def vials (self):
		return range(1, 1 + max)

grid_layout_50 = GridLayout(name = "10x5", z_up = 0, z_down = 500, x_count = 10, x_zero = 100, y_zero = 100, dx = 100, dy = 100)

class WasteBeaker (Layout):
	def xyz (self, i):
		if i == 1:
			return (1740, 2550, 0)
		else:
			return (0, 0, 0)

def fourteen_vial_rack (position, for_injection = False):
	if not 0 < position < 6:
		raise OutOfRange(position)

	layout = Layout()
	layout.name = "14 Vial Rack, position " + str(position)

	x_zero = 140 + 800 * (position - 1)
	y_zero = 900
	dx = dy = 300

	def xyz (i):
		i = 15 - int(i)
		z = 0

		if 0 < i < 8:
			x = x_zero + dx
			y = y_zero + ((7 - i) * dy)
		elif i < 15:
			x = x_zero
			y = y_zero + ((i - 8) * dy)
		else:
			raise OutOfRange(i)

		if for_injection:
			x += 100
			z += 600

		return (x, y, z)

	def vials ():
		return range(1, 15)

	layout.xyz = xyz
	layout.vials = vials

	return layout
