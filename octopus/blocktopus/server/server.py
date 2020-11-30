# -*- coding: utf-8 -*-

# Twisted Imports
from twisted.application import internet, service
from twisted.enterprise import adbapi
from twisted.internet import reactor, defer, utils
from twisted.spread import pb
from twisted.python import log, filepath, urlpath
from twisted.web import server, static, resource, guard, http
from twisted.web.template import flatten
from twisted.web.resource import NoResource
from twisted.cred.portal import IRealm, Portal

# Zope Imports
from zope.interface import implements

# Autobahn Imports
from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
from autobahn.websocket.compress import PerMessageDeflateOffer, PerMessageDeflateOfferAccept

# Sibling Imports
from .. import sketch
from .. import experiment
from . import websocket
from . import template

# System Imports
import sys, os
import uuid
import sqlite3
import json
import time
import re

now = time.time

##
## Database
##

data_path = os.path.abspath(os.path.join(os.getcwd(), "data"))

print(data_path)
dbfilename = os.path.join(data_path, "octopus.db")

if not os.path.isfile(dbfilename):
	sys.exit(
		"ERROR: Database not found.\n" + 
		"Searched in: " + dbfilename + "\n" +
		"Create the database using initialise.py before starting the server."
	)

dbpool = adbapi.ConnectionPool("sqlite3", dbfilename, check_same_thread = False)

experiment.Experiment.db = dbpool
experiment.Experiment.dataDir = os.path.join(data_path, "experiments")

sketch.Sketch.db = dbpool
sketch.Sketch.dataDir = os.path.join(data_path, "sketches")

##
## Sketch / Experiment Runtime
##

websocket_runtime = websocket.WebSocketRuntime()
loaded_sketches = websocket_runtime.sketches

def running_experiments ():
	return [
		sketch.experiment
		for sketch in loaded_sketches.values()
		if sketch.experiment is not None
	]

##
## Helper functions
##

def _redirectOrJSON (result, request: http.Request, url: urlpath.URLPath, data):
	try:
		if request.getHeader('x-requested-with') == 'XMLHttpRequest':
			request.write(json.dumps(data).encode('utf-8'))

			if not request.notifyFinish().called:
				request.finish()
			
			return
	except:
		pass

	request.redirect(str(url).encode('ascii'))
	request.finish()

def _respondWithJSON (result, request):
	request.write(json.dumps(result).encode('utf-8'))

	if not request.notifyFinish().called:
		request.finish()

def _error (failure, request):
	try:
		if request.getHeader('x-requested-with') == 'XMLHttpRequest':
			request.setResponseCode(500)
			request.write(json.dumps({ "error": str(failure) }).encode('utf-8'))
			request.finish()
			return
	except:
		pass

	log.err(failure)
	request.write(f"There was an error: {str(failure)}".encode('utf-8'))
	request.finish()

def _getArg (request, arg, cast = None, default = None):
	try:
		if cast is not None:
			return cast(request.args[arg][0])
		else:
			return request.args[arg][0]
	except (TypeError, KeyError):
		return default

def _getIntArg (request, arg):
	return _getArg(request, arg, int, 0)

def _getFloatArg (request, arg):
	return _getArg(request, arg, float, 0.)

def _getJSONArg (request, arg, default = None):
	return _getArg(request, arg, json.loads, default or {})

##
## HTTP Server - Home Page
##

class Root (resource.Resource):
	def render_GET (self, request):
		saved_sketches = sketch.find(
			default_search = {
				'deleted': { 'value': 0 }
			}, order = [
				{ 'column': 'modified_date', 'dir': 'desc' }
			],
			fetch_columns = ['guid', 'title', 'user_id', 'modified_date'],
			return_counts = False,
		)

		past_experiments = experiment.find(
			default_search = {
				'deleted': { 'value': 0 },
				'finished_date': { 'value': 0, 'operator': 'gt' }
			}, order = [
				{ 'column': 'finished_date', 'dir': 'desc' }
			],
			fetch_columns = ['guid', 'title', 'user_id', 'finished_date', 'duration'],
			return_counts = False,
			limit = 10
		)

		tpl = template.Root(running_experiments(), past_experiments, saved_sketches)
		request.write("<!DOCTYPE html>\n".encode('utf-8'))
		d = flatten(request, tpl, request.write)
		d.addCallbacks(lambda _: request.finish())
		d.addErrback(_error, request)

		return server.NOT_DONE_YET


class Sketch (resource.Resource):

	def getChild (self, id: bytes, request):
		if id == b"create":
			return NewSketch()

		return EditSketch(id)


