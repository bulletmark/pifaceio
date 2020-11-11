#!/usr/bin/env python3
'''
This package provides a pure Python interface to the PiFace Digital
peripheral board for the Raspberry Pi. This package allows a Python
program to read the inputs and write the outputs on the board via the
Raspberry Pi SPI bus. Multiple PiFace boards are supported. The newer
PiFace Digital 2 board is exactly compatible with the original board and
so is also supported by this package.
'''
# (C) Mark Blakeney, blakeney.mark@gmail.com, 2013.

import struct
import ctypes
import fcntl

# MCP23S17 Register addresses we are interested in. See MCP23S17 data sheet.
_RA_IODIRA = 0  # I/O direction A
_RA_IODIRB = 1  # I/O direction B
_RA_IOCON = 10  # I/O config
_RA_GPPUA = 12  # Port A pullups
_RA_GPPUB = 13  # Port B pullups
_RA_GPIOA = 18  # Port A pins (output)
_RA_GPIOB = 19  # Port B pins (input)

class _SPIdev:
    'Class to package 3 byte write + read transfers to spi device'
    def __init__(self, devname, speed):
        'Constructor'
        self.fp = open(devname, 'r+b', buffering=0)
        self.fn = self.fp.fileno()
        self.count = 0
        # Set the max speed
        fcntl.ioctl(self.fn, 0x40046B04, struct.pack('L', speed))

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

    def close(self):
        'Close this instance'
        self.fp.close()

    @staticmethod
    def create(data):
        'Create a transfer from given 3 byte list data'
        wbuf = ctypes.create_string_buffer(struct.pack('3B', *data))
        rbuf = ctypes.create_string_buffer(3)
        sptr = struct.pack('QQLLHBBL', ctypes.addressof(wbuf),
                ctypes.addressof(rbuf), 3, 0, 0, 0, 0, 0)
        return ctypes.create_string_buffer(sptr), wbuf, rbuf

class PiFace:
    'Allocate an instance of this class for each single PiFace board'
    _spi = {}

    def __init__(self, board=0, pull_ups=0xff, read_polarity=0x00,
            write_polarity=0xff, init_board=True, bus=0, chip=0,
            speed=int(10e6)):
        '''
        PiFace board constructor.
        board: Piface board number = 0 to 7, default = 0.
        pull_ups: Input pull up mask, default = 0xff for all pull ups on.
        read/write_polarity: Mask of bit states for pin to be considered ON.
        init_board: Set False to inhibit board initialisaion. Default is True.
        bus: SPI bus = 0 or 1, default = 0.
        chip: SPI chip select = 0 or 1, default = 0
        speed: in Hz. Default is MCP23S17 max speed of 10MHz.

        Note that bus 0, chip 0 corresponds to /dev/spidev0.0, etc.

        The PiFace board by default has pullups enabled and the inputs,
        e.g. the 4 pushbuttons, activate ON to ground so that is why the
        default read_polarity is 0x00. I.e. 0 bit state is "ON".
        '''

        # There can only be up to 8 MCP23S17 devices on SPI bus
        assert board in range(8), 'Board number must be 0 to 7'

        # Open spi device only once on first board allocated
        self.busaddr = (bus, chip)
        if self.busaddr not in PiFace._spi:
            PiFace._spi[self.busaddr] = \
                    _SPIdev('/dev/spidev{}.{}'.format(*self.busaddr), speed)

        self.spi = PiFace._spi[self.busaddr]
        self.spi.count += 1
        self.read_polarity = (~read_polarity) & 0xff
        self.write_polarity = (~write_polarity) & 0xff

        # Set up the port data (see MCP23S17 data sheet)
        cmdw = 0x40 | (board << 1)
        cmdr = cmdw | 1

        # Create write and read transfers, for performance optimisation
        self.write_cmd = [cmdw, _RA_GPIOA, 0]
        self.write_tx = _SPIdev.create(self.write_cmd)
        self.read_tx = _SPIdev.create([cmdr, _RA_GPIOB, 0])
        self.out_tx = _SPIdev.create([cmdr, _RA_GPIOA, 0])

        # Initialise board, if not inhibited to do so
        if init_board:

            # Enable hardware addressing
            self.spi.create_write([cmdw, _RA_IOCON, 8])

            # Set output port
            self.spi.create_write([cmdw, _RA_IODIRA, 0])

            # Set input port
            self.spi.create_write([cmdw, _RA_IODIRB, 0xff])

            # Set input pullups
            self.spi.create_write([cmdw, _RA_GPPUB, pull_ups & 0xff])

        # Read initial state of outputs
        self.outputs = self.read_outputs()

        # Read initial state of inputs
        self.read()

    def read(self):
        'Read and return the byte of inputs on the PiFace board'
        self.inputs = self.spi.write(self.read_tx) ^ self.read_polarity
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
        self.spi.rewrite(self.write_cmd, self.write_tx)

    def write_pin(self, pin, data):
        'Convenience function to write a pin value in pending write output'
        if data:
            self.outputs |= (1 << pin)
        else:
            self.outputs &= ~(1 << pin)

    def read_outputs(self):
        'Read and return the byte of outputs on the PiFace board'
        self.outputs_last = self.spi.write(self.out_tx) ^ self.write_polarity
        return self.outputs_last

    def read_outputs_pin(self, pin):
        'Convenience function to decode a pin value from last read output'
        return bool(self.outputs_last & (1 << pin))

    def close(self):
        'Close this PiFace board'
        self.spi.count -= 1

        # Close spi device if this is the last board we had open
        if self.spi.count == 0:
            self.spi.close()
            del PiFace._spi[self.busaddr]

# Provide non-camelcase class name alias
piface = PiFace

# Compatibility functions just for old piface package emulation.
# Not intended to be comprehensive. Really just a demonstration.
_pifaces = None

def deinit():
    'piface package compatible deinit()'
    global _pifaces
    if _pifaces:
        for pf in _pifaces:
            pf.close()

        _pifaces = None

# Takes same arguments as PiFace() constructor, see PiFace.__init__() above
def init(init_board=True, *args, **kwargs):
    'piface package compatible init()'
    global _pifaces
    deinit()
    _pifaces = [PiFace(b, init_board=init_board, *args, **kwargs)
            for b in range(8)]

    # piface package explicitly inits outputs to zero so we will too
    if init_board:
        for pf in _pifaces:
            pf.write(0)

def _get_board(board):
    'Internal service function to return PiFace board instance'
    assert board in range(8), 'Board number must be 0 to 7'
    if not _pifaces:
        init()

    return _pifaces[board]

def digital_read(pin, board=0):
    'piface package compatible digital_read()'
    pf = _get_board(board)
    pf.read()
    return pf.read_pin(pin)

def digital_write(pin, data, board=0):
    'piface package compatible digital_write()'
    pf = _get_board(board)
    pf.write_pin(pin, data)
    pf.write()

def read_input(board=0):
    'piface package compatible read_input()'
    return _get_board(board).read()

def read_output(board=0):
    'piface package compatible read_output()'
    return _get_board(board).read_outputs()

def read_output_last(board=0):
    'Return last written (cached) output byte value'
    return _get_board(board).outputs_last

def write_output(data, board=0):
    'piface package compatible write_output()'
    pf = _get_board(board)
    pf.write(data)
    return pf.outputs_last

if __name__ == '__main__':
    pf = PiFace()
    print(pf.read())
