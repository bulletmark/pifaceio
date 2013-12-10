#!/usr/bin/env python
'''
This package provides a pure Python interface to the PiFace peripheral
board for the Raspberry Pi. This package allows a Python program to read
the inputs and write the outputs on the board via the Raspberry Pi SPI
bus. Multiple PiFace boards are supported.
'''
# (C) Mark Blakeney, blakeney.mark@gmail.com, 2013.

import struct, ctypes, fcntl

# MCP23S17 Register addresses we are interested in. See MCP23S17 data sheet.
_RA_IODIRA =  0 # I/O direction A
_RA_IODIRB =  1 # I/O direction B
_RA_IOCON  = 10 # I/O config
_RA_GPPUA  = 12 # Port A pullups
_RA_GPPUB  = 13 # Port B pullups
_RA_GPIOA  = 18 # Port A pins (output)
_RA_GPIOB  = 19 # Port B pins (input)

class SPIdev(object):
    'Class to package 3 byte write + read transfers to spi device'
    def __init__(self, devname):
        'Constructor'
        self.fp = open(devname, 'r+b', buffering=0)
        self.fn = self.fp.fileno()

    def write(self, tx):
        'Write given transfer "tx" to device'
        fcntl.ioctl(self.fn, 0x40206b00, tx[0])

        # Return last (3rd) byte result from read buffer
        return struct.unpack_from('B', tx[2].raw, 2)[0]

    def rewrite(self, data, tx):
        'Repack a transfer "tx" with given 3 byte data and write to device'
        tx[1].raw = struct.pack('3B', *data)
        return self.write(tx)

    def create_write(self, data):
        'Create a transfer from given 3 byte data and write to device'
        return self.write(SPIdev.create(data))

    def __del__(self):
        'Destructor'
        if hasattr(self, 'fp'):
            self.fp.close()

    @staticmethod
    def create(data):
        'Create a transfer from given 3 byte list data'
        wbuf = ctypes.create_string_buffer(struct.pack('3B', *data))
        rbuf = ctypes.create_string_buffer(3)
        sptr = struct.pack('QQLLHBBL', ctypes.addressof(wbuf),
                ctypes.addressof(rbuf), 3, 0, 0, 0, 0, 0)
        return ctypes.create_string_buffer(sptr), wbuf, rbuf

class PiFace(object):
    'Allocate an instance of this class for each single PiFace board'
    count = 0

    def __init__(self, board=0, pull_ups=0xff, read_polarity=0x00,
            write_polarity=0xff, init=True):
        '''
        PiFace board constructor.
        board: Piface board number = 0 to 7, default = 0.
        pull_ups: Input pull up mask, default = 0xff for all pull ups on.
        read/write_polarity: Mask of bit states for pin to be considered ON.
        init: Set False to inhibit board initialisaion. Default is True.

        Note that PiFace board by default has pullups enabled and the
        inputs, e.g. the 4 pushbuttons, activate ON to ground so that
        is why the default read_polarity is 0x00. I.e. 0 bit state is "ON".
        '''

        # There can only be up to 8 MCP23S17 devices on SPI bus
        assert board in range(8), 'Board number must be 0 to 7'

        # Open spi device only once on first board allocated
        if PiFace.count == 0:
            PiFace.spi = SPIdev('/dev/spidev0.0')

        PiFace.count += 1
        self.read_polarity = (~read_polarity) & 0xff
        self.write_polarity = (~write_polarity) & 0xff

        # Set up the port data (see MCP23S17 data sheet)
        cmdw = 0x40 | (board << 1)
        cmdr = cmdw | 1

        # Create write and read transfers, for performance optimisation
        self.write_cmd = [cmdw, _RA_GPIOA, 0]
        self.write_tx = SPIdev.create(self.write_cmd)
        self.read_tx = SPIdev.create([cmdr, _RA_GPIOB, 0])
        self.out_tx = SPIdev.create([cmdr, _RA_GPIOA, 0])

        # Initialise board, if not inhibited to do so
        if init:

            # Enable hardware addressing
            PiFace.spi.create_write([cmdw, _RA_IOCON, 8])

            # Set output port
            PiFace.spi.create_write([cmdw, _RA_IODIRA, 0])

            # Set input port
            PiFace.spi.create_write([cmdw, _RA_IODIRB, 0xff])

            # Set input pullups
            PiFace.spi.create_write([cmdw, _RA_GPPUB, pull_ups & 0xff])

        # Read initial state of outputs
        self.outputs = self.read_outputs()

        # Read initial state of inputs
        self.read()

    def read(self):
        'Read and return the byte of inputs on the PiFace board'
        self.inputs = PiFace.spi.write(self.read_tx) ^ self.read_polarity
        return self.inputs

    def read_pin(self, pin):
        'Convenience function to decode a pin value from last read input'
        return bool(self.inputs & (1 << pin))

    def write(self, data=None):
        'Write the byte of outputs on the PiFace board'
        if data is not None:
            self.outputs = data & 0xff

        # Don't write outputs unless there is a change
        if self.outputs_last == self.outputs:
            return

        self.outputs_last = self.outputs
        self.write_cmd[2] = self.outputs ^ self.write_polarity
        PiFace.spi.rewrite(self.write_cmd, self.write_tx)

    def write_pin(self, pin, data):
        'Convenience function to write a pin value in pending write output'
        if data:
            self.outputs |= (1 << pin)
        else:
            self.outputs &= ~(1 << pin)

    def read_outputs(self):
        'Read and return the byte of outputs on the PiFace board'
        self.outputs_last = PiFace.spi.write(self.out_tx) ^ self.write_polarity
        return self.outputs_last

    def read_outputs_pin(self, pin):
        'Convenience function to decode a pin value from last read output'
        return bool(self.outputs_last & (1 << pin))

    def __del__(self):
        'PiFace board destructor'
        PiFace.count -= 1

        # Close spi device if this is the last board we had open
        if PiFace.count == 0:
            del PiFace.spi

# Compatibility functions just for old piface package emulation.
# Not intended to be comprehensive. Really just a demonstration.
_piface = None
def init(board=0, pull_ups=0xff, read_polarity=0x00, write_polarity=0xff,
        init_ports=True):
    'piface package compatible init()'
    global _piface
    if _piface:
        del _piface
    _piface = PiFace(board, pull_ups, read_polarity, write_polarity, init_ports)

    # piface package explicitly inits outputs to zero so we will too
    _piface.write(0)

def digital_read(pin):
    'piface package compatible digital_read()'
    assert _piface, 'init() has not been called'
    _piface.read()
    return _piface.read_pin(pin)

def digital_write(pin, data):
    'piface package compatible digital_write()'
    assert _piface, 'init() has not been called'
    _piface.write_pin(pin, data)
    _piface.write()

def read_input():
    'piface package compatible read_input()'
    assert _piface, 'init() has not been called'
    return _piface.read()

def read_output():
    'piface package compatible read_output()'
    assert _piface, 'init() has not been called'
    return _piface.read_outputs()

def write_output(data):
    'piface package compatible write_output()'
    assert _piface, 'init() has not been called'
    _piface.write(data)
    return _piface.outputs_last

def deinit():
    'piface package compatible deinit()'
    global _piface
    if _piface:
        del _piface
        _piface = None