class SketchFind (resource.Resource):

	def render_GET (self, request):
		start = _getIntArg(request, 'start')
		limit = _getIntArg(request, 'limit') or None
		sorts = _getJSONArg(request, 'sort', [])
		filters = _getJSONArg(request, 'filter', [])

		sketch.find(filters, sorts, start, limit)\
			.addCallback(_respondWithJSON, request)\
			.addErrback(_error, request)

		return server.NOT_DONE_YET


class NewSketch (resource.Resource):

	isLeaf = True

	def render_POST (self, request: http.Request):
		def _redirect (id):
			url = request.URLPath().sibling(id.encode('ascii'))
			_redirectOrJSON(None, request, url, {"created": id})

		sketch.Sketch.createId()\
			.addCallback(_redirect)\
			.addErrback(_error, request)

		return server.NOT_DONE_YET


class EditSketch (resource.Resource):

	def __init__ (self, id):
		resource.Resource.__init__(self)
		self._id = id.decode('ascii')

	def render_GET (self, request):
		def _done (exists):
			if not exists:
				request.write(f"Sketch {self._id} not found.".encode('utf-8'))
				request.finish()
				return

			tpl = template.SketchEdit(self._id)
			request.write("<!DOCTYPE html>\n".encode('utf-8'))
			d = flatten(request, tpl, request.write)
			d.addCallbacks(lambda _: request.finish())

		d = sketch.Sketch.exists(self._id)
		d.addCallback(_done)
		d.addErrback(_error, request)

		return server.NOT_DONE_YET

	def getChild (self, action: bytes, request):
		if action == b"copy":
			return CopySketch(self._id)
		elif action == b"delete":
			return DeleteSketch(self._id)
		elif action == b"restore":
			return UndeleteSketch(self._id)

		return NoResource()


class CopySketch (resource.Resource):

	isLeaf = True

	def __init__ (self, id):
		resource.Resource.__init__(self)
		self._id = id

	def render_POST (self, request):
		@defer.inlineCallbacks
		def _copy (id):
			s = sketch.Sketch(id)

			yield s.copyFrom(self._id)
			yield s.close()

			url = request.URLPath().parent().sibling(id.encode('ascii'))
			_redirectOrJSON(None, request, url, {"created": id})

		sketch.Sketch.createId()\
			.addCallback(_copy)\
			.addErrback(_error, request)

		return server.NOT_DONE_YET


class DeleteSketch (resource.Resource):

	isLeaf = True

	def __init__ (self, id):
		resource.Resource.__init__(self)
		self._id = id

	def render_POST (self, request):
		redirect_url = request.URLPath().parent().parent()

		sketch.Sketch.delete(self._id)\
			.addCallback(_redirectOrJSON, request, redirect_url, { "deleted": str(self._id) })\
			.addErrback(_error, request)

		return server.NOT_DONE_YET


class UndeleteSketch (resource.Resource):

	isLeaf = True

	def __init__ (self, id):
		resource.Resource.__init__(self)
		self._id = id

	def render_POST (self, request):
		redirect_url = request.URLPath().parent().parent()

		sketch.Sketch.restore(self._id)\
			.addCallback(_redirectOrJSON, request, redirect_url, { "restored": str(self._id) })\
			.addErrback(_error, request)

		return server.NOT_DONE_YET


class Experiment (resource.Resource):
	def getChild (self, id: bytes, request):
		return ShowExperiment(id.decode('ascii'))


class ExperimentFind (resource.Resource):

	def __init__ (self):
		resource.Resource.__init__(self)

	def render_GET (self, request):
		draw = _getIntArg(request, 'draw')
		start = _getIntArg(request, 'start')
		limit = _getIntArg(request, 'length') or None
		sorts = _getJSONArg(request, 'sort', [])
		filters = _getJSONArg(request, 'filter', [])

		def _done (result):
			result['draw'] = draw
			print(result)
			_respondWithJSON(result, request)

		experiment.find(
			filters, sorts, start, limit, {
				'deleted': { 'value': 0 },
				'finished_date': { 'value': 0, 'operator': 'gt' }
			},
			['guid', 'title', 'user_id', 'finished_date', 'duration']
		).addCallback(_done).addErrback(_error, request)

		return server.NOT_DONE_YET


