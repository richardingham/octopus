# Twisted Imports
from twisted.internet import reactor, stdio
from twisted.conch.stdio import ConsoleManhole
from twisted.conch.insults.insults import ServerProtocol
from twisted.python import log

# System Imports
import os, tty, sys, termios

# Package Imports
from octopus.transport import basic
from octopus.manufacturer import vapourtec, knauer, gilson
from octopus.sequence import shortcuts

def run ():
	log.startLogging(file('child.log', 'w'))
	fd = sys.__stdin__.fileno()
	oldSettings = termios.tcgetattr(fd)
	tty.setraw(fd)
	try:
		locals = {
			"tcp": basic.tcp,
			"serial": basic.serial,
			"knauer": knauer,
			"gilson": gilson,
			"s": shortcuts
		}
		p = ServerProtocol(ConsoleManhole, namespace = locals)
		stdio.StandardIO(p)
		reactor.run()
	finally:
		termios.tcsetattr(fd, termios.TCSANOW, oldSettings)
		os.write(fd, "\r\x1bc\r")

if __name__ == '__main__':
	run()
