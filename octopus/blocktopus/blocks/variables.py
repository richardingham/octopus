from ..workspace import Block, Disconnected, Cancelled

from twisted.internet import defer
from twisted.python import log

from octopus import data
from octopus.constants import State
from octopus.image.data import Image, DerivedImageProperty


def variableName (name):
	split = name.split('::')

	if len(split) == 2:
		return (split[0] + "::" + split[1], None)
	elif len(split) == 3:
		return (split[0] + "::" + split[1], split[2].split('.'))
	else:
		raise InvalidVariableNameError(name)

class InvalidVariableNameError (Exception):
	""" Raised by variableName """


class global_declaration (Block):
	def _varName (self, name = None):
		return "global.global::" + (name or self.getFieldValue('NAME', ''))

	def created (self):
		self._variables = []

		# Deal with name changes
		@self.on('value-changed')
		def onVarNameChanged (data):
			if not (data["block"] is self and data["field"] == 'NAME'):
				self._onConnectivityChanged()
				self._onChange()
				return

			self.workspace.variables.rename(data["oldValue"], data["newValue"])

		self.on('connectivity-changed', self._onConnectivityChanged)
		self._onConnectivityChanged()

	# Set up event listeners whenever connections change
	def _onConnectivityChanged (self, data = None):
		for v in self._variables:
			v.off('change', self._onChange)

		try:
			self._variables = set(self.getInput('VALUE').getReferencedVariables())
		except (KeyError, AttributeError):
			self._variables = []

		for v in self._variables:
			v.on('change', self._onChange)

	# Handle any changes in variables
	@defer.inlineCallbacks
	def _onChange (self, data = None):
		if self.workspace.state not in (State.RUNNING, State.PAUSED):
			return

		try:
			result = yield self.getInput('VALUE').eval()
		except (KeyError, AttributeError, Disconnected, Cancelled):
			return

		variable = self.workspace.variables[self._varName()]

		try:
			yield variable.set(result)
		except AttributeError:
			pass
		except:
			log.err()

	@defer.inlineCallbacks
	def _run (self):
		result = yield self.getInputValue('VALUE', None)

		if result is None:
			try:
				resultType = self.getInput('VALUE').outputType
			except (KeyError, AttributeError):
				raise Exception("Global declared value cannot be None")

			if resultType is None:
				raise Exception("Global declared value cannot be None")
		else:
			resultType = type(result)

		# Special handling if the variable is an image.
		if resultType is Image:
			variable = DerivedImageProperty()
		else:
			variable = data.Variable(resultType)

		variable.alias = self.getFieldValue('NAME')
		self.workspace.variables[self._varName()] = variable

		if result is not None:
			yield variable.set(result)

		self._onConnectivityChanged()

	def disposed (self):
		for v in self._variables:
			v.off('change', self._onChange)

		self.workspace.variables.remove(self._varName())

	def getGlobalDeclarationNames (self):
		name = self._varName()

		return Block.getGlobalDeclarationNames(self,
			[name] if not self.disabled else []
		)


class lexical_variable (Block):
	def _getVariable (self):
		try:
			name, attr = variableName(self.getFieldValue('VAR', ''))
			variable = self.workspace.variables[name]
		except (InvalidVariableNameError, KeyError):
			return None

		try:
			if attr is not None:
				for key in attr:
					variable = getattr(variable, key)
		except AttributeError:
			return None

		return variable

	def getReferencedVariables (self):
		variable = self._getVariable()

		return Block.getReferencedVariables(self,
			[variable] if not self.disabled and variable is not None else []
		)

	def getReferencedVariableNames (self):
		name, attr = variableName(self.getFieldValue('VAR', ''))

		return Block.getReferencedVariableNames(self,
			[name] if not self.disabled else []
		)

	getUnmatchedVariableNames = getReferencedVariableNames


class lexical_variable_set (lexical_variable):
	@defer.inlineCallbacks
	def _run (self):
		result = yield self.getInputValue("VALUE")
		variable = self._getVariable()
		yield self._setVariable(variable, result)

	@defer.inlineCallbacks
	def _setVariable (self, variable, value):
		if variable is None:
			self.emitLogMessage(
				"Cannot set unknown variable: " + str(self.getFieldValue('VAR', '')),
				"error"
			)
			return

		try:
			yield variable.set(value)
		except Exception as error:
			self.emitLogMessage(str(error), "error")


class lexical_variable_set_to (lexical_variable_set):
	@defer.inlineCallbacks
	def _run (self):
		result = self.getFieldValue('VALUE')
		unit = self.getFieldValue('UNIT', None)
		
		if isinstance(unit, (int, float)):
			result *= unit

		variable = self._getVariable()
		yield self._setVariable(variable, result)


class lexical_variable_get (lexical_variable):
	def eval (self):
		try:
			variable = self._getVariable()

		except (AttributeError):
			self.emitLogMessage(
				"Unknown variable: " + str(self.getFieldValue('VAR')),
				"error"
			)

			return defer.succeed(None)
		
		unit = self.getFieldValue('UNIT', None)
		result = variable.value
		self.outputType = variable.type

		if isinstance(unit, (int, float)):
			result /= unit

		return defer.succeed(result)


class math_change (lexical_variable_set):
	def _run (self):
		add = 1 if self.getFieldValue("MODE") == 'INCREMENT' else -1
		variable = self._getVariable()
		unit = self.getFieldValue('UNIT', None)

		if isinstance(unit, (int, float)):
			add *= unit

		return self._setVariable(variable, variable.value + add)


class connection_gsioc (lexical_variable):
	def eval (self):
		machine = self._getVariable()
		gsioc = machine.gsioc
		return defer.maybeDeferred(
			gsioc,
			int(self.getFieldValue('ID', 0)),
		)
