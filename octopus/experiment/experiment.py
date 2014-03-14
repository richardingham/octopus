# Twisted Imports
from twisted.internet import reactor, defer
from twisted.python import log

# System Imports
import os
import re
import logging
from collections import deque

# Sibling Imports
from .. import data
from .. import sequence
from .. import util
from ..machine import Machine, Component
from ..machine.interface import InterfaceSection, InterfaceSectionSet
from ..constants import Event, State

from marshal import Marshal

class LogFile (object):

	@classmethod
	def get_dir (cls, name):
		cwd = os.getcwd()
		counter = 1

		if os.path.isdir(os.path.join(cwd, name)):
			while os.path.isdir(os.path.join(cwd, name + "." + str(counter))):
				counter += 1
			name = name + "." + str(counter)

		os.mkdir(os.path.join(cwd, name))

		return name

	def __init__ (self, output_name, var_name, time_zero):
		self.f = open(os.path.join(os.getcwd(), output_name, var_name + ".csv"), "w+")
		self.time_zero = time_zero

	def write (self, time, value):
		self.f.write("{:.2f},{:.2f},{}\n".format(time, time - self.time_zero, value))

	def close (self):
		self.f.close()


class Timer (data.Variable):
	def __init__ (self):
		self.time_zero = util.now()

	def get_value (self):
		return self._value
	value = property(get_value)


