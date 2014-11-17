from twisted.internet import defer
from twisted.trial import unittest

from mock import Mock

from .. import data

class UtilsTestCase (unittest.TestCase):
	def setUp (self):
		self.x = [x for x in range(1, 5)]
		self.y = [x * 2 for x in self.x]
		self.min_x = min(self.x)
		self.max_x = max(self.x)

	def test_bounds (self):
		self.assertEqual(data._upper_bound(self.x, 2), 1)
		self.assertEqual(data._upper_bound(self.x, 3.5), 3)
		self.assertEqual(data._lower_bound(self.x, 3.5), 2)
		self.assertEqual(data._lower_bound(self.x, 4), 3)

	def test_get (self):
		# Get all data
		self.assertEqual(
			data._get(self.x, self.y, self.max_x, self.min_x, None, None), 
			zip(self.x, self.y)
		)

		# Zero interval
		for i in range(self.min_x - 2, self.max_x + 2):
			self.assertEqual(
				len(data._get(self.x, self.y, self.max_x, self.min_x, i, None)), 
				1
			)

		tests = [
			(-2, 1, [(-2, 2), (-1, 2)]),
			(-2, 2, [(-2, 2), (0, 2)]),
			(-2, 3, [(-2, 2), (1, 2)]),
			(-2, 4, [(-2, 2), (1, 2), (2, 4)]),
			(-2, 8, [(-2, 2), (1, 2), (2, 4), (3, 6), (4, 8), (6, 8)]),
			( 1, 8, [(1, 2), (2, 4), (3, 6), (4, 8), (9, 8)]),
			( 1, 2, [(1, 2), (2, 4), (3, 6)]),
			( 3, 1, [(3, 6), (4, 8)]),
			( 3, 2, [(3, 6), (4, 8), (5, 8)]),
			( 3, 8, [(3, 6), (4, 8), (11, 8)])
		]
		for start, interval, expected in tests:
			self.assertEqual(data._get(self.x, self.y, self.max_x, self.min_x, start, interval), expected)

		
class VariablesTestCase (unittest.TestCase):
	def setUp (self):
		self.v = data.Variable(int, 2)

	def test_create (self):
		self.assertEqual(self.v.type, int)
		self.assertEqual(self.v.value, 2)

	def test_events (self):
		cleared = Mock()
		changed = Mock()

		self.v.on("change", changed)
		self.v.on("clear", cleared)

		self.v.set(3)
		self.assertEqual(changed.called, True)

		self.v.truncate()
		self.assertEqual(cleared.called, True)
		self.assertEqual(self.v.value, 3)

	def test_update (self):
		self.v._archive.min_delta = 0
		self.v.set(3)
		self.v.set(4)
		self.v.set(5)
		self.assertEqual(self.v._y, [2, 3, 4, 5])
		self.assertEqual([y for x, y in self.v.get()], [2, 3, 4, 5])

	def test_get (self):
		v = data.Variable(int)
		v._archive.min_delta = 0
		v._push(2, 1)
		v._push(3, 2)
		v._push(4, 3)
		v._push(5, 4)
		self.assertEqual(v._x, [1, 2, 3, 4])
		self.assertEqual(v._y, [2, 3, 4, 5])
		self.assertEqual(v.get(2, 1), [(2, 3), (3, 4)])

class ExpressionsTestCase (unittest.TestCase):
	def setUp (self):
		self.v = data.Variable(int, 2)

	def test_create (self):
		add = self.v + 2
		self.assertEqual(add.type, int)
		self.assertEqual(add.value, 4)
		self.assertEqual(add.__class__.__name__, "AddExpression")
		self.assertIn(add._changed, self.v._events["change"])

	def test_propagate (self):		
		self.v._archive.min_delta = 0
		add = self.v + 2

		changed = Mock()
		add.on("change", changed)

		self.v.set(4)
		self.assertEqual(changed.called, True)

		self.assertEqual(add.value, 6)

