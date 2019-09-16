from twisted.internet import defer
from twisted.trial import unittest

from mock import Mock

from .. import sequence, util, control
from ...data import data

class BindTestCase (unittest.TestCase):
	def test_boundVariable (self):
		v = data.Variable(int, 0)
		d = data.Variable(bool, False)

		s = sequence.Sequence([
			sequence.LogStep("Running"),
			sequence.WhileStep(v < 10, [
				sequence.SetStep(v, v + 1),
				sequence.LogStep("v = " + v + "; d = " + d),
				sequence.WaitStep(0.2),
			]),
			sequence.LogStep("Complete"),
		])

		d_ctrl = control.Bind(d, v, lambda x: x > 5)
		s.dependents.add(d_ctrl)

		messages = []

		@s.on("log")
		def onLog (data):
			messages.append(data['message'])

		def test (result):
			self.assertEqual(messages, [
				'Running', 
				'v = 1; d = False', 
				'v = 2; d = False', 
				'v = 3; d = False', 
				'v = 4; d = False', 
				'v = 5; d = False', 
				'v = 6; d = True', 
				'v = 7; d = True', 
				'v = 8; d = True', 
				'v = 9; d = True', 
				'v = 10; d = True', 
				'Complete'
			])

		return s.run().addCallback(test)
