from twisted.internet import defer
from twisted.trial import unittest

from mock import Mock

from octopus.constants import State
from octopus.sequence import IfStep
from octopus import sequence

def simple_step ():
	d = defer.Deferred()
	step = Mock()
	step.run = Mock(return_value = d)
	step.duration = 10
	
	return d, step

class IfStepTestCase (unittest.TestCase):

	def test_serialize (self):
		pass

	def test_true (self):
		dt, if_true = simple_step()
		df, if_false = simple_step()

		s = IfStep(True, if_true, if_false)
		self.assertEqual(s.state, State.READY)
		
		d = s.run()
		self.assertEqual(s.state, State.RUNNING)

		result = "my_result"
		dt.callback(result)

		if_true.assert_called_once_with()
		self.assertEqual(s.state, State.COMPLETE)
		self.assertEqual(d.called, True)
		self.assertEqual(d.result, result)
		self.assertEqual(if_false.call_args_list, [])

	def test_true_error (self):
		dt, if_true = simple_step()
		df, if_false = simple_step()

		s = IfStep(True, if_true, if_false)
		d = s.run()

		result = "my_failure"
		dt.errback(result)

		self.assertEqual(s.state, State.ERROR)
		self.assertEqual(d.called, True)
		self.assertEqual(d.result, result)
		self.assertEqual(if_false.call_args_list, [])

	def test_false (self):
		dt, if_true = simple_step()
		df, if_false = simple_step()

		s = IfStep(False, if_true, if_false)
		self.assertEqual(s.state, State.RUNNING)
		d = s.run()

		result = "my_result"
		df.callback(result)

		self.assertEqual(s.state, State.COMPLETE)
		self.assertEqual(d.called, True)
		self.assertEqual(d.result, result)
		if_false.assert_called_once_with())
		self.assertEqual(if_true.call_args_list, [])

	def test_false_error (self):
		dt, if_true = simple_step()
		df, if_false = simple_step()

		s = IfStep(False, if_true, if_false)
		d = s.run()

		result = "my_failure"
		df.errback(result)

		self.assertEqual(s.state, State.ERROR)
		self.assertEqual(d.called, True)
		self.assertEqual(d.result, result)
		self.assertEqual(if_true.call_args_list, [])
		
	def test_reset (self):
		dt, if_true = simple_step()
		df, if_false = simple_step()

		# Run the step
		s = IfStep(True, if_true, if_false)
		d = s.run()
	
		# Run the step again?
		self.assertRaises(sequence.AlreadyRunning, s.run)

		# Finish and reset the step
		dt.callback("my_old_result")
		s.reset()
		self.assertEqual(s.state, State.READY)
		if_true.reset.assert_called_once_with()
		if_false.reset.assert_called_once_with()

		# Run the step again
		dt = defer.Deferred()
		if_true.run.return_value = dt

		d = s.run()
		self.assertEqual(s.state, State.RUNNING)
		self.assertEqual(len(if_true.call_args_list), 2)
		
		# Finish the step
		result = "my_new_result"
		df.callback(result)
		self.assertEqual(d.called, True)
		self.assertEqual(d.result, result)
		self.assertEqual(if_false.call_args_list, [])

	def test_pause_resume_cancel (self):
		dt, if_true = simple_step()
		df, if_false = simple_step()

		# Run the step
		s = IfStep(True, if_true, if_false)
		self.assertRaises(sequence.NotRunning, s.pause)
		d = s.run()

		# Pause the step
		self.assertRaises(sequence.NotPaused, s.resume)
		s.pause()
		self.assertEqual(s.state, State.PAUSED)

		# Pause the step
		self.assertRaises(sequence.NotRunning, s.pause)
		s.resume()
		self.assertEqual(s.state, State.RUNNING)

		# Cancel the step
		self.assertRaises(sequence.Stopped, s.cancel)
		self.assertEqual(s.state, State.CANCELLED

		s.reset()
		self.assertEqual(s.state, State.READY)

		if_true.pause.assert_called_once_with()
		if_false.pause.assert_called_once_with()	
		if_true.resume.assert_called_once_with()
		if_false.resume.assert_called_once_with()
		if_true.cancel.assert_called_once_with()
		if_false.cancel.assert_called_once_with()
		if_true.reset.assert_called_once_with()
		if_false.reset.assert_called_once_with()
