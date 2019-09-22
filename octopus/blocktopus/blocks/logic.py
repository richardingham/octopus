from ..workspace import Block
from twisted.internet import defer

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


class logic_compare (Block):
	outputType = bool

	_map = {
		"EQ": operator.eq,
		"NEQ": operator.ne,
		"LT": operator.lt,
		"LTE": operator.le,
		"GT": operator.gt,
		"GTE": operator.ge
	}

	def eval (self):
		def compare (results):
			lhs, rhs = results

			if lhs is None or rhs is None:
				return None

			op = self._map[self.fields['OP']]
			return op(lhs, rhs)

			# Emit a warning if bad op given

		lhs = self.getInputValue('A')
		rhs = self.getInputValue('B')

		self._complete = defer.gatherResults([lhs, rhs]).addCallback(compare)
		return self._complete


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
