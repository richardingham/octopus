# -*- coding: utf-8 -*-

# Twisted Imports
from twisted.application import internet, service
from twisted.internet import reactor, defer, utils
from twisted.spread import pb
from twisted.python import log
from twisted.web import server, static, resource, guard
from twisted.cred.portal import IRealm, Portal

# Zope Imports
from zope.interface import implements

# Autobahn Imports
from autobahn.websocket import listenWS
from autobahn.wamp import exportRpc, WampServerFactory, WampServerProtocol

# Sibling Imports
import template

# System Imports
import os
from time import time as now

BASE = "http://iego.ch.private.cam.ac.uk/labspiral"

##
## PB Server for experiments to connect to.
##

experiments = {}

def register_experiment (id, expt):
	print "Registered Expt: " + id
	
	experiments[id] = expt

def remove_experiment (id):
	print "Unregistered Expt: " + id

	del experiments[id]


class ExperimentMarshal (pb.Root):
	
	# This will be set when listenWS() is called
	publish = None

	def remote_register (self, id, expt):
		register_experiment (id, expt)
		return 'OK'

	def remote_unregister (self, id):
		remove_experiment (id)
		return 'OK'

	def remote_event (self, id, events):
		for event in events:
			self.publish(BASE + "/event#" + id, event)

		return 'OK'

##
## HTTP Server to list the experiments
##

class Root (resource.Resource):
	def render_GET (self, request):
		return """
			<!DOCTYPE html>
			<html>
			<head>
				<title>Octopus</title>
			</head>
			<body>
				<a href=\"/experiments/\">Experiments</a><br>
				<a href=\"/programs/\">Programs</a>
			</body>
			</html>
		"""


class ExperimentView (resource.Resource):
	def __init__ (self, expt, id):
		resource.Resource.__init__(self)

		self.expt = expt
		self.expt_id = id

	def render_GET (self, request):
		tpl = template.get("experiment.html")
		
		#print "Render expt"

		defers = []
		variables = {
			"experiment_id": self.expt_id
		}

		def got_title (result):
			#print "Received title"
			variables["experiment_title"] = result

		def got_state (result):
			#print "Received state"
			variables["experiment_state"] = result

		def got_tz (result):
			#print "Received tz"
			variables["experiment_time_zero"] = result

		def got_events (result):
			#print "Received ev"
			variables["experiment_events"] = result

		def got_steps (result):
			#print "Received steps"
			variables["experiment_steps"] = result

		def got_ui (result):
			#print "Received ui"
			variables["experiment_machines"] = result

			# get a single list of all property names
			variables["experiment_properties"] = [
				name 
				for list in [
					[prop["name"] for prop in machine["properties"]]
					for machine in result
				]
				for name in list
			]
			
		try:
			defers.append(self.expt.callRemote("title").addCallback(got_title))
			defers.append(self.expt.callRemote("state").addCallback(got_state))
			defers.append(self.expt.callRemote("time_zero").addCallback(got_tz))
			defers.append(self.expt.callRemote("events").addCallback(got_events))
			defers.append(self.expt.callRemote("steps").addCallback(got_steps))
			defers.append(self.expt.callRemote("ui").addCallback(got_ui))
		except pb.DeadReferenceError:
			return "Experiment not connected"

		def done (result):
			try:
				request.write(tpl.render(**variables).encode('utf-8'))
				request.finish()
			except Exception as e:
				import traceback, pprint
				request.write("Exception during rendering<br><br><pre>%s %s</pre>" % (traceback.format_exc(), pprint.pformat(variables)))
				request.finish()

				raise e

		defer.DeferredList(defers, consumeErrors = True).addCallback(done)

		return server.NOT_DONE_YET


