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

class _SPIdev(object):
    'Internal class to package write and read transfers to spi device'
    def __init__(self):
        'Constructor'
        self.fp = open('/dev/spidev0.0', 'r+b', buffering=0)
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
        return self.write(_SPIdev.create(data))

    def __del__(self):
        'Destructor'
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
            write_polarity=0xff):
        '''
        PiFace board constructor.
        board: Piface board number = 0 to 7, default = 0.
        pull_ups: Input pull up mask, default = 0xff for all pull ups on.
        read/write_polarity: Mask of bit states for pin to be considered ON.

        Note that PiFace board by default has pullups enabled and the
        inputs, e.g. the 4 pushbuttons, activate ON to ground so that
        is why the default read_polarity is 0x00. I.e. 0 bit state is "ON".
        '''

        # There can only be up to 8 MCP23S17 devices on SPI bus
        assert board in range(8), 'Board number must be 0 to 7'

        # Open spi device only once on first board allocated
        if PiFace.count == 0:
            PiFace.spi = _SPIdev()

        PiFace.count += 1
        self.read_polarity = (~read_polarity) & 0xff
        self.write_polarity = (~write_polarity) & 0xff

        # Set up the port data (see MCP23S17 data sheet)
        cmdw = 0x40 | (board << 1)
        cmdr = cmdw | 1

        # Create write and read transfers, for performance optimisation
        self.cmdwseq = [cmdw, _RA_GPIOA, 0]
        self.cmdwtx = _SPIdev.create(self.cmdwseq)
        self.cmdrtx = _SPIdev.create([cmdr, _RA_GPIOB, 0])

        # Enable hardware addressing
        PiFace.spi.create_write([cmdw, _RA_IOCON, 8])

        # Set output port
        PiFace.spi.create_write([cmdw, _RA_IODIRA, 0])

        # Set input port
        PiFace.spi.create_write([cmdw, _RA_IODIRB, 0xff])

        # Set input pullups
        PiFace.spi.create_write([cmdw, _RA_GPPUB, pull_ups & 0xff])

        # Read initial state of outputs
        self.write_data = PiFace.spi.create_write([cmdr, _RA_GPIOA, 0]) ^ \
                self.write_polarity
        self.write_last = self.write_data

        # Read initial state of inputs
        self.read()

    def read(self):
        'Read and return the byte of inputs for PiFace board'
        self.read_data = PiFace.spi.write(self.cmdrtx) ^ self.read_polarity
        return self.read_data

    def read_pin(self, pin):
        'Convenience function to decode a pin value from last read input'
        return bool(self.read_data & (1 << pin))

    def write(self, data=None):
        'Write the byte of outputs for PiFace board'
        if data is not None:
            self.write_data = data & 0xff

        # Don't write outputs unless there is a change
        if self.write_last == self.write_data:
            return

        self.write_last = self.write_data
        self.cmdwseq[2] = self.write_data ^ self.write_polarity
        PiFace.spi.rewrite(self.cmdwseq, self.cmdwtx)

    def write_pin(self, pin, data):
        'Convenience function to write a pin value in pending write output'
        if data:
            self.write_data |= (1 << pin)
        else:
            self.write_data &= ~(1 << pin)

    def __del__(self):
        'PiFace board destructor'
        PiFace.count -= 1

        # Close spi device if this is the last board we had open
        if PiFace.count == 0:
            del PiFace.spi

# Compatibility functions just for old piface package emulation.
# Not intended to be comprehensive. Really just a demonstration.
_piface = None
def init(board=0, pull_ups=0xff, read_polarity=0x00, write_polarity=0xff):
    'piface package compatible init()'
    global _piface
    if _piface:
        del _piface
    _piface = PiFace(board, pull_ups, read_polarity, write_polarity)

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

def deinit():
    'piface package compatible deinit()'
    global _piface
    if _piface:
        del _piface
        _piface = None
