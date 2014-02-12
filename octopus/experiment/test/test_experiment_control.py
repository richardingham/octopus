from twisted.internet import defer, reactor
from twisted.trial import unittest

from mock import Mock

from octopus.experiment import Experiment
from octopus.constants import State

def simple_step ():
	from octopus.sequence import Step
	from octopus.util import Event

	d = defer.Deferred()
	step = Mock(spec = Step)
	step.run = Mock(return_value = d)

	ok = defer.succeed(None)
	step.reset = Mock(return_value = ok)
	step.pause = Mock(return_value = ok)
	step.resume = Mock(return_value = ok)
	step.cancel = Mock(return_value = ok)
	step.abort = Mock(return_value = ok)

	step.event = Event()
	step.log = Event()

	step.duration = 10
	
	return d, step

def simple_machine ():
	from octopus.machine import Machine
	from octopus.machine.interface import InterfaceSection

	machine = Mock(spec = Machine)
	machine.ui = InterfaceSection()

	ok = defer.succeed(None)
	machine.ready = defer.Deferred()
	machine.reset_d = defer.Deferred()
	machine.pause_d = defer.Deferred()
	machine.resume_d = defer.Deferred()
	machine.run = Mock(return_value = ok)
	machine.reset = Mock(return_value = machine.reset_d)
	machine.pause = Mock(return_value = machine.pause_d)
	machine.resume = Mock(return_value = machine.resume_d)

	machine.variables = {}

	return machine

def simple_sequence ():
	from octopus.sequence import Sequence, Step

	steps = [
		Step(),
		Step(),
		Step()
	]
	seq = Sequence(steps)

	return seq, steps

class ExperimentInitCase (unittest.TestCase):
	
	def test_create (self):
		expt_a = Experiment()
		self.assertEqual(expt_a.step, None)

		step_d, step = simple_step()
		expt_b = Experiment(step)
		self.assertEqual(expt_b.step, step)


class ExperimentMachinesCase (unittest.TestCase):
	
	def test_run (self):
		m = simple_machine()
		step_d, step = simple_step()

		expt = Experiment(step)
		expt.register_machine(m)

		expt.run()
		self.assertEqual(expt.state, State.RUNNING)
		self.assertEqual(m.reset.call_count, 0)

		m.ready.callback(True)
		m.reset.assert_called_once_with()
		self.assertEqual(step.run.call_count, 0)

		m.reset_d.callback(True)
		step.run.assert_called_once_with()

		step_d.callback(None)


class ExperimentControlCase (unittest.TestCase):

	def test_normal_run (self):
		step_d, step = simple_step()

		# Initialisation
		expt = Experiment(step)
		self.assertEqual(expt.state, State.READY)

		# Run
		expt_d = expt.run()
		self.assertEqual(expt.state, State.RUNNING)
		step.run.assert_called_once_with()

		result = "my_result"
		step_d.callback(result)

		self.assertEqual(expt.state, State.COMPLETE)
		self.assertEqual(expt_d.called, True)

	def test_double_run (self):
		step_d, step = simple_step()

		# Initialisation
		expt = Experiment(step)

		# Run twice gives an error
		expt_d = expt.run()
		self.assertRaises(Exception, expt.run)

		step_d.callback(None)

	def test_pause_resume (self):
		# Initialisation
		step_d, step = simple_step()
		expt = Experiment(step)
		expt_d = expt.run()

		# Pause
		pause_d = expt.pause()
		step.pause.assert_called_once_with()
		self.assertEqual(expt.state, State.PAUSED)
		self.assertEqual(pause_d.result, [None])

		# Resume
		resume_d = expt.resume()
		step.resume.assert_called_once_with()
		self.assertEqual(expt.state, State.RUNNING)
		self.assertEqual(resume_d.result, [None])

		step_d.callback(None)

	def test_stop (self):
		from octopus.sequence import Stopped

		# Initialisation
		step_d, step = simple_step()
		expt = Experiment(step)
		expt_d = expt.run()

		# Stop
		self.assertEqual(expt.state, State.RUNNING)

		stop_d = expt.stop()
		step.abort.assert_called_once_with()
		self.assertEqual(expt.state, State.RUNNING)

		step_d.errback(Stopped())
		self.assertEqual(expt.state, State.ERROR)
		self.assertFailure(expt_d, Stopped)
		self.assertEqual(len(step.log.handlers), 0)