class ExperimentsRunning (resource.Resource):

	def __init__ (self):
		resource.Resource.__init__(self)

	def render_GET (self, request):
		result = [{
			'guid': expt.id,
			'sketch_guid': expt.sketch.id,
			'title': expt.sketch.title,
			'user_id': expt.sketch.title,
			'started_date': expt.startTime
		} for expt in running_experiments()]

		_respondWithJSON(result, request)
		return server.NOT_DONE_YET


class ShowExperiment (resource.Resource):

	def __init__ (self, id: str):
		resource.Resource.__init__(self)
		self._id = id

	def render_GET (self, request):
		def _done (exists):
			if not exists:
				request.write(f"Experiment {self._id} not found.".encode('utf-8'))
				request.finish()
				return

			expt = next((expt for expt in running_experiments() if expt.id == self._id), None)

			request.write("<!DOCTYPE html>\n".encode('utf-8'))
			if expt is not None:
				tpl = template.ExperimentRunning(expt)
			else:
				tpl = template.ExperimentResult(
					experiment.CompletedExperiment(self._id)
				)

			d = flatten(request, tpl, request.write)
			d.addCallbacks(lambda _: request.finish())

		d = experiment.Experiment.exists(self._id)
		d.addCallbacks(_done)
		d.addErrback(_error, request)

		return server.NOT_DONE_YET

	def getChild (self, action: bytes, request):
		if action == b"data":
			return GetExperimentData(self._id)
		elif action == b"download":
			return DownloadExperimentData(self._id)
		elif action == b"delete":
			return DeleteExperiment(self._id)
		elif action == b"restore":
			return UndeleteExperiment(self._id)

		return NoResource()


class GetExperimentData (resource.Resource):

	def __init__ (self, id):
		resource.Resource.__init__(self)
		self._id = id

	def render_GET (self, request):
		try:
			variables = list(map(lambda v: v.decode(), request.args[b'var[]']))
		except KeyError:
			variables = []

		start = _getArg(request, b'start', float)
		end = _getArg(request, b'end', float)

		expt = experiment.CompletedExperiment(self._id)
		expt.loadData(variables, start, end)\
			.addCallback(_respondWithJSON, request)\
			.addErrback(_error, request)

		return server.NOT_DONE_YET


class DownloadExperimentData (resource.Resource):

	def __init__ (self, id):
		resource.Resource.__init__(self)
		self._id = id

	@defer.inlineCallbacks
	def _getExperiment (self, id):
		exists = yield experiment.Experiment.exists(self._id)

		if not exists:
			raise Exception("Experiment not found")

		expt = next((expt for expt in running_experiments() if expt.id == id), None)

		if expt is not None:
			raise Exception("Cannot download from running experiment.")

		defer.returnValue(experiment.CompletedExperiment(self._id))

	def render_GET (self, request):
		self._render_GET(request)
		return server.NOT_DONE_YET

	@defer.inlineCallbacks
	def _render_GET (self, request):
		request.write("<!DOCTYPE html>\n".encode('utf-8'))

		try:
			expt = yield self._getExperiment(self._id)
		except Exception as e:
			request.write(f"There was an error: {str(e)}".encode('utf-8'))
			request.finish()
			return

		tpl = template.ExperimentDownload(
			experiment.CompletedExperiment(self._id)
		)

		yield flatten(request, tpl, request.write)

		request.finish()

	def render_POST (self, request):
		self._render_POST(request)
		return server.NOT_DONE_YET

	@defer.inlineCallbacks
	def _render_POST (self, request):
		try:
			expt = yield self._getExperiment(self._id)

			yield expt.load()

			variables = request.args['vars']
			time_divisor = _getArg(request, b'time_divisor', int, None)
			time_dp = _getArg(request, b'time_dp', int, None)
			filename = '.'.join([
				re.sub(r'[^a-zA-Z0-9]+', '_', expt.title).strip('_'),
				time.strftime(
					'%Y%m%d_%H%M%S',
					time.gmtime(expt.finished_date)
				),
				'xlsx'
			])

			xlsxdata = yield expt.buildExcelFile(variables, time_divisor, time_dp)

		except Exception as e:
			request.write("<!DOCTYPE html>\n".encode('utf-8'))
			_error(e, request)
			return

		request.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
		request.setHeader('Content-Disposition', 'attachment; filename=' + filename + ';')

		request.write(xlsxdata)
		request.finish()


class DeleteExperiment (resource.Resource):

	isLeaf = True

	def __init__ (self, id):
		resource.Resource.__init__(self)
		self._id = id

	def render_POST (self, request):
		redirect_url = request.URLPath().parent().parent()

		experiment.Experiment.delete(self._id)\
			.addCallback(_redirectOrJSON, request, redirect_url, { "deleted": str(self._id) })\
			.addErrback(_error, request)

		return server.NOT_DONE_YET


