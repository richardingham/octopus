# Python Imports
import uuid
import os
import json
import time
import re
import numpy as np

now = time.time # shortcut

# Twisted Imports
from twisted.internet import defer, threads, task
from twisted.python import log
from twisted.python.filepath import FilePath

# Octopus Imports
from octopus.sequence.error import AlreadyRunning, NotRunning
from octopus.events import EventEmitter

# Package Imports
from .database.dbutil import makeFinder


class Experiment (EventEmitter):
	""" This object is the representation of a running experiment,
	stored in the database and in the event store. """

	db = None
	dataDir = None

	@classmethod
	def exists (cls, id):
		d = cls.db.runQuery("SELECT guid FROM experiments WHERE guid = ?", (id,))
		d.addCallback(lambda r: len(r) > 0)

		return d

	@classmethod
	def delete (cls, id):
		return cls.db.runOperation("UPDATE experiments SET deleted = 1 WHERE guid = ?", (id, ))

	@classmethod
	def restore (cls, id):
		return cls.db.runOperation("UPDATE experiments SET deleted = 0 WHERE guid = ?", (id, ))

	def __init__ (self, sketch):
		id = str(uuid.uuid4())

		self.id = id
		self.sketch = sketch
		self.logMessages = []

	@defer.inlineCallbacks
	def run (self):
		""" Run the experiment.

		Main method to run an experiment. Returns a Deferred which
		calls back when the experiment is complete, or errs back
		if there is an error in the experiment.

		Whilst the experiment is running, the pause(), resume() and
		stop() methods can be used to interact with it. (Note: stop()
		will cause the Deferred returned by run() to errback).

		This method:

		1. Inserts an entry for the experiment into the database.
		2. Creates a directory for the experiment data.
		3. Takes a snapshot of the sketch and stores it in the directory.
		4. Sets event listeners to record any sketch changes during the
		   experiment.
		5. Records all changes to variables in the workspace
		   during the experiment.


		"""

		id = self.id
		sketch = self.sketch
		sketch_id = sketch.id
		workspace = sketch.workspace

		# If the workspace is already running, we can't run another
		# experiment on top of it. No experiment entry in the database
		# will be created.
		try:
			yield workspace.reset()
		except AlreadyRunning:
			yield workspace.abort()
			yield workspace.reset()

		self.startTime = now()

		# Insert the new experiment into the DB.
		yield self.db.runOperation("""
				INSERT INTO experiments
				(guid, sketch_guid, title, user_id, started_date)
				VALUES (?, ?, ?, ?, ?)
			""",
			(id, sketch_id, sketch.title, 1, self.startTime)
		)

		# Create a directory to store the experiment logs and data.
		stime = time.gmtime(self.startTime)

		self._experimentDir = FilePath(self.dataDir)
		for segment in [stime.tm_year, stime.tm_mon, stime.tm_mday, id]:
			self._experimentDir = self._experimentDir.child(str(segment))
			if not self._experimentDir.exists():
				self._experimentDir.createDirectory()

		# Create files for the sketch logs, snapshot, variables etc.
		eventFile = self._experimentDir.child("events.log").create()
		sketchFile = self._experimentDir.child("sketch.log").create()
		snapFile = self._experimentDir.child("sketch.snapshot.log")
		varsFile = self._experimentDir.child("variables")
		openFiles = { "_events": eventFile, "_sketch": sketchFile }
		usedFiles = {}

		# Write a snapshot of the sketch.
		with snapFile.create() as fp:
			fp.write("\n".join(map(json.dumps, workspace.toEvents())).encode('utf-8'))

		# Log events emitted by the sketch (block changes, etc.)
		# The idea is that with the snapshot and change log, the
		# layout of the sketch could be replayed over the period
		# of the experiment.
		def onSketchEvent (protocol, topic, data):
			print ("Sketch event: %s %s %s" % (protocol, topic, data))

			# Don't log block state events to the sketch log
			# (there will be lots, and they are not relevant to the
			# structure of the sketch)
			if protocol == "block" and topic == "state":
				return

			# If the sketch is renamed whilst the experiment is
			# running, update the experiment title.
			elif protocol == "sketch" and topic == "renamed":
				self.db.runOperation("""
					UPDATE experiments SET title = ? WHERE guid = ?
				""", (data['title'], id)).addErrback(log.err)

			writeEvent(sketchFile, protocol, topic, data)

		# Helper function to format an event and write it to the file.
		def writeEvent (file, protocol, topic, data):
			time = now()

			event = {
				"time": time,
				"relative": time - self.startTime,
				"protocol": protocol,
				"topic": topic,
				"data": data
			}

			file.write((json.dumps(event) + "\n").encode('utf-8'))

		sketch.subscribe(self, onSketchEvent)

		# Subscribe to workspace events. Block states are written to
		# the events log.
		@workspace.on("block-state")
		def onBlockStateChange (data):
			writeEvent(eventFile, "block", "state", data)

			data['sketch'] = sketch_id
			data['experiment'] = id
			sketch.notifySubscribers("block", "state", data, self)

		# Log messages are written to the events log, and also
		# broadcast to subscribers. The experiment keeps a record
		# of events so that new clients can get a historical log.
		@workspace.on("log-message")
		def onLogMessage (data):
			writeEvent(eventFile, "experiment", "log", data)

			data['sketch'] = sketch_id
			data['experiment'] = id
			data['time'] = round(now(), 2)
			self.logMessages.append(data)
			sketch.notifySubscribers("experiment", "log", data, self)

		# Log changes to variable data.
		#
		# Note: files are only created when a variable actually gets data,
		# not necessarily when the variable is created.
		#
		# The relative time is written, to save filesize. The absolute
		# time can be calculated using the start time at the top of the file.
		@workspace.variables.on("variable-changed")
		def onVarChanged (data):
			try:
				logFile = openFiles[data['name']]
			except KeyError:
				varName = unusedVarName(data['name'])
				fileName = fileNameFor(varName)
				logFile = self._experimentDir.child(fileName).create()
				openFiles[varName] = logFile
				addUsedFile(varName, fileName, workspace.variables.get(data['name']))

				logFile.write(
					f"# name:{data['name']}\n# type:{type(data['value']).__name__} \n# start:{self.startTime:.2f}\n".encode('utf-8')
				)

			logFile.write(f"{data['time'] - self.startTime:.2f}, {data['value']}\n".encode('utf-8'))

		# Update the open files list if a variable is renamed.
		#
		# TODO: Variable renaming during experiment run is a bit dodgy.
		# Which variable to display in the results? It might be better to
		# disallow renaming during runtime.
		@workspace.variables.on("variable-renamed")
		def onVarRenamed (data):
			openFiles[data['newName']] = openFiles[data['oldName']]
			del openFiles[data['oldName']]
			addUsedFile(data['newName'], "", data['variable'])

		# Ensure that renaming vars doesn't lead to any overwriting.
		# (see TODO above).
		def unusedVarName (varName):
			if varName in usedFiles:
				return unusedVarName(varName + "_")
			return varName

		# Format a variable name into a file name
		def fileNameFor (varName):
			return re.sub(r'[^a-z0-9\.]', '_', varName) + '.csv'

		# Build a list of files and variables to be written to the variables
		# list file, which is used to generate the var list
		# when the experiment results are being displayed.
		def addUsedFile (varName, fileName, variable):
			try:
				unit = str(variable.unit)
			except AttributeError:
				unit = ""

			if fileName != "":
				usedFiles[varName] = {
					"name": varName,
					"type": variable.type.__name__,
					"unit": unit,
					"file": fileName
				}
			else:
				usedFiles[varName] = {}

		# Write all file data. This is called periodically during the
		# experiment so that data variables that do not change very
		# often is still written to disk, and will not be lost if the
		# program crashes.
		def flushFiles ():
			try:
				for file in openFiles.values():
					file.flush()
					os.fsync(file.fileno())
			except:
				log.err()

		flushFilesLoop = task.LoopingCall(flushFiles)
		flushFilesLoop.start(5 * 60, False).addErrback(log.err)

		# Attempt to run the experiment. Make sure that eveything is
		# cleaned up after the experiment, even in the event of an error.
		try:
			yield workspace.run()
		finally:
			# Remove event handlers
			sketch.unsubscribe(self)
			workspace.off("block-state", onBlockStateChange)
			workspace.off("log-message", onLogMessage)
			workspace.variables.off("variable-changed", onVarChanged)
			workspace.variables.off("variable-renamed", onVarRenamed)

			# Close file pointers
			with varsFile.create() as fp:
				fp.write(json.dumps(usedFiles).encode('utf-8'))

			try:
				flushFilesLoop.stop()
			except:
				log.err()

			for file in openFiles.values():
				file.close()

			# Store completed time for experiment.
			self.db.runOperation("""
				UPDATE experiments SET finished_date = ? WHERE guid = ?
			""", (now(), id)).addErrback(log.err)

	def pause (self):
		"""Pause the experiment if it is running.

		Throws an error if called when the experiment is not running.
		"""
		return self.sketch.workspace.pause()

	def resume (self):
		"""Resume the experiment if it is paused.

		Throws an error if called when the experiment is not paused.
		"""
		return self.sketch.workspace.resume()

	def stop (self):
		"""Abort the experiment.

		Causes the Deferred returned from run() to errback.

		Throws an error if called when the experiment is not running.
		"""
		return self.sketch.workspace.abort()

	#
	# Subscribers
	#

	def variables (self):
		from octopus.machine import Component
		from octopus.data.data import BaseVariable

		variables = {}

		for name, var in self.sketch.workspace.variables.items():
			if isinstance(var, Component):
				variables.update(var.variables)
			elif isinstance(var, BaseVariable):
				variables[name] = var

		return variables