class ExperimentList (resource.Resource):
	def render_GET (self, request):
		request.setHeader("Content-type", "text/html; charset='utf-8'")

		response = [ 
			"<!DOCTYPE html>",
			"<html>",
			"<body>"
		]

		def result (result, id):
			return "<li><a href=\"/experiments/" + id + "\">" + result + "</a></li>"

		def done (results):
			links = [x for s, x in results if s is True]

			if len(links):
				response.append("<ul>")
				response.extend([x for s, x in results if s is True])
				response.append("</ul>")
			else:
				response.append("No experiments running")

			response.extend([
				"</body>",
				"</html>"
			])

			request.write("\n".join(response))
			request.finish()

		defers = []
		to_remove = []
		for id, expt in experiments.iteritems():
			if expt is None:
				continue

			try:
				d = expt.callRemote("title")
				d.addCallback(result, id)
				defers.append(d)
			except pb.DeadReferenceError:
				to_remove.append(id)

		for id in to_remove:
			remove_experiment(id)

		defer.DeferredList(defers, consumeErrors = True).addCallback(done)

		return server.NOT_DONE_YET

	def getChild (self, name, request):
		if name == "":
			return self

		try:
			expt = experiments[name]
		except KeyError:
			return resource.NoResource()
		else:
			return ExperimentView(expt, name)


_running_scripts = set()

class ProgramList (resource.Resource):
	def __init__ (self, scripts):
		resource.Resource.__init__(self)

		self._scripts = scripts

	def render_GET (self, request):
		request.setHeader("Content-type", "text/html; charset='utf-8'")

		response = [
			"<!DOCTYPE html>",
			"<html>",
			"<body>"
		]

		def link (id, name):
			if id in _running_scripts:
				return "<li>%s [running]</li>" % name
			else:
				return "<li><a href=\"/programs/run/%d\">%s</a></li>" % (id + 1, name)

		links = [link(id, s[0]) for id, s in enumerate(self._scripts)]

		if len(links):
			response.append("<ul>")
			response.extend(links)
			response.append("</ul>")
		else:
			response.append("No programs available")

		response.extend([
			"</body>",
			"</html>"
		])

		return "\n".join(response)

	def getChild (self, name, request):
		if name == "":
			return self

		if name == "run":
			try:
				id = int(request.postpath.pop(0)) - 1  # This is so that the default will be -1 not 0.
				script = self._scripts[id]
			except IndexError:
				return resource.NoResource(message = "Script #%s is not defined" % id)
			else:
				return ProgramRun(id, script)

		else:
			return resource.NoResource()


class ProgramRun (resource.Resource):

	isLeaf = True

	def __init__ (self, id, script):
		resource.Resource.__init__(self)

		self._script_id = id
		self._script_path = script[1]

	def render_GET (self, request):

		if self._script_id in _running_scripts:
			return "This script is already running"

		def done (result):
			print "Process complete"
			print result
			_running_scripts.discard(self._script_id)

		print "Running Script: %s" % self._script_path
		d = utils.getProcessOutput(self._script_path, reactor = reactor)
		d.addBoth(done)

		_running_scripts.add(self._script_id)

		url = "/experiments/"

		return """
			<!DOCTYPE html>
			<html>
				<head>
					<meta http-equiv=\"refresh\" content=\"10;URL=%(url)s\">
				</head>
				<body bgcolor=\"#FFFFFF\" text=\"#000000\">
					Starting Experiment. Will redirect to the experiment list in 10s.<br>
					Or you can <a href=\"%(url)s\">go to the experiment list now.</a>
				</body>
			</html>""" % { "url": url }


##
## Websocket server for javascripts to connect to.
##
	
