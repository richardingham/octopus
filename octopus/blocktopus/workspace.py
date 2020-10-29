# Twisted Imports
from twisted.internet import reactor, defer, task
from twisted.python import log

# Octopus Imports
from octopus.sequence.util import Runnable, Pausable, Cancellable, BaseStep
from octopus.sequence.error import NotRunning, AlreadyRunning, NotPaused
from octopus.constants import State
from octopus.data.data import BaseVariable
from octopus.machine import Component
from octopus.events import EventEmitter

# Debugging
defer.Deferred.debug = True

def _subclasses (cls):
	return cls.__subclasses__() + [
		g for s in cls.__subclasses__()
		for g in _subclasses(s)
	]

def get_block_plugin_modules ():
	# Add plugin machine blocks
	# https://packaging.python.org/guides/creating-and-discovering-plugins/
	import importlib
	import pkgutil
	import octopus.blocks

	def iter_namespace(ns_pkg):
		# Specifying the second argument (prefix) to iter_modules makes the
		# returned name an absolute name instead of a relative one. This allows
		# import_module to work without having to do additional modification to
		# the name.
		return pkgutil.walk_packages(ns_pkg.__path__, ns_pkg.__name__ + ".")

	return {
		name: importlib.import_module(name)
		for finder, name, ispkg
		in iter_namespace(octopus.blocks)
	}


def get_block_plugin_block_names (check_subclass):
	return [
		name 
		for mod in get_block_plugin_modules().values()
		for name, cls in mod.__dict__.items() 
		if isinstance(cls, type) 
			and issubclass(cls, check_subclass)
			and cls is not check_subclass
	]


def get_machine_js_definitions ():
	from octopus.blocktopus.blocks.machines import machine_declaration

	for block_cls in _subclasses(machine_declaration):
		try:
			yield (block_cls.__name__, block_cls.get_interface_definition())
		except AttributeError:
			pass


def get_connection_js_definitions ():
	from octopus.blocktopus.blocks.machines import connection_declaration

	for connection_cls in _subclasses(connection_declaration):
		try:
			yield (connection_cls.__name__, connection_cls.get_interface_definition())
		except AttributeError:
			pass


def populate_blocks ():
	from .blocks import mathematics, text, logic, controls, variables, machines, dependents, images, colour
	get_block_plugin_modules()

	Workspace.blocks = { c.__name__: c for c in _subclasses(Block) }


