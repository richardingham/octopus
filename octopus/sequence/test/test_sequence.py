from twisted.internet import defer
from twisted.trial import unittest

from unittest.mock import Mock

from .. import sequence
from ...data import data


class SequenceTestCase(unittest.TestCase):
    def test_simpleSequence(self):
        s = sequence.Sequence(
            [
                sequence.LogStep("one"),
                sequence.Sequence(
                    [
                        sequence.LogStep("two"),
                        sequence.LogStep("three"),
                    ]
                ),
                sequence.WaitStep(0.5),
                sequence.LogStep("four"),
            ]
        )

        messages = []

        @s.on("log")
        def onLog(data):
            messages.append(data["message"])

        def test(result):
            self.assertEqual(messages, ["one", "two", "three", "four"])

        return s.run().addCallback(test)


class ParallelTestCase(unittest.TestCase):
    def test_parallel(self):
        s = sequence.Parallel(
            [
                sequence.LogStep("one"),
                sequence.Sequence(
                    [
                        sequence.WaitStep(0.2),
                        sequence.LogStep("two"),
                        sequence.WaitStep(0.4),
                        sequence.LogStep("four"),
                    ]
                ),
                sequence.Sequence(
                    [
                        sequence.WaitStep(0.4),
                        sequence.LogStep("three"),
                    ]
                ),
                sequence.LogStep("final"),
            ]
        )

        messages = []

        @s.on("log")
        def onLog(data):
            messages.append(data["message"])

        def test(result):
            self.assertEqual(messages, ["one", "final", "two", "three", "four"])

        return s.run().addCallback(test)


class WhileTestCase(unittest.TestCase):
    def test_while(self):
        v = data.Variable(int, 0)

        w = sequence.WhileStep(v < 5, [sequence.SetStep(v, v + 1)])

        def test(result):
            self.assertEqual(v.value, 5)

        return w.run().addCallback(test)

    def test_whileMinCalls(self):
        v = data.Variable(int, 0)

        w = sequence.WhileStep(v < 2, [sequence.SetStep(v, v + 1)], min_calls=5)

        def test(result):
            self.assertEqual(v.value, 5)

        return w.run().addCallback(test)


class WaitUntilTestCase(unittest.TestCase):
    def test_waituntil(self):
        v = data.Variable(int, 0)
        expr = v > 0

        s = sequence.Parallel(
            [
                sequence.Sequence(
                    [
                        sequence.WaitUntilStep(expr),
                        sequence.LogStep("changed"),
                    ]
                ),
                sequence.Sequence(
                    [
                        sequence.WaitStep(0.1),
                        sequence.LogStep("one"),
                        sequence.WaitStep(0.1),
                        sequence.LogStep("two"),
                        sequence.WaitStep(0.1),
                        sequence.LogStep("three"),
                        sequence.WaitStep(0.1),
                        sequence.LogStep("four"),
                    ]
                ),
                sequence.Sequence(
                    [
                        sequence.WaitStep(0.25),
                        sequence.LogStep("set"),
                        sequence.SetStep(v, 1),
                    ]
                ),
            ]
        )

        messages = []

        @s.on("log")
        def onLog(data):
            messages.append(data["message"])

        def test(result):
            self.assertEqual(
                messages, ["one", "two", "set", "changed", "three", "four"]
            )

        return s.run().addCallback(test)


class CallTestCase(unittest.TestCase):
    def test_call(self):
        fn = Mock()

        s = sequence.CallStep(fn, 1, 2, arg=3)

        def test(result):
            fn.assert_called_once_with(1, 2, arg=3)

        return s.run().addCallback(test)