class LabspiralServerProtocol (WampServerProtocol):

	monitor = None
	expt_id = None
	monitor_streams = []
	monitor_frequency = 0

	@exportRpc
	def experiment (self, id):
		if self.monitor is not None:
			raise Exception(BASE + "/error#already_monitoring", "You are already monitoring something")

		elif id in experiments:
			self.expt_id = id
			self.monitor = experiments[id]

			self.factory._subscribeClient(self, BASE + "/events#" + id)
			
			print "Monitoring Experiment %s" % id

			def combine (results):
				return {
					"state": results[0][1],
					"events": results[1][1]
				}

			d = defer.DeferredList([
					self.monitor.callRemote("state"), 
					self.monitor.callRemote("events")
				], 
				consumeErrors = True
			).addCallback(combine)

			return d

		else:
			raise Exception(BASE + "/error#unknown_experiment", "This experiment is not connected")

	def machine (self, address):
		pass

	@exportRpc
	def state (self):
		try:
			print "Requesting State"
			return self.monitor.callRemote("state")
		except pb.DeadReferenceError:
			raise Exception(BASE + "/error#experiment_disconnected", "Experiment has disconnected")

	@exportRpc
	def set (self, key, value):
		if self.monitor is None:
			raise Exception(BASE + "/error#not_monitoring", "You are not connected to an experiment")

		try:
			print "Requesting Set: %s -> %s" % (key, value)
			return self.monitor.callRemote("set", key, value)
		except pb.DeadReferenceError:
			raise Exception(BASE + "/error#experiment_disconnected", "Experiment has disconnected")

	@exportRpc
	def control_set (self, control_alias, value):
		if self.monitor is None:
			raise Exception(BASE + "/error#not_monitoring", "You are not connected to an experiment")

		try:
			print "Requesting Control Set: %s -> %s" % (control_alias, value)
			return self.monitor.callRemote("control_set", control_alias, value)
		except pb.DeadReferenceError:
			raise Exception(BASE + "/error#experiment_disconnected", "Experiment has disconnected")

	@exportRpc
	def stream (self, frequency, streams):
		if self.monitor is None:
			raise Exception(BASE + "/error#not_monitoring", "You are not connected to an experiment")

		def streamsOk (result):
			self.last_update = now()
			self.monitor_streams = streams
			self.monitor_frequency = frequency

			return 'OK'

		def streamsNotOk (failure):
			raise Exception(BASE + "/error#bad_streams", "Requested streams are invalid") 

		try:
			return self.monitor.callRemote("check_streams", streams).addCallbacks(streamsOk, streamsNotOk)
		except pb.DeadReferenceError:
			raise Exception(BASE + "/error#experiment_disconnected", "Experiment has disconnected")

	@exportRpc
	def data (self):
		if self.monitor is None:
			raise Exception(BASE + "/error#not_monitoring", "You are not connected to an experiment")

		if len(self.monitor_streams) == 0:
			return None

		# make sure the updates come in consistent steps.
		time_now = now()
		frequency = self.monitor_frequency
		time_now -= time_now % frequency

		# make sure we have a decent time-step (at least one frequency)
		start = self.last_update + frequency 
		interval = time_now - start

		if interval < 0:
			return None

		self.last_update = time_now

		try:
			return self.monitor.callRemote("data", self.monitor_streams, start, interval, frequency)
		except pb.DeadReferenceError:
			raise Exception(BASE + "/error#experiment_disconnected", "Experiment has disconnected")

	@exportRpc
	def properties (self, variables):
		try:
			return self.monitor.callRemote("properties", variables)
		except pb.DeadReferenceError:
			raise Exception(BASE + "/error#experiment_disconnected", "Experiment has disconnected")
		

	@exportRpc
	def all_events (self):
		try:
			return self.monitor.callRemote("events")
		except pb.DeadReferenceError:
			raise Exception(BASE + "/error#experiment_disconnected", "Experiment has disconnected")
		

	def onSessionOpen (self):
		self.registerForRpc(self, BASE + "/monitor#")
		self.registerForPubSub(BASE + "/event#", prefixMatch = True)

		def register (command):
			def fn ():
				if self.monitor is None:
					raise Exception(BASE + "/error#not_monitoring", "You are not monitoring an experiment")
				try:
					return self.monitor.callRemote(command)
				except pb.NoSuchMethod:
					raise Exception(BASE + "/error#not_an_experiment", "You are not monitoring an experiment")
				except pb.DeadReferenceError:
					raise Exception(BASE + "/error#experiment_disconnected", "Experiment has disconnected")

			self.registerProcedureForRpc(BASE + "/monitor#" + command, fn)

		for command in ["start", "stop", "pause", "resume"]:
			register(command)

		def discardPub (topic, id, event):
			return False

		self.registerHandlerForPub(BASE + "/event#", None, discardPub, prefixMatch = True)


#
# Run server
#

#import pkg_resources
#from autobahn.resource import WebSocketResource, HTTPChannelHixie76Aware

