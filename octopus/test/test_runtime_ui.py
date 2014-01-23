from twisted.internet import defer
from twisted.trial import unittest

from mock import Mock

from octopus import runtime as r


class UITestCase (unittest.TestCase):

	def test_replace (self):
		var1 = r.variable(True, "r1", "R1")
		var2 = r.variable(1, "r2", "R2")

		interface = r._experiment.interface

		r.ui(properties = [var1])
		output = interface.output()

		self.assertEqual(output[0]["name"], "experiment")
		self.assertEqual(len(output[0]["properties"]), 1)
		self.assertEqual(output[0]["properties"][0]["name"], "r1")
		self.assertEqual(output[0]["properties"][0]["value"], True)

		r.ui("my_ui", properties = [var1, var2])
		output = interface.output()

		self.assertEqual(len(output[0]["properties"]), 1)
		self.assertEqual(output[1]["name"], "my_ui")
		self.assertEqual(len(output[1]["properties"]), 2)
		self.assertEqual(output[1]["properties"][0]["name"], "r1")
		self.assertEqual(output[1]["properties"][1]["name"], "r2")

		r.ui("my_ui", properties = [var1, var2, var1])
		output = interface.output()

		self.assertEqual(len(output), 2)
		self.assertEqual(len(output[1]["properties"]), 3)
		self.assertEqual(output[1]["properties"][0]["name"], "r1")
		self.assertEqual(output[1]["properties"][1]["name"], "r2")
		self.assertEqual(output[1]["properties"][2]["name"], "r1")


