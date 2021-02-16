# Twisted Imports
from twisted.python.constants import ValueConstant, Values


class State(Values):
    READY = ValueConstant("ready")
    RUNNING = ValueConstant("running")
    PAUSED = ValueConstant("paused")
    COMPLETE = ValueConstant("complete")
    CANCELLED = ValueConstant("cancelled")
    ERROR = ValueConstant("error")


class Event(Values):
    NEW_EXPERIMENT = ValueConstant("new-expt")
    EXPERIMENT = ValueConstant("e")
    INTERFACE = ValueConstant("i")
    STEP = ValueConstant("s")
    LOG = ValueConstant("l")
    TIMEZERO = ValueConstant("z")