class WampService (service.Service):
	"""
	Wamp service - this runs a Twisted Web site with a labspiral
	Wamp server running under path "/ws".
	"""

	def __init__(self, port = 9000, debug = False):
		self.port = port
		self.debug = debug

		factory = WampServerFactory("ws://localhost:%d" % self.port, debug = self.debug)
		factory.protocol = LabspiralServerProtocol
		factory.setProtocolOptions(allowHixie76 = True) # needed if Hixie76 is to be supported
		self.factory = factory

	def startService(self):

		## FIXME: Site.start/stopFactory should start/stop factories wrapped as Resources
		self.factory.startFactory()
		
		## we serve static files under "/" ..
		#webdir = os.path.abspath(pkg_resources.resource_filename("echows", "web"))
		#root = static.File(webdir)

		## and our WebSocket server under "/ws"
		##resource = WebSocketResource(self.factory)
		#root.putChild("ws", resource)

		## both under one Twisted Web Site
		#site = server.Site(root)
		#site.protocol = HTTPChannelHixie76Aware # needed if Hixie76 is to be supported

		#self.site = site
		#self.listener = reactor.listenTCP(self.port, site)
		self.listener = reactor.listenTCP(self.port, self.factory)

	def stopService(self):
		self.factory.stopFactory()
		#self.site.stopFactory()
		self.listener.stopListening()

def makeService (options):
	"""
	This will be called from twistd plugin system and we are supposed to
	create and return our application service.
	"""

	application = service.IServiceCollection(
		service.Application("octopus_server", uid = 1, gid = 1)
	)

	wamp_service = WampService(
		int(options["wampport"]), 
		debug = False
	)
	wamp_service.setServiceParent(application)

	ExperimentMarshal.publish = wamp_service.factory.dispatch
	internet.TCPServer(
		int(options["pbport"]),
		pb.PBServerFactory(ExperimentMarshal())
	).setServiceParent(application)
	
	resources_path = os.path.join(os.path.dirname(__file__), "resources")

	# class ExperimentListRealm (object):
		# """
		# A realm which gives out L{ExperimentList} instances for authenticated
		# users.
		# """
		# implements(IRealm)

		# def requestAvatar(self, avatarId, mind, *interfaces):
			# if resource.IResource in interfaces:
				# return resource.IResource, ExperimentList(), lambda: None
			# raise NotImplementedError()

	#from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
	#checkers = [InMemoryUsernamePasswordDatabaseDontUse(joe='blow')]
	#wrapper = guard.HTTPAuthSessionWrapper(
	#	Portal(ExperimentListRealm(), checkers),
	#	[guard.DigestCredentialFactory('md5', 'example.com')])

	# Read in preconfigured scripts list
	if options["scripts"] is not None:
		try:
			with open(options["scripts"]) as f:
				scripts = [line.split("\t") for line in f.readlines()]
				scripts = [(s[0], s[1].strip()) for s in scripts if len(s) is 2]
		except IOError:
			scripts = []
	else:
		scripts = []

	root = resource.Resource()
	root.putChild("", Root())
	#root.putChild("experiments", wrapper)
	root.putChild("experiments", ExperimentList())
	root.putChild("programs", ProgramList(scripts))
	root.putChild("resources", static.File(resources_path))
	site = server.Site(root)
	internet.TCPServer(
		int(options["port"]),
		site
	).setServiceParent(application)

	return application

def run_server ():
	reactor.listenTCP(8789, pb.PBServerFactory(ExperimentMarshal()))
	log.msg("PB listening on port 8789")

	factory = WampServerFactory("ws://localhost:9000")
	factory.protocol = LabspiralServerProtocol
	listenWS(factory)
	log.msg("WS listening on port 9000")

	ExperimentMarshal.publish = factory.dispatch

	root = resource.Resource()
	root.putChild("", Root())
	root.putChild("experiments", ExperimentList())
	root.putChild("resources", static.File("resources"))
	site = server.Site(root)
	reactor.listenTCP(8001, site)
	log.msg("HTTP listening on port 8001")

	reactor.run()

	log.msg("Server stopped")

if __name__ == "__main__":
	run_server()