class Workspace (Runnable, Pausable, Cancellable, EventEmitter):
	blocks = {}

	def __init__ (self):
		self.state = State.READY

		self.allBlocks = {}
		self.topBlocks = {}
		self.variables = Variables()

	def addBlock (self, id, type, fields = None, x = 0, y = 0):
		try:
			blockType = type
			blockClass = self.blocks[blockType]
		except KeyError:
			raise Exception("Unknown Block: %s" %  blockType)

		block = blockClass(self, id)
		block.position = [x, y]

		try:
			for field, value in fields.items():
				block.fields[field] = value
		except AttributeError:
			pass

		block.created()

		self.allBlocks[block.id] = block
		self.topBlocks[block.id] = block

		self.emit('top-block-added', block = block)

	def getBlock (self, id):
		try:
			return self.allBlocks[id]
		except KeyError:
			print("Attempted to access unconnected block {:s}".format(str(id)))
			raise

	def removeBlock (self, id):
		block = self.getBlock(id)

		try:
			del self.topBlocks[block.id]
		except KeyError:
			pass

		# Disconnect prevBlock connection
		prev = block.prevBlock
		if prev is not None:
			if prev.nextBlock == block:
				prev.disconnectNextBlock(block)
			else:
				prevInputs = prev.inputs
				for input in prevInputs.keys():
					if prevInputs[input] is block:
						prev.disconnectInput(input, "value")

		# Disconnect nextBlock connection
		next = block.nextBlock
		if next is not None:
			if next.prevBlock == block:
				block.disconnectNextBlock(next)

		# Disconnect output connection
		output = block.outputBlock
		if output is not None:
			outputInputs = output.inputs
			for input in outputInputs.keys():
				if outputInputs[input] is block:
					output.disconnectInput(input, "value")

		try:
			del self.allBlocks[block.id]
		except KeyError:
			pass

		self.emit('top-block-removed', block = block)
		block.disposed()

	def connectBlock (self, id, parent, connection, input = None):
		childBlock = self.getBlock(id)
		parentBlock = self.getBlock(parent)

		if id in self.topBlocks:
			del self.topBlocks[id]

		if connection == "input-value":
			parentBlock.connectInput(input, childBlock, "value")
		elif connection == "input-statement":
			parentBlock.connectInput(input, childBlock, "statement")
		elif connection == "previous":
			parentBlock.connectNextBlock(childBlock)

		self.emit('top-block-removed', block = childBlock)

	def disconnectBlock (self, id, parent, connection, input = None):
		childBlock = self.getBlock(id)
		parentBlock = self.getBlock(parent)

		self.topBlocks[id] = childBlock

		if connection == "input-value":
			parentBlock.disconnectInput(input, "value")
		elif connection == "input-statement":
			parentBlock.disconnectInput(input, "statement")
		elif connection == "previous":
			parentBlock.disconnectNextBlock(childBlock)

		self.emit('top-block-added', block = childBlock)

	#
	# Controls
	#

	def _run (self):
		self._complete = defer.Deferred()
		dependencyGraph = []
		runningBlocks = set()
		externalStopBlocks = set()
		resumeBlocks = []
		self.emit("workspace-started")

		def _runBlock (block):
			if self.state is State.PAUSED:
				self._onResume = _onResume
				resumeBlocks.append(block)
				return

			if block.externalStop:
				externalStopBlocks.add(block)
			else:
				runningBlocks.add(block)

			# Run in the next tick so that dependency graph
			# and runningBlocks are all updated before blocks
			# are run (and potentially finish)
			d = task.deferLater(reactor, 0, block.run)
			d.addCallbacks(
				callback = _blockComplete,
				callbackArgs = [block],
				errback = _blockError,
				errbackArgs = [block]
			)
			d.addErrback(log.err)

		def _onResume ():
			for block in resumeBlocks:
				_runBlock(block)

			resumeBlocks = []

		def _blockComplete (result, block):
			if block.externalStop:
				return

			runningBlocks.discard(block)
			decls = block.getGlobalDeclarationNames()

			# Check if any other blocks can be run
			toRun = []
			for item in dependencyGraph:
				for decl in decls:
					item["deps"].discard(decl)

				if len(item["deps"]) == 0:
					toRun.append(item)

			# _runBlock needs to be called in the next tick (done in _runBlock)
			# so that the dependency graph is updated before any new blocks run.
			for item in toRun:
				dependencyGraph.remove(item)
				item["block"].off("connectivity-change", item["onConnectivityChange"])
				_runBlock(item["block"])

			# Check if the experiment can be finished
			reactor.callLater(0, _checkFinished)

		def _blockError (failure, block):
			if failure.type is Disconnected:
				return _blockComplete(None, block)

			# If any one step fails, cancel the rest.
			if not _blockError.called:
				log.msg("Received error %s from block %s. Aborting." % (failure, block.id))

				def _errback (error):
					# Pass the error if this is called as errback, or else
					# the original failure if abort() had no errors.
					# Call later to try to allow any other block-state events
					# to propagate before the listeners are cancelled.
					if not self._complete.called:
						_externalStop()
						self.state = State.ERROR
						reactor.callLater(0, self._complete.errback, error or failure)

					self.emit("workspace-stopped")
					_blockError.called = True

				try:
					self.abort().addBoth(_errback)
				except NotRunning:
					pass

		# Allow access to called within scope of _blockError
		_blockError.called = False

		def _updateDependencyGraph (data = None, block = None):
			toRemove = []

			for item in dependencyGraph:
				if block is not None and item['block'] is not block:
					continue

				# If a block is no longer a top block, remove it
				# from the dependency graph
				if item['block'].prevBlock is not None:
					toRemove.append(item)
					continue

				# Update dependency list
				item['deps'] = set(item['block'].getUnmatchedVariableNames())

			for item in toRemove:
				item['block'].off('connectivity-change', item['onConnectivityChange'])
				dependencyGraph.remove(item)

		# When a new top block is added, add it to the list of blocks that must
		# complete before the run can be finished; or to the list of blocks that
		# must be stopped when the run finishes, if appropriate.
		@self.on('top-block-added')
		def onTopBlockAdded (data):
			block = data['block']

			if block._complete is not None and block._complete.called is False:
				if block.externalStop:
					externalStopBlocks.add(block)
				else:
					runningBlocks.add(block)

				block._complete.addCallbacks(
					callback = _blockComplete,
					callbackArgs = [block],
					errback = _blockError,
					errbackArgs = [block]
				).addErrback(log.err)

			_updateDependencyGraph()

		self.on('top-block-removed', _updateDependencyGraph)

		# If there are no more running blocks, stop running.
		def _checkFinished (error = None):
			log.msg("Finished?: Waiting for %s blocks" % len(runningBlocks))

			if len(runningBlocks) > 0:
				return

			log.msg("Skipped blocks:" + str(dependencyGraph))

			if not (_blockError.called or self._complete.called):
				_externalStop()
				self.state = State.COMPLETE
				self._complete.callback(None)
				_removeListeners()

		def _removeListeners ():
			self.emit("workspace-stopped")
			self.off('top-block-added', onTopBlockAdded)
			self.off('top-block-removed', _updateDependencyGraph)

			for item in dependencyGraph:
				item['block'].off('connectivity-change', item['onConnectivityChange'])

		# Cancel all blocks which must be stopped externally.
		def _externalStop ():
			for block in externalStopBlocks:
				try:
					block.cancel(propagate = True).addErrback(log.err)
				except NotRunning:
					pass

		# Set up the dependency graph
		allDeclaredGlobalVariables = set()
		blocksToRunImmediately = []
		dependencyError = False

		# Create a list of all global variables defined in the workspace
		for block in self.topBlocks.values():
			allDeclaredGlobalVariables.update(block.getGlobalDeclarationNames())

		def _generateOnConnectivityChange (block):
			def onConnectivityChange (data):
				_updateDependencyGraph(block = block)

			return onConnectivityChange

		# Defer blocks with dependencies until these have been met.
		for block in self.topBlocks.values():
			deps = set(block.getUnmatchedVariableNames())

			# Check that all of these dependencies will be met.
			for dep in deps:
				if dep not in allDeclaredGlobalVariables:
					self.emit(
						"log-message",
						level = "error",
						message = "Referenced variable {:s} is never defined. ".format(dep),
						block = block.id
					)
					dependencyError = True

			if len(deps) == 0:
				log.msg("Block %s has no deps, running now" % block.id)
				blocksToRunImmediately.append(block)

			else:
				log.msg("Block %s waiting for %s" % (block.id, deps))

				onConnectivityChange = _generateOnConnectivityChange(block)
				block.on("connectivity-change", onConnectivityChange)

				dependencyGraph.append({
					"block": block,
					"deps": deps,
					"onConnectivityChange": onConnectivityChange
				})

		# If there are no blocks that have no dependencies, then
		# there must be a circular dependency somewhere!
		if len(blocksToRunImmediately) == 0:
			self.emit(
				"log-message",
				level = "error",
				message = "No blocks can run."
			)
			dependencyError = True

		# Check for circular dependencies using a topological sorting algorithm
		def findCircularDependencies (blocks, graph):
			circularDeps = []

			while len(blocks) > 0:
				block = blocks.pop()
				toRemove = []

				for item in graph:
					for decl in block["decls"]:
						item["deps"].discard(decl)

					if len(item["deps"]) == 0:
						toRemove.append(item)

				for item in toRemove:
					graph.remove(item)
					blocks.append(item)

			# Remove any blocks that just depend on one of the
			# circularly-dependent blocks
			toRemove = []
			for item in graph:
				if len(item["decls"]) == 0:
					toRemove.append(item)

			for item in toRemove:
				graph.remove(item)

			return graph

		circularDeps = findCircularDependencies(
			blocks = [{
				"block": block.id,
				"position": block.position,
				"decls": block.getGlobalDeclarationNames()
			} for block in blocksToRunImmediately],
			graph = [{
				"block": item["block"].id,
				"position": item["block"].position,
				"deps": item["deps"].copy(),
				"decls": item["block"].getGlobalDeclarationNames()
			} for item in dependencyGraph]
		)

		if len(circularDeps) > 0:
			self.emit(
				"log-message",
				level = "error",
				message = "Circular dependencies detected:"
			)

			for item in sorted(
				circularDeps, key = lambda item: item["position"]
			):
				self.emit(
					"log-message",
					level = "error",
					message = "* {:s} depends on {:s}".format(
						', '.join(item["decls"]),
						', '.join(item["deps"])
					),
					block = item["block"]
				)

			dependencyError = True

		# Do not run if there was an error with the dependencies.
		if dependencyError:
			self.state = State.COMPLETE
			self._complete.errback(Exception("Dependency errors prevented start."))
			_removeListeners()

		# Run blocks with no dependencies in order of their position.
		# Blocks are sorted first by x then by y.
		else:
			for block in sorted(
				blocksToRunImmediately, key = lambda b: b.position
			):
				_runBlock(block)

		return self._complete

	def _reset (self):
		results = []
		for block in self.topBlocks.values():
			try:
				results.append(block.reset())
			except AlreadyRunning:
				pass

		return defer.DeferredList(results)

	def _pause (self):
		results = []
		for block in self.topBlocks.values():
			try:
				results.append(block.pause())
			except NotRunning:
				pass

		self.emit("workspace-paused")
		return defer.DeferredList(results)

	def _resume (self):
		results = []
		for block in self.topBlocks.values():
			try:
				block.resume()
			except NotPaused:
				pass

		self.emit("workspace-resumed")
		return defer.DeferredList(results)

	def _cancel (self, abort = False):
		results = []
		for block in self.topBlocks.values():
			try:
				block.cancel(abort)
			except NotRunning:
				pass

		return defer.DeferredList(results)

	#
	# Serialisation
	#

	def toEvents (self):
		events = []
		for block in self.topBlocks.values():
			events.extend(block.toEvents())

		return events

	def fromEvents (self, events):
		for e in events:
			if "block" in e['data']:
				e['data']['id'] = e['data']['block']
			event = Event.fromPayload(e['type'], e['data'])
			event.apply(self)


