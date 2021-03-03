import sys
from pathlib import Path

from twisted.python import log
from twisted.internet import reactor


from octopus.manufacturer.vapourtec import R2R4
from octopus.transport.basic import serial
from octopus.sequence.sequence import Sequence, LogStep, WaitStep, SetStep
from octopus.sequence.experiment import Experiment


# Serial connection, baud rate 19200 matches default
serial_connection = serial("COM4")

# Create r2 object
r2 = R2R4(endpoint=serial_connection)

# Verbose twisted-level log with all Serial communication
log.startLogging(Path("runtime.log").open("w"))


# Create experiment
exp = Experiment()
exp.set_log_output("runtime_log")
# Add machine to experiment
exp.register_machine(r2)


# Test sequence (currently only 1 reactor is plugged in bay 2)
seq = Sequence([
    LogStep("This is the first step"),
    SetStep(r2.power, "off"),
    SetStep(r2.pump1.input, "solvent"),
    SetStep(r2.pump2.input, "solvent"),
    WaitStep(2),
    SetStep(r2.output, "waste"),
    SetStep(r2.pump1.target, 200),
    SetStep(r2.pump2.target, 500),
    SetStep(r2.pump1.input, "reagent"),
    SetStep(r2.pump2.input, "reagent"),
    SetStep(r2.loop1, "load"),
    SetStep(r2.loop2, "load"),
    SetStep(r2.heater2.target, 35),
    SetStep(r2.power, "on"),
    WaitStep(10),
    SetStep(r2.pump1.target, 0),
    SetStep(r2.pump2.target, 0),
    SetStep(r2.heater2.target, -1000),
    LogStep("This is the third step"),
])

reactor.callWhenRunning(seq.run)
exp.finished += reactor.stop
reactor.run()
