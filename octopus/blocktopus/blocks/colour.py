# Package Imports
from ..workspace import Block

# Twisted Imports
from twisted.internet import defer
from twisted.python import log


class colour_picker (Block):
    def eval (self):
        colour = self.fields['COLOUR']

        if len(colour) != 7:
            colour = '#000000'

        return defer.succeed((
            int(colour[1:3], 16),
            int(colour[3:5], 16),
            int(colour[5:7], 16),
        ))
