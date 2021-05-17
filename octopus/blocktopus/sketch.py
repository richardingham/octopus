# Python Imports
import uuid
import os
import re
import json
from time import time as now
import asyncio

# Twisted Imports
from twisted.python.filepath import FilePath
from twisted.logger import Logger

# Octopus Imports
from octopus.sequence.error import NotRunning
from octopus.events import EventEmitter

# Package Imports
from .database.dbutil import makeFinder
from .workspace import Workspace, Aborted, Cancelled
from .experiment import Experiment


class Sketch (EventEmitter):
	""" This object is the representation of the persistent sketch,
	stored in the database and in the event store. """

	# We will use a file based event store for now, then migrate to EventStore later.

	db = None
	dataDir = None
	log = Logger()

	@classmethod
	def createId (cls):
		id = str(uuid.uuid4())
		created_date = now()

		# Check that the UUID is not already used. I am sure this is probably unnecessary by definition...
		#rows = cls.db.runQuery("SELECT guid FROM sketches WHERE guid = ?", (id,))
		#if len(rows) == 0:
		#	break

		# Insert the new sketch into the DB
		def _done (result):
			return id

		return cls.db.runOperation("""
				INSERT INTO sketches
				(guid, title, user_id, created_date, modified_date, deleted)
				VALUES (?, ?, ?, ?, ?, 0)
			""",
			(id, "New Sketch", 1, created_date, created_date)
		).addCallback(_done)

	@classmethod
	def exists (cls, id):
		d = cls.db.runQuery("SELECT guid FROM sketches WHERE guid = ?", (id,))
		d.addCallback(lambda r: len(r) > 0)

		return d

	@classmethod
	def delete (cls, id):
		return cls.db.runOperation("UPDATE sketches SET deleted = 1 WHERE guid = ?", (id, ))

	@classmethod
	def restore (cls, id):
		return cls.db.runOperation("UPDATE sketches SET deleted = 0 WHERE guid = ?", (id, ))

	def __init__ (self, id):
		self.id = id
		self.title = ""
		self.user_id = 1
		self.loaded = False
		self.workspace = Workspace()
		self.experiment = None
		self.subscribers = {}
		self._eventIndex = 0

		self._sketchDir = FilePath(self.dataDir).child(id)
		if not self._sketchDir.exists():
			self._sketchDir.createDirectory()

		eventFile = self._sketchDir.child("events.log")
		if not eventFile.exists():
			eventFile.create()

		self._eventsLog = eventFile.open('a')

		self.log.info(
			"Initialising sketch {log_source.id!s} with data dir {log_source._sketchDir!s}"
		)

	def load (self):
		return self._loadFrom(self.id)

	def copyFrom (self, id):
		return self._loadFrom(id, copy = True)

	
	async def _loadFrom (self, id, copy = False):
		sketch = await self.db.runQuery(
			"SELECT title FROM sketches WHERE guid = ?",
			(id, )
		)

		if len(sketch) == 0:
			raise Error("Sketch %s not found." % id)

		self.title = sketch[0][0]
		self.loaded = True

		# Find the most recent snapshot file
		try:
			sketchDir = FilePath(self.dataDir).child(id)
			max_snap = max(map(
				lambda fp: int(
					os.path.splitext(fp.basename())[0].split('.')[1]
				),
				sketchDir.globChildren('snapshot.*.log')
			))

			self.log.debug(
				"Found latest snapshot {snapshot_id} for sketch {log_source.id!s}",
				snapshot_id = max_snap
			)

		except ValueError:
			self._eventIndex = 0
			self._snapEventIndex = 0
		else:
			snapFile = sketchDir.child('snapshot.' + str(max_snap) + '.log')

			if max_snap > 0:
				loop = asyncio.get_running_loop()
				snapshot = await loop.run_in_executor(None, snapFile.getContent)
				events = list(map(
					json.loads,
					filter(lambda e: e.strip() != b"", snapshot.split(b"\n"))
				))
				self.workspace.fromEvents(events)

				self.log.info(
					"Loaded from snapshot {snapshot_id} for sketch {log_source.id!s}",
					snapshot_id = max_snap
				)

			if copy:
				self._eventIndex = len(events)
				self._snapEventIndex = 0
			else:
				self._eventIndex = max_snap
				self._snapEventIndex = max_snap

		# Rename if a copy
		if copy:
			self.rename(self.title + " Copy")

	def close (self):
		self.log.info(
			"Closing sketch {log_source.id!s}",
		)

		# If anything has changed...
		if self._eventIndex > self._snapEventIndex:
			# Write a snapshot
			snapFile = self._sketchDir.child("snapshot." + str(self._eventIndex) + ".log")
			if not snapFile.exists():
				snapFile.create()

			with snapFile.open('w') as fp:
				fp.write("\n".join(map(json.dumps, self.workspace.toEvents())).encode('utf-8'))
			
			self.log.debug(
				"Written snapshot file {snap_file} sketch {log_source.id!s}",
				snap_file = snapFile
			)

		# Set the modified date
		self.db.runOperation('''
			UPDATE sketches
			SET modified_date = ?
			WHERE guid = ?
		''', (now(), self.id))

		# Close the events log
		self._eventsLog.close()

		self.emit("closed")

	def rename (self, title):
		self._writeEvent("RenameSketch", { "from": self.title, "to": title })
		self.db.runOperation("UPDATE sketches SET title = ? WHERE guid = ?", (title, self.id))
		self.title = title

	#
	# Subscribers
	#

	def subscribe (self, subscriber, notifyFn):
		self.subscribers[subscriber] = notifyFn

	def unsubscribe (self, subscriber):
		if subscriber in self.subscribers:
			del self.subscribers[subscriber]

		if len(self.subscribers) == 0:
			self.close()

	def notifySubscribers (self, protocol, topic, payload, source = None):
		for subscriber, notifyFn in self.subscribers.items():
			if subscriber is not source:
				notifyFn(protocol, topic, payload)

	#
	# Experiment
	#

	async def runExperiment (self, context):
		if self.experiment is not None:
			raise ExperimentAlreadyRunning

		self.log.info(
			"Creating experiment for sketch {log_source.id!s}",
		)

		self.experiment = Experiment(self)

		self.notifySubscribers("experiment", "state-started", {
			"sketch": self.id,
			"experiment": self.experiment.id
		}, self.experiment)

		try:
			try:
				result = await self.experiment.run()
			except Cancelled as msg:
				result = msg

		except Exception as exc:
			if isinstance(exc, Aborted):
				exc = Aborted("Manual stop")

			self.notifySubscribers("experiment", "state-error", {
				"sketch": self.id,
				"experiment": self.experiment.id,
				"error": exc
			}, self.experiment)

		else:
			self.notifySubscribers("experiment", "state-stopped", {
				"sketch": self.id,
				"experiment": self.experiment.id
			}, self.experiment)

		finally:
			self.log.info(
				"Closing experiment for sketch {log_source.id!s} ({result})",
				result = result
			)

			self.experiment = None

	def pauseExperiment (self, context):
		if self.experiment is None:
			raise NoExperimentRunning
	
		self.log.info(
			"Pausing experiment for sketch {log_source.id!s}"
		)

		try:
			self.experiment.pause()
		except Exception as exc:
			self.notifySubscribers("experiment", "state-error", {
				"sketch": self.id,
				"experiment": self.experiment.id,
				"error": str(exc)
			}, self.experiment)
			raise
		else:
			self.notifySubscribers("experiment", "state-paused", {
				"sketch": self.id,
				"experiment": self.experiment.id
			}, self.experiment)


	def resumeExperiment (self, context):
		if self.experiment is None:
			raise NoExperimentRunning
	
		self.log.info(
			"Resuming experiment for sketch {log_source.id!s}"
		)

		try:
			self.experiment.resume()
		except Exception as exc:
			self.notifySubscribers("experiment", "state-error", {
				"sketch": self.id,
				"experiment": self.experiment.id,
				"error": str(exc)
			}, self.experiment)
		else:
			self.notifySubscribers("experiment", "state-resumed", {
				"sketch": self.id,
				"experiment": self.experiment.id
			}, self.experiment)

	def stopExperiment (self, context):
		if self.experiment is None:
			raise NoExperimentRunning

		self.log.info(
			"Stopping experiment for sketch {log_source.id!s}"
		)

		self.experiment.stop()

	#
	# Operations
	#

	def renameSketch (self, payload, context):
		self.rename(payload['title'])

		self.notifySubscribers("sketch", "renamed", {
			"event": self._eventIndex,
			"title": payload['title']
		}, context)

	def processEvent (self, event, context):
		event.apply(self.workspace)
		eid = self._writeEvent(event.type, event.values)

		self.notifySubscribers(event.jsProtocol, event.jsTopic, event.valuesWithEventId(eid), context)

	def runtimeCancelBlock (self, id):
		try:
			block = self.workspace.getBlock(id)
		except KeyError:
			return

		try:
			block.cancel()
		except NotRunning:
			pass

	def _writeEvent (self, eventType, data):
		if not self.loaded:
			raise Error("Sketch is not loaded")

		self._eventIndex += 1

		event = {
			"index": self._eventIndex,
			"type": eventType,
			"data": data
		}

		self._eventsLog.write((json.dumps(event) + "\n").encode("utf-8"))

		return self._eventIndex


find = makeFinder(
	Sketch,
	'sketches',
	{
		'guid': { 'type': str },
		'title': {
			'type': str,
			'modifier': lambda x: '%' + x + '%',
			'operator': ' LIKE ?' 
		},
		'user_id': { 'type': int },
		'created_date': { 'type': int },
		'modified_date': { 'type': int },
		'deleted': { 'type': bool }
	}
)


class Error (Exception):
	pass

class ExperimentAlreadyRunning (Error):
	pass

class NoExperimentRunning (Error):
	pass
