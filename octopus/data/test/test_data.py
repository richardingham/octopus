from twisted.internet import defer
from twisted.trial import unittest

from mock import Mock

from octopus.data import data

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
		self.v.set(3)
		self.v.set(4)
		self.v.set(5)
		self.assertEqual(self.v._y, [2, 3, 4, 5])
		self.assertEqual([y for x, y in self.v.get()], [2, 3, 4, 5])

	def test_get (self):
		self.v.truncate()
		self.v._push(1, 2)
		self.v._push(2, 3)
		self.v._push(3, 4)
		self.v._push(4, 5)
		self.assertEqual(self.v._x, [2, 3, 4, 5])
		self.assertEqual(self.v._y, [2, 3, 4, 5])
		self.assertEqual(self.v.get(2, 1), [3, 4])

class ExpressionsTestCase (unittest.TestCase):
	def setUp (self):
		self.v = data.Variable(int, 2)

	def test_create (self):
		add = self.v + 2
		self.assertEqual(add.type, int)
		self.assertEqual(add.value, 4)
		self.assertEqual(add.__class__.__name__, "AddExpression")
		self.assertIn(add._changed, v._events["change"])

	def test_propagate (self):		
		add = self.v + 2
		self.v.set(4)
		self.assertEqual(a.value, 6)