find = makeFinder(
	Experiment,
	'experiments',
	{
		'guid': { 'type': str },
		'sketch_guid': { 'type': str },
		'title': {
			'type': str,
			'modifier': lambda x: '%' + x + '%',
			'operator': ' LIKE ?'
		},
		'user_id': { 'type': int },
		'started_date': { 'type': int },
		'finished_date': { 'type': int },
		'duration': {
			'type': int,
			'sql': '(finished_date - started_date) AS duration'
		},
		'deleted': { 'type': bool }
	}
)


class CompletedExperiment (object):
	def __init__ (self, id):
		self.id = id

	@defer.inlineCallbacks
	def load (self):
		expt = yield self._fetchFromDb(self.id)
		experimentDir = self._getExperimentDir(self.id, expt['started_date'])

		self.title = expt['sketch_title']
		self.date = expt['started_date']
		self.started_date = expt['started_date']
		self.finished_date = expt['finished_date']
		self.sketch_id = expt['sketch_guid']

		def _varName (name):
			if '::' in name:
				return '.'.join(name.split('::')[1:])
			else:
				return name

		variables = yield self._getVariables(experimentDir)
		self.variables = [
			{
				"key": v["name"],
				"name": _varName(v["name"]),
				"type": v["type"],
				"unit": v["unit"]
			}
			for v in variables.values()
			if "name" in v
		]

	@defer.inlineCallbacks
	def loadData (self, variables, start, end):
		date = yield self._fetchDateFromDb(self.id)
		experimentDir = self._getExperimentDir(self.id, date)
		storedVariablesData = yield self._getVariables(experimentDir)

		data = yield defer.gatherResults(map(
			lambda variable: self._getData(
				experimentDir.child(variable["file"]),
				variable["name"],
				variable["type"],
				start,
				end
			),
			map(lambda name: storedVariablesData[name], variables)
		))

		defer.returnValue(data)

	@defer.inlineCallbacks
	def buildExcelFile (self, variables, time_divisor, time_dp):
		import pandas as pd
		from io import BytesIO

		date = yield self._fetchDateFromDb(self.id)
		experimentDir = self._getExperimentDir(self.id, date)
		storedVariablesData = yield self._getVariables(experimentDir)
		bio = BytesIO()

		# https://pandas.pydata.org/pandas-docs/stable/user_guide/io.html#writing-excel-files-to-memory
		writer = pd.ExcelWriter(bio, engine='xlsxwriter')

		def varName (variable):
			""" Generates a column title from a variable name """

			if variable["unit"] != '':
				unit = ' (' + variable["unit"] + ')'
			else:
				unit = ''

			if '::' in variable["name"]:
				name = '.'.join(variable["name"].split('::')[1:])
			else:
				name = variable["name"]

			return name + unit

		# Read data for each requested variable
		cols = yield defer.gatherResults(map(
			lambda variable: threads.deferToThread(
				pd.read_csv,
				experimentDir.child(variable["file"]).path,
				comment = '#',
				index_col = 0,
				usecols = [0, 1],
				names = ["Time", varName(variable)]
			),
			map(lambda name: storedVariablesData[name.decode('ascii')], variables)
		))

		# Convert the columns into a single DataFrame
		dataframe = pd.concat(cols, axis = 1)

		# Ensure there is a datapoint at each time point. Fill rather than
		# interpolate to maintain greatest data fidelity.
		dataframe.fillna(method = 'pad', inplace = True)

		# Reduce the number of datapoints according to time_divisor / time_dp
		# This is done over the entire dataframe, after filling empty values,
		# so that all property values are retained.
		def format_time (x):
			if x != "":
				return round(float(x) / time_divisor, time_dp)

		dataframe = dataframe.groupby(format_time).first()

		# Remove invalid chars from expt title for Excel sheet title
		sheet_title = re.sub(r'[\[\]\*\/\\\?]+', '', self.title)[0:30]

		# Generate excel file
		dataframe.to_excel(writer, sheet_name = sheet_title)
		writer.save()

		# Seek to the beginning and read to copy the workbook to a variable in memory
		bio.seek(0)
		defer.returnValue(bio.read())

	def _fetchFromDb (self, id):
		def _done (rows):
			try:
				row = rows[0]
			except KeyError:
				return None

			return {
				'guid': str(row[0]),
				'sketch_guid': str(row[1]),
				'user_id': int(row[2]),
				'started_date': int(row[3]),
				'finished_date': int(row[4]),
				'sketch_title': str(row[5])
			}

		return Experiment.db.runQuery("""
			SELECT guid, sketch_guid, user_id, started_date, finished_date, title
			FROM experiments
			WHERE guid = ?
		""", (id, )).addCallback(_done)

	def _fetchDateFromDb (self, id):
		def _done (rows):
			try:
				return int(rows[0][0])
			except KeyError:
				return None

		return Experiment.db.runQuery("""
			SELECT started_date
			FROM experiments
			WHERE guid = ?
		""", (id, )).addCallback(_done)

	def _getExperimentDir (self, id, startTime):
		stime = time.gmtime(startTime)

		experimentDir = FilePath(Experiment.dataDir)
		for segment in [stime.tm_year, stime.tm_mon, stime.tm_mday, id]:
			experimentDir = experimentDir.child(str(segment))
			if not experimentDir.exists():
				return None

		return experimentDir

	@defer.inlineCallbacks
	def _getVariables (self, experimentDir):
		varsFile = experimentDir.child("variables")
		try:
			content = yield threads.deferToThread(varsFile.getContent)
			variables = json.loads(content)
		except:
			log.err()
			variables = {}

		defer.returnValue(variables)

	@defer.inlineCallbacks
	def _getData (self, dataFile, name, var_type, start = None, end = None):

		if var_type == "int":
			cast = int
		elif var_type == "float":
			cast = float
		else:
			cast = str

		if end is None:
			start = None

		def _readFile ():
			data = []
			with dataFile.open() as fp:
				for line in fp:
					# Skip comments
					if line[0] == 35:  
						# b'#' == 35
						continue

					time, value = line.split(b',')
					time = float(time)

					if start is not None:
						if time < start:
							continue
						if time > end:
							break

					data.append((time, cast(value.decode())))

			return data

		try:
			data = yield threads.deferToThread(_readFile)
		except:
			log.err()
			defer.returnValue({})

		# Make a readable variable name
		#var_name = '.'.join(name.split('::')[1:])

		if len(data) > 400 and cast in (int, float):
			if end is None:
				try:
					interval = data[-1][0] - data[0][0]
				except IndexError:
					interval = 0
			else:
				interval = end - start

			spread = max(data, key = lambda x: x[1])[1] - min(data, key = lambda x: x[1])[1]
			print ("Simplifying data with interval " + str(interval) + " (currently %s points)" % len(data))
			print ("Spread: %s" % spread)
			print ("Epsilon: %s" % min(interval / 200., spread / 50.))
			data = rdp(data, epsilon = min(interval / 200., spread / 50.))

		print (" -> %s points" % len(data))

		defer.returnValue({
			'name': name,
			'type': var_type,
			'data': data
		})


from math import sqrt

def distance(a, b):
	return  sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

def point_line_distance(point, start, end):
	if (start == end):
		return distance(point, start)
	else:
		n = abs(
			(end[0] - start[0]) * (start[1] - point[1]) - (start[0] - point[0]) * (end[1] - start[1])
		)
		d = sqrt(
			(end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2
		)
		return n / d

def rdp(points, epsilon):
	"""
	Reduces a series of points to a simplified version that loses detail, but
	maintains the general shape of the series.
	"""
	dmax = 0.0
	index = 0
	for i in range(1, len(points) - 1):
		d = point_line_distance(points[i], points[0], points[-1])
		if d > dmax:
			index = i
			dmax = d
	if dmax >= epsilon:
		results = rdp(points[:index+1], epsilon)[:-1] + rdp(points[index:], epsilon)
	else:
		results = [points[0], points[-1]]
	return results
