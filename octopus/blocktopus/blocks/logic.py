from ..workspace import Block
from twisted.internet import defer
from .variables import lexical_variable

import operator


class logic_null (Block):
	def eval (self):
		return defer.succeed(None)


class logic_boolean (Block):
	def eval (self):
		return defer.succeed(self.fields['BOOL'] == 'TRUE')


class logic_negate (Block):
	outputType = bool

	def eval (self):
		def negate (result):
			if result is None:
				return None

			return result == False

		self._complete = self.getInputValue('BOOL').addCallback(negate)
		return self._complete


_operators_map = {
	"EQ": operator.eq,
	"NEQ": operator.ne,
	"LT": operator.lt,
	"LTE": operator.le,
	"GT": operator.gt,
	"GTE": operator.ge
}

def _compare (lhs, rhs, op_id):
	if lhs is None or rhs is None:
		return None

	op = _operators_map[op_id]
	return op(lhs, rhs)

	# Emit a warning if bad op given

class logic_compare (Block):
	outputType = bool

	def eval (self):
		lhs = self.getInputValue('A')
		rhs = self.getInputValue('B')
		op_id = self.fields['OP']

		def _eval (results):
			lhs, rhs = results
			return _compare(lhs, rhs, op_id)

		self._complete = defer.gatherResults([lhs, rhs]).addCallback(_eval)
		return self._complete


class lexical_variable_compare (lexical_variable):
	outputType = bool

	def eval (self):
		variable = self._getVariable()

		if variable is None:
			self.emitLogMessage(
				"Unknown variable: " + str(self.getFieldValue('VAR')),
				"error"
			)

			return defer.succeed(None)

		value = self.getFieldValue('VALUE')
		op_id = self.getFieldValue('OP')

		unit = self.getFieldValue('UNIT', None)
		
		if isinstance(unit, (int, float)):
			value *= unit
		
		return defer.succeed(_compare(variable.value, value, op_id))


class logic_operation (Block):
	outputType = bool

	def eval (self):
		@defer.inlineCallbacks
		def _run ():
			op = self.fields['OP']
			lhs = yield self.getInputValue('A')

			if lhs is None:
				return

			if op == "AND":
				if bool(lhs):
					rhs = yield self.getInputValue('B')

					if rhs is None:
						return

					defer.returnValue(bool(rhs))
				else:
					defer.returnValue(False)
			elif op == "OR":
				if bool(lhs):
					defer.returnValue(True)
				else:
					rhs = yield self.getInputValue('B')

					if rhs is None:
						return

					defer.returnValue(bool(rhs))

			# Emit a warning
			return

		self._complete = _run()
		return self._complete


class logic_ternary (Block):
	# TODO: outputType of then and else should be the same.
	# this is then the outputType of the logic_ternary block.
	
	def eval (self):
		@defer.inlineCallbacks
		def _run ():
			test = yield self.getInputValue('IF')

			if test is None:
				return

			if bool(test):
				result = yield self.getInputValue('THEN')
				defer.returnValue(result)
			else:
				result = yield self.getInputValue('ELSE')
				defer.returnValue(result)

		self._complete = _run()
		return self._complete