class Variables (EventEmitter):
	def __init__ (self):
		self._variables = {}
		self._handlers = {}

	def add (self, name, variable):
		if name in self._variables:
			if self._variables[name] is variable:
				return

			self.remove(name)

		self._variables[name] = variable

		def _makeHandler (name):
			def onChange (data):
				self.emit('variable-changed', name = name, **data)

			return onChange

		if isinstance(variable, BaseVariable):
			onChange = _makeHandler(name)
			variable.on('change', onChange)
			self._handlers[name] = onChange
			self.emit('variable-added', name = name, variable = variable)

		elif isinstance(variable, Component):
			handlers = {}
			for attrname, attr in variable.variables.items():
				onChange = _makeHandler(attrname)
				attr.on('change', onChange)
				handlers[attrname] = onChange
				self._variables[attrname] = attr
				self.emit('variable-added', name = attrname, variable = variable)

			self._handlers[name] = handlers

		else:
			self._handlers[name] = None

	def remove (self, name):
		try:
			variable = self._variables[name]
		except KeyError:
			return

		if isinstance(variable, BaseVariable):
			variable.off(
				'change',
				self._handlers[name]
			)
			self.emit('variable-removed', name = name, variable = variable)

		elif isinstance(variable, Component):
			for attrname, attr in variable.variables.items():
				attr.off(
					'change',
					self._handlers[name][attrname]
				)
				self.emit('variable-removed', name = attrname, variable = variable)
				del self._variables[attrname]

		del self._variables[name]
		del self._handlers[name]

	def rename (self, oldName, newName):
		log.msg("Renaming variable: %s to %s" % (oldName, newName))

		if oldName == newName:
			return

		try:
			variable = self._variables[oldName]
		except KeyError:
			return

		if isinstance(variable, Component):
			oldNames = [name for name, var in variable.variables.items()]
		else:
			oldNames = [oldName]

		variable.alias = newName

		for name in oldNames:
			variable = self._variables[name]
			newName = variable.alias

			self._variables[newName] = self._variables[name]
			self._handlers[newName] = self._handlers[name]
			del self._variables[name]
			del self._handlers[name]

			self.emit('variable-renamed',
				oldName = name,
				newName = newName,
				variable = variable
			)

	def get (self, name):
		try:
			return self._variables[name]
		except KeyError:
			return None

	__getitem__ = get
	__setitem__ = add
	__delitem__ = remove

	def items (self):
		return self._variables.items()

	def values (self):
		return self._variables.values()


