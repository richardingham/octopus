from twisted.internet import defer
from twisted.trial import unittest

from unittest.mock import Mock

import random

from octopus.machine import machine
from octopus import data


# NB the assertFailure() calls here only work because set() returns an immediate value.
# https://twistedmatrix.com/documents/current/api/twisted.trial.unittest.TestCase.html


class ImmutableTestCase(unittest.TestCase):
    def setUp(self):
        self.p_int = machine.Property(
            "Test immutable int property",
            type=int,
            options=None,
            min=None,
            max=None,
            unit=None,
            setter=None,
        )

    def test_immutable(self):
        for i in range(100):
            value = random.randint(-100000, 100000)
            self.assertFailure(self.p_int.set(value), data.errors.Immutable)


class MutableTestCase(unittest.TestCase):
    def setUp(self):
        def _setter(varname):
            def setter(value):
                return getattr(self, varname)._push(value)

            return setter

        self.p_int = machine.Property(
            "Test int property",
            type=int,
            options=None,
            min=None,
            max=None,
            unit=None,
            setter=_setter("p_int"),
        )
        self.p_float = machine.Property(
            "Test float property",
            type=float,
            options=None,
            min=None,
            max=None,
            unit=None,
            setter=_setter("p_float"),
        )
        self.p_str = machine.Property(
            "Test str property",
            type=str,
            options=None,
            min=None,
            max=None,
            unit=None,
            setter=_setter("p_str"),
        )

    def test_int_values(self):
        for i in range(100):
            value = random.randint(-100000, 100000)

            self.p_int.set(value)
            self.assertEqual(self.p_int.value, value)

            self.p_float.set(value)
            self.assertEqual(self.p_float.value, value)

            self.p_str.set(value)
            self.assertEqual(self.p_str.value, str(value))

    def test_float_values(self):
        for i in range(100):
            value = random.randint(-100000, 100000) / 100.0

            self.p_int.set(value)
            self.assertEqual(self.p_int.value, int(value))

            self.p_float.set(value)
            self.assertEqual(self.p_float.value, value)

            self.p_str.set(value)
            self.assertEqual(self.p_str.value, str(value))

    def test_str_values(self):
        import string

        p_int_value = self.p_int.value
        p_float_value = self.p_float.value

        for i in range(100):
            value = "".join(
                random.choice(string.ascii_uppercase + string.ascii_lowercase)
                for _ in range(10)
            )

            self.assertFailure(self.p_int.set(value), data.errors.InvalidType)
            self.assertEqual(self.p_int.value, p_int_value)

            self.assertFailure(self.p_float.set(value), data.errors.InvalidType)

            self.assertEqual(self.p_float.value, p_float_value)

            self.p_str.set(value)
            self.assertEqual(self.p_str.value, value)

    def test_convert(self):
        for i in range(100):
            value = random.randint(-100000, 100000)

            self.p_int.set(str(value))
            self.assertEqual(self.p_int.value, value)


class MaxMinTestCase(unittest.TestCase):
    def setUp(self):
        def _setter(varname):
            def setter(value):
                return getattr(self, varname)._push(value)

            return setter

        self.p_max = machine.Property(
            "Test max int property",
            type=int,
            options=None,
            min=None,
            max=100,
            unit=None,
            setter=_setter("p_max"),
        )
        self.p_min = machine.Property(
            "Test min int property",
            type=int,
            options=None,
            min=0,
            max=None,
            unit=None,
            setter=_setter("p_min"),
        )
        self.p_maxmin = machine.Property(
            "Test max/min int property",
            type=int,
            options=None,
            min=-100,
            max=100,
            unit=None,
            setter=_setter("p_maxmin"),
        )

    def test_maxmin(self):
        for i in range(100):
            value = random.randint(-100000, 100000)

            if value > 100:
                self.assertFailure(self.p_max.set(value), data.errors.ValueTooLarge)
                self.assertFailure(self.p_maxmin.set(value), data.errors.ValueTooLarge)
                self.p_min.set(value)

            elif value < 0:
                self.assertFailure(self.p_min.set(value), data.errors.ValueTooSmall)

                if value < -100:
                    self.assertFailure(
                        self.p_maxmin.set(value), data.errors.ValueTooSmall
                    )
                else:
                    self.p_maxmin.set(value)

                self.p_max.set(value)

            else:
                self.p_max.set(value)
                self.p_min.set(value)
                self.p_maxmin.set(value)


class OptionsTestCase(unittest.TestCase):
    def setUp(self):
        def _setter(varname):
            def setter(value):
                return getattr(self, varname)._push(value)

            return setter

        self.p_int = machine.Property(
            "Test int property",
            type=int,
            options=(1, 2, 3, 4, 5),
            min=None,
            max=None,
            unit=None,
            setter=_setter("p_int"),
        )
        self.p_str = machine.Property(
            "Test str property",
            type=str,
            options=("apple", "banana", "cherry"),
            min=None,
            max=None,
            unit=None,
            setter=_setter("p_str"),
        )

    def test_int_options(self):
        for value in range(-100, 100):
            if value > 0 and value < 6:
                self.p_int.set(value)
            else:
                self.assertFailure(self.p_int.set(value), data.errors.InvalidValue)

    def test_str_options(self):
        for value in ("apple", "banana", "cherry"):
            self.p_str.set(value)

        for value in ("anteater", "bear", "cat"):
            self.assertFailure(self.p_str.set(value), data.errors.InvalidValue)
