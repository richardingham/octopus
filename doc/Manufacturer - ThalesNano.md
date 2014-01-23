ThalesNano H-Cube
=================

```python
thalesnano.HCube(connection)
```

Baud rate 9600 (can be changed). 8N1.

Properties
----------

 *	`state` (r, str)

	Current state . 

 *	`message` (r, str)

	Current status message.

 *	`system_pressure_target` (rw, int)

	Current setting for system pressure. Hydrogen must be off to change the pressure.
	Takes values from 10-100 in steps of 10, in bar.

 *	`system_pressure` (r, int)

	Current pressure reading (bar).

 *	`inlet_pressure` (r, int)

	Pressure at the inlet, in bar.

 *	`hydrogen_pressure` (r, int)

	Should be the H2 pressure. Doesn't work.

 *	`column_temperature_target` (rw, int)

	Current setting for column temperature.
	Takes values from 10-100 in steps of 10, in degrees C.

	Changes incrementally if the hydrogen is on.
	Completes only when the target has changed all the way.

 *	`column_temperature` (r, int)

	Current temperature reading (degree C).

 * 	`hydrogen_mode` (rw, str)

	Takes values "full", "controlled", "off". If mode is set to "full", "system_pressure_target" will be set to 0.
	Can't change when the hydrogen is on.

 *	`gas_liquid_ratio` (r, int)

	Allegedly some kind of bubble counter.

Methods
-------

 *	`start_hydrogenation()`

	Turn on hydrogen. Completes once pressure has built up.

 *	`stop_keep_hydrogen()`

	Release pressure, keep hydrogen.
	Completes after valves have closed.

 *	`stop_release_hydrogen()`

	Release pressure, don't keep hydrogen.
	Completes after pressure has released.

 *	`shutdown()`

	Shut down H-Cube.
