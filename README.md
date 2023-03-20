### PIFACEIO
[![PyPi](https://img.shields.io/pypi/v/pifaceio)](https://pypi.org/project/pifaceio/)

This package provides a Python interface to the [PiFace Digital][pifaceboard]
peripheral I/O board for the [Raspberry Pi][rpi].
A [PiFace Digital][pifaceboard] board offers 8 digital inputs and 8
digital outputs. This package allows a Python program to read the inputs
and write the outputs on the board via the Raspberry Pi SPI bus.

The newer [PiFace Digital 2][pifaceboard2] board is exactly compatible
with the original board and so is also supported by this package.

Multiple [PiFace Digital][pifaceboard] boards are supported, on either
or both of the RPi SPI bus chip selects. This pifaceio package is
focussed on simplicity and performance for polled implementations and is
an alternative to the official [pifacedigitalio][] Python package for
the [PiFace Digital][pifaceboard] board. In my simple benchmark of
polled reads and writes ([see next
section](#performance-benchmarks-against-pifacedigitalio)), pifaceio
performs an order of magnitude faster, and with much less overhead than
[pifacedigitalio][].

Interrupts are not supported. See [pifacedigitalio][] for interrupt and
other functionality.

The pifaceio package is implemented in pure Python code using only the
Python standard library, uses no external 3rd party packages, and is
compatible with Python version 3.6 and later.

#### Performance Benchmarks Against pifacedigitalio

A small [`benchmark`](benchmark) program is included in the
repository. It produces the following sample of simple polled read and
write performance comparisons between [pifacedigitalio][] and
[pifaceio][] on a Raspberry Pi2B.

|Function                              |`pifacedigitalio`|`pifaceio` |Speedup
|--------------------------------------|-----------------|-----------|--------
|Input reads per second                |1740             |16317      |x 9.4
|Output writes per second              |884              |11590      |x 13.1
|Input reads per second (classic API)  |1773             |11128      |x 6.3
|Output reads per second (classic API) |889              |9140       |x 10.3

### INSTALLATION

The [pifaceio pypi package][pifaceio] is available from [PyPi][] so you
can install it using [pip][]. If [pip][] is not already installed run:

```sh
sudo apt-get install python3-pip
```

Then use pip to install the [pifaceio][] package:

```sh
sudo pip3 install -U pifaceio
```

To set up permissions/groups/udev etc for spidev device on RPi, run the
included script and then reboot.

```sh
sudo pifaceio-install-spidev.sh
```

### UPGRADE

```sh
sudo pip3 install -U pifaceio
```

### USAGE

Board addresses, input pins, and output pins are always numbered from 0.

In general, you start with a once-off allocation of a PiFace board
instance at startup with:

```python
pf = pifaceio.PiFace()
```

Default is first PiFace board (0). Optionally takes an argument 0 to 7
for up to 8 PiFace board addresses. Create multiple PiFace() instances
if you want to use multiple boards in parallel.

There are also other (rarely needed) options to disable the input pull
up resistors, and to invert the input and output bit polarities. See
pifaceio.py for details.

At each poll time, e.g. every part second, read all the inputs (i.e. the
single input byte) with:

```python
pf.read() # returns the input byte you can use directly if you prefer
```

Then read and write individual pins according to your logic with:

```python
in_val = pf.read_pin(pin_in)
# ..
pf.write_pin(pin_out, out_val)
# ..
```

Finally, write all the outputs at the end of processing (i.e. write the
single output byte) with:

```python
pf.write() # optionally, takes an output byte to write directly
```

Note that `read_pin()` is just a convenience method wrapping a bit
test around the previously read input byte from `read()` and
`write_pin()` is just a convenience method wrapping a bit set/clear
around the output byte pending it being written by `write()`. You don't
have to use `read_pin()` or `write_pin()` if you just want to read,
test/manipulate, and write the 8 bit input and/or output byte directly.
In that case you would just use `read()`, and `write()` only in your
application.

### EXAMPLES

Simple example to just reflect all PiFace 8 inputs to the 8 outputs
every 10 msec, on the default first PiFace board:

```python
import pifaceio, time
pf = pifaceio.PiFace()

while True:
    pf.write(pf.read())
    time.sleep(.01)
```

Same example, but do it across 4 PiFace boards:

```python
import pifaceio, time
pifaces = [pifaceio.PiFace(n) for n in range(4)]

while True:
    for pf in pifaces:
        pf.write(pf.read())
    time.sleep(.01)
```

Simple example to test if both input pin 0 and 1 are on at same time,
and then set output pin 7 if true:

```python
import pifaceio
pf = pifaceio.PiFace()
...
# Fetch inputs (i.e. single byte)
pf.read()
first_two_inputs_on = pf.read_pin(0) and pf.read_pin(1)

# Now write that state to output pin 7
pf.write_pin(7, first_two_inputs_on)

# Do final (actual) write when all output pin states are set.
pf.write()
```

Simulated "interrupt" processing example by light-weight poll every 10 msecs:

```python
import pifaceio, time
pf = pifaceio.PiFace()

def process_change():
    'On any changed inputs, read inputs and write outputs'
    pf.write_pin(7, pf.read_pin(0) and pf.read_pin(1))

    # .. etc .. do logic using pf.read_pin() and pf.write_pin()

# Loop forever polling inputs ..
last = None
while True:
    data = pf.read()

    # Do processing only on change
    if last != data:
        last = data
        process_change()
        pf.write()        # note write() only writes if output changes

    time.sleep(.01)
```

### PIFACE PACKAGE BACKWARDS COMPATIBILITY

As an alternative API, pifaceio also implements the "classic" API from
the [pifacedigitalio][] and it's predecessor [piface][] packages. The
classic API will work compatibly, but performance is slightly degraded
compared to reading and writing the single input and output bytes using
the canonical new and preferred pifaceio API described above. However,
performance is still significantly superior to the original
[pifacedigitalio][] and [piface][] packages as shown in the above
[performance
comparison](#performance-benchmarks-against-pifacedigitalio) section.

```python
#import piface.pfio as pf (change this line ..)
#import pifacedigitalio as pf (or this line .., to the following line)
import pifaceio as pf

# The following calls should be approximately compatible:
pf.init()
value = pf.digital_read(pin)
pf.digital_write(pin, value)
pf.deinit()
```

You can also use multiple boards with this compatibility interface, e.g.
as follows where board can be from 0 to 7.

```python
value = pf.digital_read(pin, board)
pf.digital_write(pin, value, board)
```

### LICENSE

Copyright (C) 2013 Mark Blakeney. This program is distributed under the
terms of the GNU General Public License.
This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or any later
version.
This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License at <http://www.gnu.org/licenses/> for more details.

[rpi]: http://www.raspberrypi.org
[pifaceboard]: http://www.piface.org.uk/products/piface_digital/
[pifaceboard2]: http://www.element14.com/community/docs/DOC-69001/l/piface-digital-2-for-raspberry-pi
[piface]: http://github.com/thomasmacpherson/piface
[pifacedigitalio]: http://github.com/piface/pifacedigitalio
[PyPi]: https://pypi.python.org/pypi
[pip]: http://www.pip-installer.org/en/latest
[pifaceio]: https://pypi.python.org/pypi/pifaceio

<!-- vim: se ai et syn=markdown: -->
