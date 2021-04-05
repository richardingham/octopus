# Package Imports
from octopus.blocktopus.workspace import Block, Disconnected, Cancelled
from octopus.blocktopus.blocks.variables import lexical_variable

# Octopus Imports
from octopus.constants import State
from octopus.sequence.error import NotRunning, AlreadyRunning

# Twisted Imports
from twisted.internet import reactor, defer
from twisted.python import log
import twisted.internet.error

# Python Imports
from time import time as now
import re


class controls_dependents(Block):
    @defer.inlineCallbacks
    def _run(self):
        stack = self.getInput("STACK")

        if stack is None:
            return

        self._runDependents()
        self.on("connectivity-changed", self._runDependents)

        try:
            yield stack.run()
        finally:
            self.off("connectivity-changed", self._runDependents)

            # Inputs may have changed
            yield defer.gatherResults(
                [
                    input.cancel()
                    for name, input in self.inputs.items()
                    if input is not None
                    and input.state in (State.RUNNING, State.PAUSED)
                    and name[:3] == "DEP"
                ],
                consumeErrors=True,
            )

    def _runDependents(self, data=None):
        def _cancelled(failure):
            failure.trap(Disconnected, Cancelled)

        if self.state is not State.RUNNING:
            pass

        for input in [
            input
            for name, input in self.inputs.items()
            if input is not None and input.state is State.READY and name[:3] == "DEP"
        ]:
            input.run().addErrback(_cancelled).addErrback(log.err)

    def _pause(self):
        def onResume():
            self._runDependents()

        self._onResume = onResume


class controls_bind(lexical_variable, Block):
    externalStop = True

    def _run(self):
        self._run_complete = defer.Deferred()
        self._variables = []

        self.on("connectivity-changed", self._setListeners)
        self.on("value-changed", self._setListeners)
        self._setListeners()

        return self._run_complete

    @defer.inlineCallbacks
    def _runUpdate(self, data=None):
        if self.state is State.PAUSED:
            return

        try:
            result = yield self.getInputValue("VALUE")
            self._getVariable().set(result)
        except (AttributeError, Disconnected, Cancelled):
            # May get an AttributeError if the variable has been
            # changed and become None.
            # Disconnected is handled by setListeners.
            # Cancelled is received if the child is cancelled.
            return
        except Exception as e:
            self._removeListeners()
            self._run_complete.errback(e)

    def _setListeners(self, data=None):
        for v in self._variables:
            v.off("change", self._runUpdate)

        try:
            self._variables = set(self.getInput("VALUE").getReferencedVariables())
        except (KeyError, AttributeError):
            self._variables = []

        for v in self._variables:
            v.on("change", self._runUpdate)

        self._runUpdate()

    def _removeListeners(self):
        self.off("connectivity-changed", self._setListeners)
        self.off("value-changed", self._setListeners)

        for v in self._variables:
            v.off("change", self._runUpdate)

    def _cancel(self, abort=False):
        self._removeListeners()
        self._run_complete.callback(None)


class controls_statemonitor(Block):
    _triggered = False
    cancel_on_trigger = True
    cancel_on_reset = True
    auto_reset = True

    externalStop = True

    def _run(self):
        self._run_complete = defer.Deferred()
        self._variables = []

        self.on("connectivity-changed", self.setListeners)
        self.on("value-changed", self.setListeners)
        self.setListeners()

        return self._run_complete

    @defer.inlineCallbacks
    def runUpdate(self, data=None):
        if self.state is State.PAUSED:
            self._onResume = self.runUpdate
            return
        elif self.state is not State.RUNNING:
            return

        inputValues = [
            input.eval()
            for name, input in self.inputs.items()
            if input is not None and name[:4] == "TEST"
        ]
        results = yield defer.DeferredList(inputValues, consumeErrors=True)

        ok = True
        for success, result in results:
            if success:
                ok &= bool(result)
            else:
                # Ignore if Disconnected or Cancelled.
                # TODO: log a warning if an exception.
                pass

        # Reset if already triggered and inputs now OK.
        if self._triggered and self.auto_reset and ok:
            self.resetTrigger()

        # Trigger if not triggered already, and inputs not OK.
        elif not self._triggered and not ok:
            # Cancel reset_step
            try:
                if self.cancel_on_trigger:
                    self.getInput("RESET").cancel(propagate=True)
            except (KeyError, AttributeError, NotRunning) as e:
                pass

            # Run trigger_step
            try:
                self.getInput("TRIGGER").reset()
                self.getInput("TRIGGER").run()
            except (KeyError, AttributeError, AlreadyRunning):
                return

            self._triggered = True

    def resetTrigger(self, run_reset_step=True):
        self._triggered = False

        if self.cancel_on_reset:
            try:
                self.getInput("TRIGGER").cancel(propagate=True)
            except (KeyError, AttributeError, NotRunning):
                pass

        if run_reset_step:
            try:
                self.getInput("RESET").reset()
                self.getInput("RESET").run()
            except (KeyError, AttributeError, AlreadyRunning):
                return

    def setListeners(self, data=None):
        for v in self._variables:
            v.off("change", self.runUpdate)

        self._variables = []
        inputs = [
            input
            for name, input in self.inputs.items()
            if input is not None and name[:4] == "TEST"
        ]
        for input in inputs:
            try:
                self._variables.extend(input.getReferencedVariables())
            except AttributeError:
                pass

        self._variables = set(self._variables)
        for v in self._variables:
            v.on("change", self.runUpdate)

        self.runUpdate()

    def removeListeners(self):
        self.off("connectivity-changed", self.setListeners)
        self.off("value-changed", self.setListeners)

        for v in self._variables:
            v.off("change", self.runUpdate)

    def _cancel(self, abort=False):
        self.removeListeners()
        self._run_complete.callback(None)


class controls_dependent_stack(Block):

    externalStop = True

    def _run(self):
        self._run_complete = defer.Deferred()

        try:
            self.getInput("STACK").reset()
            self.getInput("STACK").run()
        except (KeyError, AttributeError, AlreadyRunning):
            return

        return self._run_complete

    def _cancel(self, abort=False):
        self._run_complete.callback(None)