def anyOfStackIs (block, states):
	while block:
		if block.state in states:
			return True

		block = block.nextBlock


class Block (BaseStep, EventEmitter):

	# If this block needs to be stopped by the workspace
	# (e.g. long-running disconnected controls)
	# TODO: make this more general - this ought to be True
	# for any block with an output connection which is started
	# by eval() rather than run()
	externalStop = False

	# If this block returns an output, the output data type
	# may be specified. Useful if the block does not return a
	# value immediately.
	outputType = None

	@property
	def state (self):
		return self._state

	@state.setter
	def state (self, value):
		self._state = value
		self.workspace.emit("block-state", block = self.id, state = value.name)

	@property
	def disabled (self):
		try:
			return self._disabled
		except AttributeError:
			return False

	@disabled.setter
	def disabled (self, disabled):
		self._disabled = bool(disabled)

		try:
			if disabled:
				self.cancel(propagate = False)
			else:
				self.reset(propagate = False)
		except (NotRunning, AlreadyRunning):
			pass

		self.emit("connectivity-changed")

	def __init__ (self, workspace, id):
		self.workspace = workspace
		self.id = id
		self.type = self.__class__.__name__
		self.state = State.READY
		self.nextBlock = None
		self.prevBlock = None
		self.outputBlock = None
		self.parentInput = None
		self._complete = None
		self.fields = {}
		self.inputs = {}
		self.mutation = ""
		self.comment = ""
		#self._addedInputs = []
		self.collapsed = False
		self.disabled = False
		self.position = [0, 0]
		self.inputsInline = None

	def created (self):
		pass

	def disposed (self):
		pass

	def emitLogMessage (self, message, level):
		self.workspace.emit(
			"log-message",
			level = level,
			message = message,
			block = self.id
		)

	def connectNextBlock (self, childBlock):
		if self.nextBlock is not None:
			raise Exception("Block.connectNextBlock (#%s): parent #%s already has a next Block" % (childBlock.id, self.id))
		if childBlock.prevBlock is not None:
			raise Exception("Block.connectNextBlock (#%s): child #%s already has a previous Block" % (self.id, childBlock.id))

		self.nextBlock = childBlock
		childBlock.prevBlock = self
		childBlock.parentInput = None

		if self.state in (State.RUNNING, State.PAUSED):
			try:
				childBlock.reset()
			except AlreadyRunning:
				pass
		else:
			if anyOfStackIs(childBlock, [State.RUNNING, State.PAUSED]):
				if childBlock._complete is not None:
					self._complete = defer.Deferred()
					childBlock._complete.addCallbacks(self._complete.callback, self._complete.errback)
			elif self.state is State.READY:
				try:
					childBlock.reset()
				except AlreadyRunning:
					pass

		@childBlock.on('connectivity-changed')
		def onConnChange (data):
			self.emit('connectivity-changed', **data)

		@childBlock.on('value-changed')
		def onValueChange (data):
			self.emit('value-changed', **data)

		@self.on('disconnected')
		def onDisconnect (data):
			if "next" in data and data['next'] is True:
				childBlock.off('connectivity-changed', onConnChange)
				childBlock.off('value-changed', onValueChange)
				self.off('disconnected', onDisconnect)

		self.emit('connectivity-changed')

	def disconnectNextBlock (self, childBlock):
		if self.nextBlock != childBlock:
			raise Exception("Block.disconnectNextBlock: must pass the correct child block")

		# Cancel parent block if waiting for data
		try:
			if not childBlock._complete.called:
				childBlock._complete.errback(Disconnected())
				childBlock._complete = defer.Deferred()
		except AttributeError:
			pass

		self.nextBlock = None
		childBlock.prevBlock = None
		childBlock.parentInput = None

		self.emit('disconnected', next = True)
		self.emit('connectivity-changed')

	def getSurroundParent (self):
		block = self

		while block is not None:
			if block.outputBlock is not None:
				block = block.outputBlock
				continue

			prev = block.prevBlock

			if prev.nextBlock is block:
				block = prev
			else:
				return prev

		return None

	def getChildren (self):
		children = []

		for block in self.inputs.values():
			if block is not None:
				children.append(block)

		if self.nextBlock is not None:
			children.append(self.nextBlock)

		return children

	def setFieldValue (self, fieldName, value):
		oldValue = self.getFieldValue(fieldName)

		self.fields[fieldName] = value
		self.emit('value-changed',
			block = self,
			field = fieldName,
			oldValue = oldValue,
			newValue = value
		)

	def getFieldValue (self, fieldName, default = None):
		try:
			return self.fields[fieldName]
		except KeyError:
			return default

	def getInput (self, inputName):
		return self.inputs[inputName]

	def getInputValue (self, inputName, default = False):
		try:
			input = self.inputs[inputName]
		except KeyError:
			input = None

		if input is None:
			return defer.succeed(default)

		def error (failure):
			failure.trap(Cancelled, Disconnected)
			return default

		return input.eval().addErrback(error)

	def connectInput (self, inputName, childBlock, type):
		if type == "value":
			childBlock.outputBlock = self
		elif type == "statement":
			childBlock.prevBlock = self
		else:
			raise Exception("Block.connectInput: invalid type %s" % type)

		self.inputs[inputName] = childBlock
		childBlock.parentInput = inputName

		if type == "value":
			if self.state is State.READY:
				try:
					childBlock.reset()
				except AlreadyRunning:
					pass
			elif self.state is State.RUNNING:
				try:
					childBlock.reset()
					childBlock.run()
				except AlreadyRunning:
					pass
			elif self.state is State.PAUSED:
				if childBlock.state is State.PAUSED:
					pass
				elif childBlock.state is State.RUNNING:
					childBlock.pause()
				else:
					# Should not raise AlreadyRunning due to two if's above
					childBlock.reset()

					# Do not call run() because most input blocks will be eval()ed.
					# Parent blocks expecting to run() children should run them
					# again when they are resumed.
			else:
				try:
					childBlock.cancel()
				except NotRunning:
					pass

		@childBlock.on('connectivity-changed')
		def onConnChange (data):
			self.emit('connectivity-changed', **data)

		@childBlock.on('value-changed')
		def onValueChange (data):
			self.emit('value-changed', **data)

		@self.on('disconnected')
		def onDisconnect (data):
			if "input" in data and data['input'] == inputName:
				childBlock.off('connectivity-changed', onConnChange)
				childBlock.off('value-changed', onValueChange)
				self.off('disconnected', onDisconnect)

		self.emit('connectivity-changed')
		self.workspace.emit('top-block-removed', block = childBlock)

	def disconnectInput (self, inputName, type):
		try:
			childBlock = self.inputs[inputName]
		except KeyError:
			return

		# Cancel parent block if waiting for data
		try:
			if not childBlock._complete.called:
				childBlock._complete.errback(Disconnected())
				childBlock._complete = defer.Deferred()
		except AttributeError:
			pass

		if type == "value":
			childBlock.outputBlock = None
		elif type == "statement":
			childBlock.prevBlock = None
		else:
			raise Exception("Block.disconnectInput: invalid type %s" % type)

		self.inputs[inputName] = None
		childBlock.parentInput = None

		self.emit('disconnected', input = inputName)
		self.emit('connectivity-changed')
		self.workspace.emit('top-block-added', block = childBlock)

	def getReferencedVariables (self, variables = None):
		variables = variables or []

		for block in self.getChildren():
			variables.extend(block.getReferencedVariables())

		return variables

	def getReferencedVariableNames (self, variables = None):
		variables = variables or []

		for block in self.getChildren():
			variables.extend(block.getReferencedVariableNames())

		return variables

	def getGlobalDeclarationNames (self, variables = None):
		""" Returns a list of global variable names
		that are declared within this block.

		Note: This function must not return any local
		variable names, because this will look like a
		circular dependency.
		"""

		variables = variables or []

		for block in self.getChildren():
			variables.extend(block.getGlobalDeclarationNames())

		return variables

	def getUnmatchedVariableNames (self, variables = None):
		""" Find variables that must be defined in a higher scope.

		Returns a list of referenced variables that
		are not defined within their scope (i.e. must be
		defined globally."""

		variables = variables or []

		for block in self.getChildren():
			variables.extend(block.getUnmatchedVariableNames())

		return variables

	#
	# Control
	#

	def run (self, parent = None):
		# This block has been disabled or cancelled - skip it.
		if self.disabled is True or self.state is State.CANCELLED:
			if self.nextBlock is not None:
				return self.nextBlock.run(parent)
			else:
				return defer.succeed(None)

		# If this block is ready, then the entire stack must be ready.
		if self.state is not State.READY:
			raise AlreadyRunning

		self.state = State.RUNNING
		self.parent = parent

		self._complete = defer.Deferred()

		def _done (result = None):
			""" Run the next block, chaining the callbacks """

			if self.state is State.PAUSED:
				self._onResume = _done
				return

			if self.state not in (State.CANCELLED, State.ERROR):
				self.state = State.COMPLETE

			if self.state is State.ERROR or self._complete is None:
				# Don't continue execution if there has been an error
				# (i.e. abort has been called)
				pass
			elif self.nextBlock is not None:
				def _disconnected (failure):
					f = failure.trap(Cancelled, Disconnected)

					if f is Aborted:
						raise f

				try:
					# Do not need to reset, should have been done on connect.
					d = self.nextBlock.run()
				except AlreadyRunning:
					if self.nextBlock._complete is not None:
						d = self.nextBlock._complete
					else:
						self._complete.callback(None)
						return

				d.addErrback(
					_disconnected
				).addCallbacks(
					lambda result: self._complete.callback(result),
					lambda failure: self._complete.errback(failure)
				)
			else:
				self._complete.callback(None)

		def _error (failure):
			log.err("Block %s #%s Error: %s" % (self.type, self.id, failure))
			self.state = State.ERROR

			if self._complete is not None:
				self._complete.errback(failure)

		d = defer.maybeDeferred(self._run)
		d.addCallbacks(_done, _error)

		return self._complete

	def eval (self):
		return defer.succeed(None)

	def pause (self):
		if self.state is State.RUNNING:
			self.state = State.PAUSED

			results = [defer.maybeDeferred(self._pause)]
			for block in self.getChildren():
				try:
					results.append(block.pause())
				except NotRunning:
					pass

			return defer.DeferredList(results)

		# Pass on pause call to next block.
		elif self.nextBlock is not None:
			return self.nextBlock.pause()

		# Bottom of stack, nothing was running
		else:
			raise NotRunning

	def resume (self):
		if self.state is State.PAUSED:
			self.state = State.RUNNING

			results = [defer.maybeDeferred(self._resume)]

			# Blocks can set a function to call when they are resumed
			try:
				onResume, self._onResume = self._onResume, None
				onResume()
			except (AttributeError, TypeError):
				pass

			# Resume all children
			for block in self.getChildren():
				try:
					block.resume()
				except NotPaused:
					pass

			return defer.DeferredList(results)

		# Pass on resume call
		elif self.nextBlock is not None:
			return self.nextBlock.resume()

		# Bottom of stack, nothing needed resuming
		else:
			raise NotPaused

	def cancel (self, abort = False, propagate = False):
		if self.state in (State.RUNNING, State.PAUSED):
			if abort:
				self.state = State.ERROR
				propagate = True
			else:
				self.state = State.CANCELLED

			self._onResume = None

			# Send cancelled message to any parent block.
			try:
				if abort and self._complete.called is False:
					self._complete.errback(Aborted())
					self._complete = None
			except AttributeError:
				pass

			results = []

			# Propagate cancel call if required
			if propagate:
				try:
					results.append(self.nextBlock.cancel(abort, propagate))
				except (AttributeError, NotRunning):
					pass

			# Cancel the block execution
			results.append(defer.maybeDeferred(self._cancel, abort))

			# Cancel any inputs
			# (cancel without propagate affects only one block + inputs.)
			for block in self.inputs.values():
				# Cancel all input children
				try:
					results.append(block.cancel(abort, propagate = True))
				except (AttributeError, NotRunning):
					pass
			return defer.DeferredList(results)

		# Pass on call to next block.
		elif (abort or propagate) and self.nextBlock is not None:
			if self.state is State.READY:
				self.state = State.CANCELLED

			return self.nextBlock.cancel(abort, propagate)

		# Bottom of stack, nothing was running
		# Or, this step is not running yet. Stop it from running.
		elif self.state is State.READY:
			self.state = State.CANCELLED

			return defer.succeed(None)

		# Nothing to do
		else:
			return defer.succeed(None)

	def _cancel (self, abort = False):
		pass

	def reset (self, propagate = True):
		# Entire stack must not be RUNNING or PAUSED
		if (not propagate and self.state in (State.RUNNING, State.PAUSED)) \
		or (propagate and anyOfStackIs(self, (State.RUNNING, State.PAUSED))):
			raise AlreadyRunning

		results = []

		# Reset this block and inputs
		if self.state is not State.READY:
			self.state = State.READY
			self._onResume = None

			results.append(defer.maybeDeferred(self._reset))
			for block in self.inputs.values():
				try:
					results.append(block.reset())
				except AlreadyRunning:
					# Something has gone wrong as the this block's state
					# should reflect those of its (input) children.
					# Try to cancel the child.
					results.append(block.cancel(propagate = True).addCallback(lambda _: block.reset))
				except AttributeError:
					pass

		# Reset next block if propagating
		if propagate and self.nextBlock is not None:
			results.append(self.nextBlock.reset())

		return defer.DeferredList(results)

	#
	# Serialise
	#

	def toEvents (self):
		events = []
		events.append({ "type": "AddBlock", "data": { "id": self.id, "type": self.type, "fields": self.fields }})

		if self.mutation != "":
			events.append({ "type": "SetBlockMutation", "data": { "id": self.id, "mutation": self.mutation }})

		if self.comment != "":
			events.append({ "type": "SetBlockComment", "data": { "id": self.id, "value": self.comment }})

		if self.outputBlock is not None:
			events.append({ "type": "ConnectBlock", "data": { "id": self.id, "connection": "input-value", "parent": self.outputBlock.id, "input": self.parentInput }})

		elif self.prevBlock is not None:
			if self.parentInput is not None:
				events.append({ "type": "ConnectBlock", "data": { "id": self.id, "connection": "input-statement", "parent": self.prevBlock.id, "input": self.parentInput }})
			else:
				events.append({ "type": "ConnectBlock", "data": { "id": self.id, "connection": "previous", "parent": self.prevBlock.id }})

		for child in self.getChildren():
			events.extend(child.toEvents())

		if self.disabled:
			events.append({ "type": "SetBlockDisabled", "data": { "id": self.id, "value": True }})

		if self.inputsInline is False:
			events.append({ "type": "SetBlockInputsInline", "data": { "id": self.id, "value": False }})

		# Collapsed should come after children
		if self.collapsed:
			events.append({ "type": "SetBlockCollapsed", "data": { "id": self.id, "value": True }})

		# Only move top blocks, and only once children have been added
		if self.outputBlock is None and self.prevBlock is None:
			events.append({ "type": "SetBlockPosition", "data": { "id": self.id, "x": self.position[0], "y": self.position[1] }})

		return events