class Experiment (object):

	title = "Untitled Experiment"
	default_log_output = "main"

	@property
	def id (self):
		return self._id

	@id.setter
	def id (self, value):
		if self._id is not None:
			raise ValueError("ID has already been set")

		if not re.match(r'^[a-zA-Z0-9\-\_]+$', value):
			raise ValueError("ID can only contain alphanumeric characters, _ and -")

		self._id = value
		self._log("ID set", logging.DEBUG)

		self.id_set(self, value)

	@property
	def state (self):
		return self._state

	@state.setter
	def state (self, value):
		self._state = value
		self.marshal.event(Event.EXPERIMENT, { "state": value.value })

		try:
			# todo... collect in a list to write later.
			self._event_log.write(util.now(), "expt-state:%s" % value.value)
		except AttributeError:
			pass

	@property
	def marshal (self):
		return self._marshal

	def _log (self, msg, level = None):
		log.msg("Experiment [%s]: %s" % (self.id, msg),	logLevel = level)

	id_set = util.Event()
	started = util.Event()
	finished = util.Event()
	cancelled = util.Event()
	paused = util.Event()
	resumed = util.Event()
	error = util.Event()

	#
	# event types:
	#	[e] experiment-change: { *delta: id, title, state }
	#	[i] interface-change: { item: x, *delta - disabled / enabled, text | delete-item: x }
	#	[s] step-change: { id: n, *delta - state, duration, child, expr ...  }
	#   [l] log { type: x, message: x } No - use the log handler
	#       (via experiment.log.message)
	#   [z] timezero { time: x }
	#

	def __init__ (self, step = None, id = None, marshal = None):
		self._id = None

		self._machines = set()

		self._logging = False
		self._log_variables = {}
		self._time_zero = util.now()

		self.step = step

		self.interface = InterfaceSectionSet()
		self.interface["experiment"] = InterfaceSection()

		if marshal is None:
			self._marshal = Marshal(self)
		else:
			self._marshal = marshal
			self._marshal.push(self)

		self.state = State.READY

		if id is not None:
			self.id = id


	# Todo: extract from Steps? (Difficult!)
	def register_machine (self, machine):
		"""
		Registers a machine with the experiment.

		Registered machines are started before the experiment is run,
		and their variables and controls are registered automatically
		with the experiment.
		"""

		self._machines.add(machine)
		self.interface[machine.alias] = machine.ui

	def run (self):
		"""
		Start running the experiment.
		"""

		if self.state is not State.READY:
			raise Exception("Already Started")

		if self.step is None:
			raise Exception("No Step")

		self.state = State.RUNNING
		finished = defer.Deferred()

		@defer.inlineCallbacks
		def run_experiment ():
			# wait for machines to be ready
			# todo: with some timeout
			self._log("Waiting for machines")
			try:
				result = yield defer.gatherResults(
					[m.ready for m in self._machines]
				)
			except:
				self._log("Error")
				raise # deal with Busy / errback.

			# reset machines
			# todo: with some timeout
			self._log("Resetting machines")
			try:
				result = yield defer.gatherResults(
					[defer.maybeDeferred(m.reset) for m in self._machines]
				)
			except:
				self._log("Error")
				raise # deal with errback.

			# start logging
			# add event listeners to step
			self._log("Starting logging")
			self.set_log_output(self.default_log_output)

			self.interface.event += self._interface_event #(log, passthrough to marshal)
			self.step.event += self._step_event #(log, passthrough to marshal)
			self.step.log += self._step_log #(log, passthrough to marshal)

			# run step
			self._log("Running experiment sequence")
			try:
				self.started()
				yield self.step.run()
				self.state = State.COMPLETE

			except Exception as error:
				self._log(error)
				self.error(error)
				self.state = State.ERROR
				raise

			finally:
				# remove event listeners
				self.interface.event -= self._interface_event
				self.step.event -= self._step_event
				self.step.log -= self._step_log

				# pop experiment from marshal
				self._log("Waiting for marshal")
				yield self._marshal.popExperiment()

				# stop logging
				self.stop_logging()
				self.finished()

		d = run_experiment()
		d.addCallbacks(finished.callback, finished.errback)
		d.addErrback(log.err)

		# TODO:
		# log for events 
		# log for log events
		# make a new dir for each invocation of run
		# store child.log in this dir
		# store control python file in this dir (runtime).
		# periodically flush all log files.

		# Finished will callback once the experiment is complete
		return finished

	def _interface_event (self, item, **data):
		data["item"] = item.name
		self._marshal.event(Event.INTERFACE, data)

	def _step_event (self, item, **data):
		data["step"] = item.id
		data["type"] = item.type

		if "child" in data and data["child"] is not None:
			data["child"] = data["child"].serialize()

		if "children" in data and data["children"] is not None:
			data["children"] = [c.serialize() for c in data["children"]]

		if "state" in data:
			data["state"] = data["state"].value

		# send to event log
		self._event_log.write(util.now(), "step:" + str(data))

		self._marshal.event(Event.STEP, data)

	def _step_log (self, message, level = None):
		data = {
			"level": level or "info",
			"message": message
		}

		# send to log
		self._msg_log.write(util.now(), message)

		self._marshal.event(Event.LOG, data)

	def pause (self):
		"""
		Pause the experiment.

		This pauses the currently running step, and calls the pause method on
		all registered machines.
		"""

		if self.state is State.RUNNING:
			self.state = State.PAUSED
			self.paused(self)

			return defer.gatherResults(
				[defer.maybeDeferred(self.step.pause)]
				+ [defer.maybeDeferred(m.pause) for m in self._machines]
			)

	def resume (self):
		"""
		Resume the experiment.

		Resumes after pause() has been called.
		"""

		if self.state is State.PAUSED:
			self.state = State.RUNNING
			self.resumed(self)

			return defer.gatherResults(
				[defer.maybeDeferred(self.step.resume)]
				+ [defer.maybeDeferred(m.resume) for m in self._machines]
			)

	def stop (self):
		"""
		(Emergency) stop the experiment.

		Immediately halts all processing and exits with an error.
		"""

		if self.state in (State.RUNNING, State.PAUSED):
			self.cancelled(self)

			return defer.gatherResults(
				[defer.maybeDeferred(self.step.abort)]
				+ [defer.maybeDeferred(m.pause) for m in self._machines]
			)
	#
	# Logging
	#
	# TODO - replace logger with batch logger.
	#
	def log_variables (self, *variables):
		if self._logging is True:
			raise Error ("Cannot set variables whilst actively logging")

		self._log_variables = {}

		for v in variables:
			if isinstance(v, data.Variable) and v.alias not in self._variables:
				self._log_variables[v.alias] = v

			elif isinstance(v, Component):
				self._log_variables.update(v.variables)

	def set_log_output (self, name):
		time_zero = util.now()
		name = LogFile.get_dir(name)

		if len(self._log_variables) is 0:
			for m in self._machines:
				self._log_variables.update(m.variables)

			self._log_variables.update(self.interface.properties)

		items = self._log_variables.iteritems()

		for key, var in items:
			try:
				var.setLogFile(LogFile(name, key, time_zero))
				var.truncate()
			except AttributeError:
				pass

		try:
			self._event_log.close()
			self._msg_log.close()
		except AttributeError:
			pass

		self._event_log = LogFile(name, "events", time_zero)
		self._msg_log = LogFile(name, "log", time_zero)

		self._logging = True
		self._time_zero = time_zero

		self._event_log.write(time_zero, "tz")
		self.marshal.event(Event.TIMEZERO, { "time": time_zero, "clear": True } )

	def stop_logging (self):
		self._logging = False

		items = self._log_variables.iteritems()

		for key, var in items:
			try:
				var.stopLogging()
			except AttributeError:
				pass

		try:
			self._event_log.close()
			self._event_log = None
		except AttributeError:
			pass

		try:
			self._msg_log.close()
			self._msg_log = None
		except AttributeError:
			pass


class Variable (data.Variable):
	def __init__ (self, title, type, unit = None):
		data.Variable.__init__(self, type)

		self.title = title
		self.unit = unit

		# Store all values
		self._length = None
		self._archive.threshold_factor = None

	def _push (self, value, time = None):
		if type(value) != self.type:
			value = self.type(value)

		# Ignore repeat values
		if value != self.value:
			# Make a step change by inserting the initial and
			# final values at the same time.
			if self.value is not None:
				data.Variable._push(self, self.value, time)

			data.Variable._push(self, value, time)

	def get (self, start, interval = None, step = 1):
		return self._archive.get(start, interval)
