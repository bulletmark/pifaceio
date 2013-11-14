#!/usr/bin/env python
'''
This package provides a python interface to the PiFace peripheral board
for the Raspberry Pi. This package allows a python program to read the
inputs and write the outputs on the board via the Raspberry Pi SPI bus.
Multiple PiFace boards are supported.
'''
# (C) Mark Blakeney, blakeney.mark@gmail.com, 2013.

# Use 3rd party py-spidev package from github/PyPi
import spidev

# MCP23S17 Register addresses we are interested in. See MCP23S17 data sheet.
_RA_IODIRA =  0 # I/O direction A
_RA_IODIRB =  1 # I/O direction B
_RA_IOCON  = 10 # I/O config
_RA_GPPUA  = 12 # Port A pullups
_RA_GPPUB  = 13 # Port B pullups
_RA_GPIOA  = 18 # Port A pins (output)
_RA_GPIOB  = 19 # Port B pins (input)

class PiFace(object):
    'Allocate an instance of this class for each single PiFace board'
    count = 0
    spi = None

    def __init__(self, board=0):
        'PiFace board constructor. Piface board number = 0 (default) to 7'

        # There can only be up to 8 MCP23S17 devices on SPI bus
        assert board in range(8)

        # Open spi device only once on first board
        if PiFace.count == 0:
            PiFace.spi = spidev.SpiDev()
            PiFace.spi.open(0, 0)

        PiFace.count += 1

        # Set up the port data (see MCP23S17 data sheet)
        cmdw = 0x40 | (board << 1)
        cmdr = cmdw | 1
        self.cmdwseq = [cmdw, _RA_GPIOA, 0]
        self.cmdrseq = [cmdr, _RA_GPIOB, 0]

        # Enable hardware addressing
        PiFace.spi.xfer([cmdw, _RA_IOCON, 8])

        # Set output port
        PiFace.spi.xfer([cmdw, _RA_IODIRA, 0])

        # Set input port
        PiFace.spi.xfer([cmdw, _RA_IODIRB, 0xff])

        # Set input pullups on
        PiFace.spi.xfer([cmdw, _RA_GPPUB, 0xff])

        # Read initial state of outputs
        self.outdata = PiFace.spi.xfer([cmdr, _RA_GPIOA, 0])[2]

        # Read initial state of inputs
        self.read()

    def read(self):
        'Read the byte of inputs for PiFace board'
        self.indata = PiFace.spi.xfer(self.cmdrseq[:])[2] ^ 0xff
        return self.indata

    def read_pin(self, pin):
        'Convenience function to decode a pin value from last read input'
        return bool(self.indata & (1 << pin))

    def write(self, data=None):
        'Write the byte of outputs for PiFace board'
        if data is not None:
            self.outdata = data

        self.cmdwseq[2] = self.outdata
        PiFace.spi.xfer(self.cmdwseq[:])

    def write_pin(self, pin, data):
        'Convenience function to write a pin value in pending write output'
        if data:
            self.outdata |= (1 << pin)
        else:
            self.outdata &= ~(1 << pin)

    def __del__(self):
        'PiFace board destructor'
        PiFace.count -= 1

        # Close spi device if this is the last board we had open
        if PiFace.count == 0:
            PiFace.spi.close()
            del PiFace.spi
            PiFace.spi = None

# Compatibility functions just for old piface package emulation.
# Not intended to be comprehensive. Really just a demonstration.
_piface = None
def init(boardno=0):
    'piface package compatible init()'
    global _piface
    if _piface:
        del _piface
    _piface = PiFace(boardno)

    # piface package explicitly inits outputs to zero so we will too
    _piface.write(0)

def digital_read(pin):
    'piface package compatible digital_read()'
    assert _piface
    _piface.read()
    return _piface.read_pin(pin)

def digital_write(pin, data):
    'piface package compatible digital_write()'
    assert _piface
    _piface.write_pin(pin, data)
    _piface.write()

def deinit():
    'piface package compatible deinit()'
    global _piface
    if _piface:
        del _piface
        _piface = None
