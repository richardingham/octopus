from twisted.web.template import Element, renderer, XMLFile as Twisted_XMLFile, Tag
from twisted.python.filepath import FilePath

import os
import json
import time
import datetime

blocktopus_dir = os.path.join(os.path.dirname(__file__), "..")
templates_dir = FilePath(os.path.join(blocktopus_dir, "templates"))
resources_dir = os.path.join(blocktopus_dir, "resources", "cache")
resources_json = os.path.join(blocktopus_dir, "templates", "template-resources.json")

resources_uri = '/resources/cache/'
websocket_url = "ws://localhost:9000"

with open(resources_json) as templates_file:
    resources = json.load(templates_file)


class XMLFile (Twisted_XMLFile):
	def getTemplateName (self):
		return os.path.splitext(self._path.basename())[0]


class ElementWithCachedResources (Element):
	@renderer
	def cached_js (self, request, tag):
		for src in resources[self.loader.getTemplateName()].keys():
			if os.path.splitext(src)[1] != '.js':
				continue

			yield tag.clone().fillSlots(
				src = resources_uri + src
			)

	@renderer
	def cached_css (self, request, tag):
		for src in resources[self.loader.getTemplateName()].keys():
			if os.path.splitext(src)[1] != '.css':
				continue

			yield tag.clone().fillSlots(
				src = resources_uri + src
			)


class Root (ElementWithCachedResources):
	loader = XMLFile(templates_dir.child('root.xml'))

	def __init__ (self, running_experiments, past_experiments, saved_sketches):
		Element.__init__(self)
		self.running_experiments = running_experiments
		self.past_experiments = past_experiments
		self.saved_sketches = saved_sketches

	@renderer
	def running_experiment (self, request, tag):
		if len(self.running_experiments):
			for expt in self.running_experiments:
				yield tag.clone().fillSlots(
					url = "/experiment/{:s}".format(expt.id),
					title = expt.sketch.title,
					duration = str(datetime.timedelta(seconds = int(
						time.time() - expt.startTime
					)))
				)
		else:
			yield Tag('div',
				children = ['No running experiments'],
				attributes = {
				'class': 'list-group-item'
				}
			)

	@renderer
	def past_experiment (self, request, tag):
		def _done (expts):
			def _render ():
				for expt in expts:
					yield tag.clone().fillSlots(
						guid = expt['guid'],
						url = "/experiment/{:s}".format(expt['guid']),
						delete_url = "/experiment/{:s}/delete".format(expt['guid']),
						download_url = "/experiment/{:s}/download".format(expt['guid']),
						title = expt['title'],
						finished_date = time.strftime(
							'%d %b %Y, %H:%M',
							time.gmtime(expt['finished_date'])
						),
						finished_date_raw = str(expt['finished_date']),
						duration = str(datetime.timedelta(seconds = int(
							expt['duration']
						))),
						duration_raw = str(expt['duration'])
					)

			return _render()

		return self.past_experiments.addCallback(_done)

	@renderer
	def saved_sketch (self, request, tag):
		def _done (sketches):
			def _render ():
				for sketch in sketches:
					yield tag.clone().fillSlots(
						guid = sketch['guid'],
						url = "/sketch/{:s}".format(sketch['guid']),
						delete_url = "/sketch/{:s}/delete".format(sketch['guid']),
						copy_url = "/sketch/{:s}/copy".format(sketch['guid']),
						title = sketch['title'],
						modified_date = time.strftime(
							'%d %b %Y, %H:%M',
							time.gmtime(sketch['modified_date'])
						),
						modified_date_raw = str(sketch['modified_date'])
					)

			return _render()

		return self.saved_sketches.addCallback(_done)


class SketchEdit (ElementWithCachedResources):
	loader = XMLFile(templates_dir.child('sketch-edit.xml'))

	def __init__ (self, sketch_id):
		Element.__init__(self)
		self.sketch_id = sketch_id

	@renderer
	def editor_body (self, request, tag):
		return tag.fillSlots(
			websocket_url = websocket_url,
			sketch_id = self.sketch_id
		)

	@renderer
	def plugin_machines (self, request, tag):
		from octopus.blocktopus.blocks.machines import machine_declaration
		from octopus.blocktopus.workspace import get_block_plugin_block_names
		
		for block_name in sorted(get_block_plugin_block_names(machine_declaration)):
			yield tag.clone().fillSlots(
				type = block_name
			)

	@renderer
	def plugin_connections (self, request, tag):
		from octopus.blocktopus.blocks.machines import connection_declaration
		from octopus.blocktopus.workspace import get_block_plugin_block_names
		
		for block_name in sorted(get_block_plugin_block_names(connection_declaration)):
			yield tag.clone().fillSlots(
				type = block_name
			)


class ExperimentResult (ElementWithCachedResources):
	loader = XMLFile(templates_dir.child('experiment-result.xml'))

	def __init__ (self, expt):
		Element.__init__(self)
		self.expt = expt
		self._load = expt.load()

	@renderer
	def body (self, request, tag):
		def _done (result):
			return tag.fillSlots(
				sketch_url = "/sketch/{:s}".format(self.expt.sketch_id),
				download_url = "/experiment/{:s}/download".format(self.expt.id),
				data_url = "/experiment/{:s}/data".format(self.expt.id),
				id = self.expt.id,
				title = self.expt.title,
				sketch_id = self.expt.sketch_id,
				started_date = str(self.expt.started_date),
				finished_date = str(self.expt.finished_date),
				variables = json.dumps(self.expt.variables)
			)

		return self._load.addCallback(_done)


class ExperimentDownload (ElementWithCachedResources):
	loader = XMLFile(templates_dir.child('experiment-download.xml'))

	def __init__ (self, expt):
		Element.__init__(self)
		self.expt = expt
		self._load = expt.load()

	@renderer
	def variable (self, request, tag):
		def _done (_):
			def _render ():
				for v in self.expt.variables:
					yield tag.clone().fillSlots(
						key = v['key'],
						name = v['name'],
						type = v['type'],
						unit = v['unit'],
					)

			return _render()

		return self._load.addCallback(_done)


class ExperimentRunning (ElementWithCachedResources):
	loader = XMLFile(templates_dir.child('experiment-running.xml'))

	def __init__ (self, experiment):
		Element.__init__(self)
		self.experiment = experiment

	@renderer
	def editor_body (self, request, tag):
		return tag.fillSlots(
			websocket_url = websocketUrl,
			sketch_id = self.experiment.sketch.id,
			experiment_id = self.experiment.id,
			title = self.experiment.sketch.title,
			started_date = str(self.experiment.startTime)
		)
