from twisted.internet import defer
from twisted.trial import unittest

from unittest.mock import Mock

from .. import data


class VariablesTestCase(unittest.TestCase):
    def test_create(self):
        s = data.Variable(str, "abc")
        self.assertEqual(s.value, "abc")

        i = data.Variable(int, 1)
        self.assertEqual(i.value, 1)

        f = data.Variable(float, 1.5)
        self.assertEqual(f.value, 1.5)

        b = data.Variable(bool, False)
        self.assertEqual(b.value, False)

    def test_set(self):
        s = data.Variable(str, "abc")
        s.set("def")
        self.assertEqual(s.value, "def")

        i = data.Variable(int, 1)
        i.set(2)
        self.assertEqual(i.value, 2)

        f = data.Variable(float, 1.5)
        f.set(3.7)
        self.assertEqual(f.value, 3.7)

        b = data.Variable(bool, False)
        b.set(True)
        self.assertEqual(b.value, True)

    def test_add(self):
        s = data.Variable(str, "abc")
        self.assertEqual((s + "def").value, "abcdef")
        self.assertEqual((s + 3).value, "abc3")
        self.assertEqual((s + True).value, "abcTrue")

        i = data.Variable(int, 1)
        self.assertEqual((i + "def").value, "1def")
        self.assertEqual((i + 3).value, 4)
        self.assertEqual((i + True).value, 2)

        f = data.Variable(float, 1.5)
        self.assertEqual((f + "def").value, "1.5def")
        self.assertEqual((f + 3).value, 4.5)
        self.assertEqual((f + True).value, 2.5)

        b = data.Variable(bool, False)
        self.assertEqual((b + "def").value, "Falsedef")
        self.assertEqual((b + 3).value, 3)
        self.assertEqual((b + True).value, True)
