# System Imports
import os
import tty
import sys
import termios

# Twisted Imports
from twisted.internet import reactor, stdio
from twisted.conch.stdio import ConsoleManhole
from twisted.conch.insults.insults import ServerProtocol
from twisted.python import log

# Package Imports
from octopus.transport import basic

# from octopus.sequence import shortcuts


def run():
    log.startLogging(open("child.log", "w"))
    fd = sys.__stdin__.fileno()
    oldSettings = termios.tcgetattr(fd)
    tty.setraw(fd)

    try:
        locals = {
            "tcp": basic.tcp,
            "serial": basic.serial,
            # "s": shortcuts
        }

        p = ServerProtocol(ConsoleManhole, namespace=locals)
        stdio.StandardIO(p)
        reactor.run()

    finally:
        termios.tcsetattr(fd, termios.TCSANOW, oldSettings)
        os.write(fd, "\r\x1bc\r")


if __name__ == "__main__":
    run()
