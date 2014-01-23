Phidgets Devices
================

Phidgets devices connect by USB (some connect via an InterfaceKit which is 
itself connected by USB).

The Phidgets Drivers need to be installed - see doc/Installation - Phidgets

Use the protocols.phidgets.Phidget connection, which accepts the phidget
device ID as a parameter. N.B. You can use the Phidgets Control Panel software
(for windows, downloadable from phidgets.com) to determine the ID for each
device.

```python
connection = Phidget(1005)
```

For devices that connect via an InterfaceKit, use the `InterfaceKit.input()`,
`InterfaceKit.output()` and `InterfaceKit.sensor()` methods to get connection 
objects.

```python
ifk = phidgets.InterfaceKit(Phidget(1005))
device = phidgets.PHSensor(ifk.sensor(2))
```

InterfaceKit
============

```python
phidgets.InterfaceKit(Phidget(id))
```

Methods
-------

 *	`input(id)`

	Access a connection to digital input `id`. The connection object has a 
	method, `state()` that returns the input state.

 *	`output(id)`

	Access a connection to digital output `id`. The connection object has 
	two methods: `state` returns the output state, and `set` which changes
	it.

 *	`sensor(positions)`

	Access a connection to analogue sensor `id`. The connection object has a 
	method, `value()` that returns the current voltage detected by the sensor.


TemperatureSensor
=================

Tested with the four-thermocouple device.

```python
phidgets.TemperatureSensor(connection, inputs)
```

`inputs` is a list of the connected thermocouples:

```python
inputs = [{
	"index":      0,    # Which position the thermocouple is connected to (0-3).
	"type":       type, # What sort of thermocouple is attached.
	"min_change": 0.5,  # Minimum temperature change to record (default 0.5 deg).
}]
```

`type` can be a member of `phidgets.ThermocoupleType`:

 *  `phidgets.ThermocoupleType.E` (E-type)
 *  `phidgets.ThermocoupleType.J` (J-type)
 *  `phidgets.ThermocoupleType.K` (K-type)
 *  `phidgets.ThermocoupleType.T` (T-type)

TemperatureSensor is created with an list of attached thermocouples:

`TemperatureSensor.thermocouples[...]`
 
Each themocouple object has a `temperature` property (r, float) with units
degree C.


PHSensor
========

Only tested with USB model.

```python
phidgets.PHSensor(connection, min_change)
```

`min_change` is the minimum pH change that will be registered. Default: 0.5.

Properties
----------

 *	`temperature` (rw, float)

	Current temperature at probe (degree C).

 *	`ph` (r, float)

	The current measured pH value.