def _toHyphenated (name):
	import re
	s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
	return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

def _toUpperCamel (name):
	# We capitalize the first letter of each component except the first one
	# with the 'title' method and join them together.
	return "".join(map(str.capitalize, str(name).split('-')))

class Event (object):
	"""
	Events that can be applied to a workspace.
	"""

	jsProtocol = 'block'

	@classmethod
	def fromPayload (cls, action, payload):
		try:
			try:
				return cls.types[action](**payload)
			except AttributeError:
				cls.types = { c.jsTopic: c for c in cls.__subclasses__() }
				cls.types.update({ c.__name__: c for c in cls.__subclasses__() })
				return cls.types[action](**payload)
		except KeyError:
			raise UnknownEventError(_toUpperCamel(action))

	_fields = ()

	def __init__ (self, **fields):
		values = {}

		for f in self._fields:
			values[f] = fields[f] if f in fields else None

		self.values = values
		self.type = self.__class__.__name__

	def valuesWithEventId (self, event_id):
		values = self.values.copy()
		values['event'] = event_id
		return values

	def apply (self, workspace):
		pass

	def toJSON (self):
		import json
		return json.dumps({
			"type": self.type,
			"data": self.values
		})

class AddBlock (Event):
	_fields = ("id", "type", "fields", "x", "y")
	jsTopic = "created"

	def apply (self, workspace):
		workspace.addBlock(**self.values)

