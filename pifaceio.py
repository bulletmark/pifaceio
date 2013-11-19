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

    def __init__(self, board=0, pull_ups=0xff, in_polarity=0x00,
            out_polarity=0xff):
        '''
        PiFace board constructor.
        board: Piface board number = 0 to 7, default = 0.
        pull_ups: Input pull up mask, default = 0xff for all pull ups on.
        in/out_polarity: Mask of bit states for pin to be considered ON.

        Note that PiFace board by default has pullups enabled and the
        inputs, e.g. the 4 pushbuttons, activate ON to ground so that
        is why the default in_polarity is 0x00. I.e. 0 bit state is "ON".
        '''

        # There can only be up to 8 MCP23S17 devices on SPI bus
        assert board in range(8)

        # Open spi device only once on first board
        if PiFace.count == 0:
            PiFace.spi = spidev.SpiDev()
            PiFace.spi.open(0, 0)

        PiFace.count += 1
        self.in_polarity = (~in_polarity) & 0xff
        self.out_polarity = (~out_polarity) & 0xff

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

        # Set input pullups
        PiFace.spi.xfer([cmdw, _RA_GPPUB, pull_ups])

        # Read initial state of outputs
        self.out_data = PiFace.spi.xfer([cmdr, _RA_GPIOA, 0])[2]

        # Read initial state of inputs
        self.read()

    def read(self):
        'Read the byte of inputs for PiFace board'
        self.in_data = PiFace.spi.xfer(self.cmdrseq[:])[2] ^ self.in_polarity
        return self.in_data

    def read_pin(self, pin):
        'Convenience function to decode a pin value from last read input'
        return bool(self.in_data & (1 << pin))

    def write(self, data=None):
        'Write the byte of outputs for PiFace board'
        if data is not None:
            self.out_data = data

        self.cmdwseq[2] = self.out_data ^ self.out_polarity

        # Need to pass a temp list copy because py-spidev clobbers it
        PiFace.spi.xfer(self.cmdwseq[:])

    def write_pin(self, pin, data):
        'Convenience function to write a pin value in pending write output'
        if data:
            self.out_data |= (1 << pin)
        else:
            self.out_data &= ~(1 << pin)

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
def init(board=0, pull_ups=0xff, in_polarity=0x00, out_polarity=0xff):
    'piface package compatible init()'
    global _piface
    if _piface:
        del _piface
    _piface = PiFace(board, pull_ups, in_polarity, out_polarity)

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
