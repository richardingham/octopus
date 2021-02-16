# Twisted Imports
from twisted.internet import defer


class Slave(object):
    def __init__(self, immediate_command, buffered_command, name):
        self.immediate_command = immediate_command
        self.buffered_command = buffered_command
        self.name = name

    def connect(self, protocolFactory):
        return defer.succeed(self)