class RemoveBlock (Event):
	_fields = ("id", )
	jsTopic = "disposed"

	def apply (self, workspace):
		workspace.removeBlock(**self.values)

class ConnectBlock (Event):
	_fields = ("id", "connection", "parent", "input")
	jsTopic = "connected"

	def apply (self, workspace):
		workspace.connectBlock(**self.values)

class DisconnectBlock (Event):
	_fields = ("id", "connection", "parent", "input")
	jsTopic = "disconnected"

	def apply (self, workspace):
		workspace.disconnectBlock(**self.values)

class SetBlockPosition (Event):
	_fields = ("id", "x", "y")
	jsTopic = "set-position"

	def apply (self, workspace):
		block = workspace.getBlock(self.values['id'])
		block.position = [
			int(self.values['x'] or 0),
			int(self.values['y'] or 0)
		]

class SetBlockFieldValue (Event):
	_fields = ("id", "field", "value")
	jsTopic = "set-field-value"

	def apply (self, workspace):
		block = workspace.getBlock(self.values['id'])
		block.setFieldValue(self.values['field'], self.values['value'])

class SetBlockDisabled (Event):
	_fields = ("id", "value")
	jsTopic = "set-disabled"

	def apply (self, workspace):
		block = workspace.getBlock(self.values['id'])
		block.disabled = self.values['value']

