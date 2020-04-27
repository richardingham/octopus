
import random

from twisted.trial import unittest

from .. import logic
from .. import mathematics 
from ...workspace import Workspace, Block
from .... import data



class CompareBlockTestCase (unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.block: Block = logic.logic_compare(self.workspace, 1)

        self.inputA = mathematics.math_number(self.workspace, 2)
        self.inputA.setFieldValue('NUM', 10)

        self.inputB = mathematics.math_number(self.workspace, 2)
        self.inputB.setFieldValue('NUM', 20)

        self.block.connectInput('A', self.inputA, "value")
        self.block.connectInput('B', self.inputB, "value")
    
    def test_compare_gt(self):
        self.block.setFieldValue('OP', 'GT')
        result = self.block.eval()
        self.assertEqual(self.successResultOf(result), False)
        return result

    def test_compare_lt(self):
        self.block.setFieldValue('OP', 'LT')
        result = self.block.eval()
        self.assertEqual(self.successResultOf(result), True)
        return result

    def test_compare_eq(self):
        self.block.setFieldValue('OP', 'EQ')
        result = self.block.eval()
        self.assertEqual(self.successResultOf(result), False)
        return result

    def test_compare_neq(self):
        self.block.setFieldValue('OP', 'NEQ')
        result = self.block.eval()
        self.assertEqual(self.successResultOf(result), True)
        return result


class LexicalVariableCompareBlockTestCase (unittest.TestCase):
    def setUp(self):
        self.variable = data.Variable(int)
        self.workspace = Workspace()
        self.workspace.variables.add('global.global::test_var', self.variable)

        self.block: Block = logic.lexical_variable_compare(self.workspace, 1)
        self.block.setFieldValue('VAR', 'global.global::test_var')

    def test_variable(self):
        self.assertIs(self.block._getVariable(), self.variable)

    def test_compare_eq(self):
        self.variable.set(11)
        self.block.setFieldValue('VALUE', 10)
        self.block.setFieldValue('OP', 'EQ')

        result = self.block.eval()
        self.assertEqual(self.successResultOf(result), False)
        return result

    def test_compare_unit(self):
        self.variable.set(11)
        self.block.setFieldValue('VALUE', 10)
        self.block.setFieldValue('UNIT', 100)
        self.block.setFieldValue('OP', 'GT')

        result = self.block.eval()
        self.assertEqual(self.successResultOf(result), False)
        return result