# Twisted Imports
from twisted.internet import reactor, defer
from twisted.internet.error import ConnectionRefusedError
from twisted.spread import pb
from twisted.python import log

# System Imports
import logging
from collections import deque

# Package Imports
from .. import util
from ..constants import Event

HOST = "127.0.0.1"
PORT = 8789

# TODO - send all data in bulk at end of experiment.
# TODO - experiment resume from a written log after crash???
class Marshal (object):

	def __init__ (self, experiment):
		self._stack = deque()

		self.id = None
		self.connected = False
		self.sending = False
		self.marshal = None
		self._popWait = None
		self._eventQueue = []

		self.push(experiment)

	def push (self, experiment):
	
		if self.id is not None and experiment.id != self.id:
			raise Exception("Marshal.push(): New experiment must not have a different ID")

		try:
			self._stack.append(self._experiment)
		except AttributeError:
			pass

		self._experiment = experiment

		if experiment.id is None:
			if self.id is None:
				experiment.id_set += self._id_set
			else:
				experiment.id = self.id
		elif self.id is None:
			self.id = experiment.id
			self.connect()

		self.eventHistory = []
		self._eventIndex = 0

		self.event(Event.NEW_EXPERIMENT, { 
			"title": self._experiment.title, 
			"id": self._experiment.id,
			"event_index": self._eventIndex,
			"interface": self._experiment.interface.output()
		})

	def _pop (self):
		try:
			self._experiment.id_set -= self._id_set
			self._experiment = self._stack.pop()
			self.event(Event.NEW_EXPERIMENT, { 
				"title": self._experiment.title, 
				"id": self._experiment.id,
				"event_index": self._eventIndex,
				"interface": self._experiment.interface.output()
			})

		except IndexError:
			# Root experiment has finished. Shut down somehow?
			pass

	def _id_set (self, expt, id):
		if expt is self._experiment and self.id is None:
			self.id = id
			self.connect()

	def connect (self):
		def connected (marshal):
			self.connected = True
			self.marshal = marshal
			self.register().addCallback(registered)

		def registered (result):
			self._send()

		def failed (failure):
			# Connection to marshal failed
			f = failure.check(ConnectionRefusedError)

			if f is ConnectionRefusedError:
				# Retry in 5 seconds
				reactor.callLater(5, self.connect)
			else:
				print failure

		if self.connected:
			return

		factory = pb.PBClientFactory()
		reactor.connectTCP(HOST, PORT, factory)
		factory.getRootObject().addCallbacks(connected, failed)

	def register (self):
		def register_failed (failure):
			print "Registration failed: " + str(failure)

		return self.marshal.callRemote(
			"register", 
			self._experiment.id, 
			_RemoteWrapper(self._experiment)
		).addErrback(register_failed)

	def _send (self):
		if self.connected is False:
			return

		def sent (result):
			self.sending = False
			self._send()

		def failed (failure, events):
			print "Event send failed"

			f = failure.check(pb.PBConnectionLost)

			if f is pb.PBConnectionLost:
				print "Reconnecting"
				retry(events)
			else:
				print failure

		def retry (events):
			self._eventQueue[:0] = events
			self.sending = False
			self.connected = False
			self.connect()

		# Try to send all queued events in a batch
		if len(self._eventQueue) > 0:
			events, self._eventQueue = self._eventQueue, []

		else:
			# Finish off if this is the last event to send
			if self._popWait is not None:
				try:
					self._popWait.callback(None)
					self._pop()
				except defer.AlreadyCalledError:
					pass

				self._popWait = None

			return

		try:
			d = self.marshal.callRemote("event", self.id, events)
			d.addCallbacks(sent, failed, errbackArgs = events)
			self.sending = True

		except pb.DeadReferenceError:
			print "Disconnected from Marshal, reconnecting"
			retry(events)

	def event (self, type, data):
		ev = {
			"index": self._eventIndex,
			"time":  util.now(),
			"type":  type.value,
			"data":  data
		}
		self._eventIndex += 1

		self._eventQueue.append(ev)
		self.eventHistory.append(ev)

		print "Event: " + repr(ev)

		if self.sending is False:
			self._send()

	def popExperiment (self):
		if self.connected:
			self._popWait = defer.Deferred()

			#TODO:? Queue a send of a complete set of data.

			return self._popWait

		else:
			return defer.succeed(None)


class _RemoteWrapper (object, pb.Referenceable):

	def __init__ (self, experiment):
		self.experiment = experiment

	def remote_title (self):
		return self.experiment.title

	def remote_state (self):
		return self.experiment.state.value

	def remote_time_zero (self):
		return self.experiment._time_zero

	def remote_steps (self):
		return []

	def remote_events (self, start = None, end = None):
		return self.experiment.marshal.eventHistory[start:end]

	def remote_current_step (self):
		return self.experiment._current.serialize()

	def remote_properties (self, variables):
		return [
			self.experiment.interface.properties[x.encode('ascii', 'replace')].value 
			for x in variables
		]

	def remote_check_streams (self, streams):
		streams = [x.encode('ascii', 'replace') for x in streams]
		bad_streams = [
			name not in self.experiment.interface.properties
			for name in streams
		]

		if any(bad_streams):
			raise Exception("Invalid Streams", bad_streams)

		return 'OK'

	def remote_data (self, streams, start, interval, step):
		streams = [x.encode('ascii', 'replace') for x in streams]
		self.remote_check_streams(streams)

		def compress (point):
			try:
				return (round(point[0] - start, 1), round(point[1], 2))
			except TypeError:
				return 0

		return {
			"zero": round(start, 1),
			"max": round(interval, 1),
			"data": [
				map(compress, self.experiment.interface.properties[x].get(start, interval, step))
				for x in streams
			]
		}

	def remote_ui (self):
		return self.experiment.interface.output()

	def remote_control_set (self, control_alias, value):
		try:
			self.experiment._log("Setting control %s to %s" % (control_alias, value), logging.DEBUG)
			return self.experiment.interface.controls[control_alias].update(value)
		except (KeyError, AttributeError):
			self.experiment._log("Set control failed", logging.WARNING)
			raise
			#return False

	def remote_start (self):
		return self.experiment.run()

	def remote_stop (self):
		return self.experiment.stop()

	def remote_pause (self):
		return self.experiment.pause()

	def remote_resume (self):
		return self.experiment.resume()
