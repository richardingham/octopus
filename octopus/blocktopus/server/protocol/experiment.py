from time import time as now
from octopus.data import Variable

def _format (variable):
	if variable.value is None:
		if variable.type in (float, int):
			return 0

	if variable.type in (str, int):
		return variable.value

	if variable.type is float:
		return round(variable.value, 2)

	return str(variable)

class ExperimentProtocol (object):
	def __init__ (self, transport):
		self.transport = transport

	def send (self, topic, payload, context):
		self.transport.send('experiment', topic, payload, context)

	def receive (self, topic, payload, sketch, experiment, context):
		try:
			# Experiment control commands
			if sketch is None:
				raise Error("[%s:%s] No Sketch specified" % ('experiment', topic))

			if topic == 'run':
				return sketch.runExperiment(context)
			if topic == 'pause':
				return sketch.pauseExperiment(context)
			if topic == 'resume':
				return sketch.resumeExperiment(context)
			if topic == 'stop':
				return sketch.stopExperiment(context)

			# Experiment interaction commands
			if experiment is None:
				raise Error("[%s:%s] No Experiment specified" % ('experiment', topic))

			if topic == 'load':
				return self.loadExperiment(experiment, context)
			if topic == 'choose-properties':
				return context.chooseExperimentProperties(experiment, payload['properties'])
			if topic == 'choose-streams':
				return context.chooseExperimentStreams(experiment, payload['streams'])
			if topic == 'get-properties':
				return self.sendProperties(sketch, experiment, context.getExperimentProperties(experiment), context)
			if topic == 'get-streams':
				oneoff = 'oneoff' in payload and payload['oneoff']

				if 'streams' in payload:
					streams = payload['streams']
				else:
					streams = context.getExperimentStreams(experiment)

				if 'end' in payload:
					end = payload['end']
				else:
					end = now()

				return self.sendStreams(sketch, experiment, streams, payload['start'], end, context, oneoff)

			if topic == 'set-property':
				return self.setProperty(sketch, experiment, payload['variable'], payload['value'], context)

		except Error as e:
			self.send('error', e, context)
			return

	def loadExperiment (self, experiment, context):
		def _prop (k, p):
			result = {
				"key":   k,
				"name":  p.alias,
				"title": p.title if hasattr(p, "title") else "",
				"unit":  p.unit if hasattr(p, "unit") else "",
				"type":  p.type.__name__ if type(p.type) is not str else p.type,
				"value": _format(p),
				"edit":  hasattr(p, "_setter") or type(p) is Variable
			}

			for key in ("min", "max", "options", "colour"):
				try:
					attr = getattr(p, key)

					if attr is not None:
						result[key] = attr
				except AttributeError:
					pass

			return result

		context.subscribeExperiment(experiment)

		self.send("load", {
			"sketch": experiment.sketch.id,
			"experiment": experiment.id,
			"title": experiment.sketch.title,
			"variables": [_prop(k, v) for k, v in experiment.variables().items()]
		}, context)

	def setProperty (self, sketch, experiment, property, value, context):
		variables = experiment.variables()

		def _sendError (message, e = None):
			self.send("error", {
				"sketch": sketch.id,
				"experiment": experiment.id,
				"message": message + (" (" + str(e) + ")" if e is not None else "")
			}, context)

		try:
			variable = variables[property]
			variable.set(value).addErrback(lambda f: _sendError("Error setting property " + property, f))
		except KeyError:
			_sendError("Property " + property + " does not exist")
		except Exception as e:
			_sendError("Could not set property " + property , e)

	def sendProperties (self, sketch, experiment, properties, context):
		variables = experiment.variables()

		def _value (name):
			try:
				return _format(variables[name])
			except KeyError:
				return None

		return self.send(
			'properties',
			{
				"sketch": sketch.id,
				"experiment": experiment.id,
				"data": {
					name: _value(name)
					for name in properties
				}
			},
			context
		)

	def sendStreams (self, sketch, experiment, streams, start, end, context, oneoff = False):
		variables = experiment.variables()
		interval = end - start

		def _compress (point):
			try:
				return (round(point[0] - start, 1), round(point[1], 2))
			except TypeError:
				return 0

		payload = {
			"sketch": sketch.id,
			"experiment": experiment.id,
			"zero": round(start, 1),
			"max": round(start + interval, 1),
			"data": [
				{
					"name": name,
					"data": list(map(_compress, variables[name].get(start, interval)))
				}
				for name in streams
			]
		}

		if oneoff:
			payload['oneoff'] = True

		return self.send(
			'streams',
			payload,
			context
		)


class Error (Exception):
	pass
