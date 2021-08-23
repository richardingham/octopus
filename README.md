
Octopus provides ability to create control programmes for laboratory automation
using [Python 3.9](http://www.python.org) and [Twisted](http://www.twistedmatrix.com),
and real-time remote monitoring over http/websockets for running protocols.

It can provide a command-line interface for interacting with machines using
virtual instrument interfaces, or for creating scripted protocols to be run.

It is primarily designed for flow chemistry equipment; it is designed to work by
defining parameters to set for each virtual instrument interface, rather than by
defining methods to be called.

Blocktopus is a web-based user interface for definind octopus experiments based on
the Google Blockly block-based programming environment.


# Blocktopus Installation

## Download Repository

### Download by cloning the repository:

```
git clone https://github.com/richardingham/octopus.git
cd octopus
mkdir data
```

### (Optional) - add plugins:

- Either, rename `octopus-plugins.txt.example` to `octopus-plugins.txt` and add any plugins you want to use.
- Or, create a `plugins` directory and pull any plugins into that directory.


## Option 1 - Run in Docker

Build and run docker container:

```
docker build -t "octopus:latest" .
docker run -it -p 8001:8001 -p 9000:9000 -v /app/data:/app/data octopus:latest
```

Access the interface:

```
http://127.0.0.1:8001
```


## Option 2 - Run without Docker

### Install requirements and build

```
pyenv local 3.9.5
pip install -r requirements.txt
pip install -r octopus-plugins.txt
yarn install
yarn run build
```

### Start the application

```
python octopus/blocktopus/server/server.py --plugins-dir=plugins
```

Use `--help` for all options.

### Access the interface:

```
http://127.0.0.1:8001
```


# Octopus only installation

```
pyenv local 3.9.5
pip install git+https://github.com/richardingham/octopus.git
```

## Octopus - command line

```
$ python -m octopus.console
```

```python
>>> reactor = vapourtec.R2R4(serial("/dev/ttyUSB0", baudrate = 19200))
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


# Plugins

Instrument interfaces are provided via plugins.

A plugin is any python package that provides instruments. These should be installed using pip.
For instruments to be auto-discovered by Blocktopus there should be an entry point to `blocktopus_blocks` 
defined for each block in the setup.py.

See [octopus_wpi](https://github.com/richardingham/octopus_wpi) for an example.


# Available Machine Interfaces

 *  [Gilson](doc/Manufacturer%20-%20Gilson.md) - 506C Control Module, 
    233XL Sample Injector, 402 Syringe Pump, 151 UV/Vis.
 *  [Heidolph](doc/Manufacturer%20-%20Heidolph.md) - Hei-End Hotplate.
 *  [Kern](doc/Manufacturer%20-%20Kern.md) - PCB Balance
 *  [Knauer](doc/Manufacturer%20-%20Knauer.md) - K-120, S-100 HPLC pump.
 *  [Mettler Toledo](doc/Manufacturer%20-%20Mettler Toledo.md) - Balance, iC IR connector.
 *  [ThalesNano](doc/Manufacturer%20-%20ThalesNano.md) - H-Cube.
 *  [Vapourtec](doc/Manufacturer%20-%20Vapourtec.md) - R2+/R4. (*Contact author for access.*)
 *  [VICI](doc/Manufacturer%20-%20Vici.md) - Multi-Position Valve.
 *  [World Precision Instruments](https://github.com/richardingham/octopus_wpi) - Aladdin Syringe Pump.

## Using Phidgets

Drivers for some [Phidgets devices](http://www.phidgets.com) are available. 
Before use, the DLL and API must be installed.

 *  [Phidgets](doc/Manufacturer - Phidgets.md).