class SetBlockCollapsed (Event):
	_fields = ("id", "value")
	jsTopic = "set-collapsed"

	def apply (self, workspace):
		block = workspace.getBlock(self.values['id'])
		block.collapsed = bool(self.values['value'])

class SetBlockComment (Event):
	_fields = ("id", "value")
	jsTopic = "set-comment"

	def apply (self, workspace):
		block = workspace.getBlock(self.values['id'])
		block.comment = str(self.values['value'])

class SetBlockInputsInline (Event):
	_fields = ("id", "value")
	jsTopic = "set-inputs-inline"

	def apply (self, workspace):
		block = workspace.getBlock(self.values['id'])
		block.inputsInline = bool(self.values['value'])

class SetBlockMutation (Event):
	_fields = ("id", "mutation")
	jsTopic = "set-mutation"

	def apply (self, workspace):
		block = workspace.getBlock(self.values['id'])
		block.mutation = self.values['mutation']

# Not Implemented:
# block-set-deletable (value)
# block-set-editable (value)
# block-set-movable (value)
# block-set-help-url (value)
# block-set-colour (value)

# Not Required
# block-add-input
# block-remove-input
# block-move-input

class UnknownEventError (Exception):
	pass

class Disconnected (Exception):
	pass

class Cancelled (Exception):
	pass

class Aborted (Cancelled):
	pass

populate_blocks()