class UndeleteExperiment (resource.Resource):

	isLeaf = True

	def __init__ (self, id):
		resource.Resource.__init__(self)
		self._id = id

	def render_POST (self, request):
		redirect_url = request.URLPath().parent().parent()

		experiment.Experiment.restore(self._id)\
			.addCallback(_redirectOrJSON, request, redirect_url, { "restored": str(self._id) })\
			.addErrback(_error, request)

		return server.NOT_DONE_YET


def makeWebsocketServerFactory (host, port):
	# WebSocket Server
	websocketUrl = "ws://" + str(host) + ":" + str(port)
	template.websocketUrl = websocketUrl

	factory = WebSocketServerFactory(websocketUrl) #, debug = False)
	factory.protocol = websocket.OctopusEditorProtocol
	factory.runtime = websocket_runtime

	def accept (offers):
		# Required for Chromium ~33 and newer
		for offer in offers:
			if isinstance(offer, PerMessageDeflateOffer):
				return PerMessageDeflateOfferAccept(offer)

	factory.setProtocolOptions(perMessageCompressionAccept = accept)

	return factory

def makeHTTPResourcesServerFactory ():
	# HTTP Server
	root = resource.Resource()
	root.putChild(b"", Root())
	root.putChild(b"sketch", Sketch())
	root.putChild(b"experiment", Experiment())

	root.putChild(b"sketches.json", SketchFind())
	root.putChild(b"experiments.json", ExperimentFind())

	rootDir = filepath.FilePath(os.path.join(os.path.dirname(__file__), ".."))
	root.putChild(b"resources", static.File(rootDir.child(b"resources").path))

	return server.Site(root)

def makeConsoleServerFactory ():
	from twisted.conch.insults import insults
	from twisted.conch.manhole import ColoredManhole
	from twisted.conch.manhole_ssh import ConchFactory, TerminalRealm
	from twisted.conch.ssh import keys
	from twisted.cred import checkers, portal

	shell_password = str(uuid.uuid1()).split("-")[0]

	# Note - using unsafe credentials checker.
	checker = checkers.InMemoryUsernamePasswordDatabaseDontUse(octopus=shell_password)

	def chainProtocolFactory():
		return insults.ServerProtocol(
			ColoredManhole,
			dict(
				sketches = loaded_sketches,
				experiments = running_experiments
			)
		)

	rlm = TerminalRealm()
	rlm.chainedProtocolFactory = chainProtocolFactory
	ptl = portal.Portal(rlm, [checker])

	factory = ConchFactory(ptl)
	factory.publicKeys[b"ssh-rsa"] = keys.Key.fromFile(os.path.join(data_path, "ssh-keys", "ssh_host_rsa_key.pub"))
	factory.privateKeys[b"ssh-rsa"] = keys.Key.fromFile(os.path.join(data_path, "ssh-keys", "ssh_host_rsa_key"))

	print ("Octopus SSH access credentials are octopus:%s\n\n" % shell_password)

	return factory


def makeService (options):
	"""
	This will be called from twistd plugin system and we are supposed to
	create and return an application service.
	"""

	application = service.IServiceCollection(
		service.Application("octopus_editor_server", uid = 1, gid = 1)
	)

	ws_factory = makeWebsocketServerFactory(str(options["wshost"]), int(options["wsport"]))
	internet.TCPServer(int(options["wsport"]), ws_factory).setServiceParent(application)

	http_factory = makeHTTPResourcesServerFactory()
	internet.TCPServer(int(options["port"]), http_factory).setServiceParent(application)

	try:
		console_factory = makeConsoleServerFactory()
		internet.TCPServer(int(options["consoleport"]), console_factory).setServiceParent(application)
	except IOError:
		log.err("ERROR: Console could not be started. Create SSH keys using initialise.py before running.")

	return application


def run_server ():
	import sys
	log.startLogging(sys.stdout)

	ws_port = 9000
	ws_factory = makeWebsocketServerFactory("localhost", ws_port)
	reactor.listenTCP(ws_port, ws_factory)
	log.msg("WS listening on port %s" % ws_port)

	http_factory = makeHTTPResourcesServerFactory()
	reactor.listenTCP(8001, http_factory)
	log.msg("HTTP listening on port 8001")

	reactor.run()

	log.msg("Server stopped")


if __name__ == "__main__":
	run_server()
