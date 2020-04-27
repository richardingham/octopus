
Octopus provides ability to create control programmes for laboratory automation
using [Python 3](http://www.python.org) and [Twisted](http://www.twistedmatrix.com),
and real-time remote monitoring over http/websockets for running protocols.

It can provide a command-line interface for interacting with machines using
virtual instrument interfaces, or for creating scripted protocols to be run.

It is primarily designed for flow chemistry equipment; it is designed to work by
defining parameters to set for each virtual instrument interface, rather than by
defining methods to be called.


Installation
============

Install the dependencies
------------------------

```
$ sudo apt-get install python-setuptools
$ sudo apt-get install python-pip
$ sudo apt-get install python-dev
```

```
$ sudo pip install twisted
$ sudo pip install pyserial
$ sudo pip install crc16
```

Set up octopus on the Python Path
---------------------------------

One way to do this is to install to a directory within your home directory,
and then add this directory to the Python Path.

For a Raspberry Pi computer, the standard user is `pi`. For other linux computers, 
substitute `/home/pi` for `/home/[your user]`.

 1.  Make a directory `/home/pi/lib/python` if it does not exist.

 2.  Copy the two directories `octopus` and `twisted` to `/home/pi/lib/python`.

 3.  Create a file: `/usr/lib/python3.x/dist-packages/my-path.pth`
     containing the contents `/home/pi/lib/python` (or whichever path you have chosen).

Source: [darmawan-salihun.blogspot.co.uk](http://darmawan-salihun.blogspot.co.uk/2012/12/adding-new-path-to-pythonpath.html)


Running the Control Software
============================

```
$ python -m octopus
```

```python
>>> reactor = vapourtec.R2R4(serial("/dev/ttyUSB0"), baudrate = 19200)
>>> reactor.power.value
off

>>> reactor.pump1.target.set(1000)
>>> reactor.power.set("on")
>>> reactor.power.value
on

>>> reactor.pump1.pressure.value
1866
```

 *  [Read the full documentation](doc/Octopus Documentation.md)
 
I recommend the use of [GNU screen](https://www.gnu.org/software/screen/) when
running long experiments on a remote computer, to avoid having a network 
disconnection terminate the experiment. For a good introduction to screen, 
visit [aperiodic.net](http://aperiodic.net/screen/start).


Available Machine Interfaces
============================

 *  [Gilson](doc/Manufacturer - Gilson.md) - 506C Control Module, 
    233XL Sample Injector, 402 Syringe Pump, 151 UV/Vis.
 *  [Heidolph](doc/Manufacturer - Heidolph.md) - Hei-End Hotplate.
 *  [Kern](doc/Manufacturer - Kern.md) - PCB Balance
 *  [Knauer](doc/Manufacturer - Knauer.md) - K-120, S-100 HPLC pump.
 *  [Mettler Toledo](doc/Manufacturer - Mettler Toledo.md) - Balance, iC IR connector.
 *  [ThalesNano](doc/Manufacturer - ThalesNano.md) - H-Cube.
 *  [Vapourtec](doc/Manufacturer - Vapourtec.md) - R2+/R4.
 *  [VICI](doc/Manufacturer - Vici.md) - Multi-Position Valve.
 *  [World Precision Instruments](doc/Manufacturer - WPI.md) - Aladdin Syringe Pump.

Using Phidgets
==============

Drivers for some [Phidgets devices](http://www.phidgets.com) are available. 
Before use, the DLL and API must be installed.

 *  [Phidgets](doc/Manufacturer - Phidgets.md).

