GSIOC Connection
================

Master GSIOC connection. Usually through a 506C.

```python
master = gilson.GSIOC(connection)
slave = gilson.UVVis151(master.gsioc(15))
```

See octopus.protocol.gsioc for GSIOC/FIFO implementation.

Methods
-------

 * `gsioc(id)`

	Builds a connection object to refer to an instrument connected on GSIOC port.

	`id` is the GSIOC id of the desired connection. (You have to create a new connection for each device)



Control Module (506C)
=====================

```python
gilson.ControlModule506C(master.gsioc(id))
```

`id` is usually 63.

Attributes
----------

These must be set before the machine connects.

 *	`analogue_sample_frequency` (float, in seconds, default 0.1)

	Sets the frequency at which the hardware ADC records samples.

 *	`analogue_sample_interval` (float, in seconds, default 0.5)

	Sets the frequency at which the software polls the 506C unit.

 *	`contact_input_sample_interval`

	As above, for contact inputs.

 *	`contact_output_sample_interval`

	As above, for contact outputs.

Properties
----------

 *	`analogue1` ... `analogue4` (r, float)

	Current analogue input, in mV.

 *	`input1` ... `input4` (r, str)

	State of digital contacts. 

	Values: "open", "closed".

 *	`output1` ... `output6` (rw, str)

	State of digital contacts. 

	Values: "open", "closed".


Methods
-------

None


233 XL Sample Injector
======================

```python
gilson.SampleInjector233(master.gsioc(id))
```

Default locations (based on manual calibration of our machine and needle - CAUTION!)
 * "zero": Home position 
 * "inject:1": Injection port 1
 * "inject:2": Injection port 2
 * "wash:a:deep": Wash station A, needle in deep recess.
 * "wash:a:shallow": Wash station A, needle in shallow recess.
 * "wash:a:drain": Wash station A, needle over drain

Modify the `_default_locations` attribute to change these.
 
Properties
----------

 *	`position` (rw, str)

	Current position. Pass in a name that corresponds to one of the layouts.
	Setting the position completes when the movement has finished.

	Movement procedure: Z to zero; X, Y to desired position; Z to desired position.

	Default: "zero"

 *	`injection` (rw, str)
 
	Position of the injection valve.

	Values: "load", "inject".  
	Default: "load".

 *	`switching` (rw, str)
 
	Position of the switching valve.

	Values: "load", "inject".  
	Default: "load".

Methods
-------

 *	`add_layout(name, layout)`

	Register a layout. Its positions will be prefixed with "name:"

	Layouts must be programmed manually, see octopus/manufacturer/gilson_components/layout.py for details.

 *	`remove_layout(name)`

 * 	`clear_layouts()`


402 Syringe Pump
================

Only tested with units having only one syringe.

```python
gilson.SyringePump402(master.gsioc(id), syringe_sizes)
```

`syringe_sizes` is a list of two items, with the installed piston sizes in uL.  
Valid values: `None`, `100`, `250`, `500`, `1000`, `5000`, `10000`, `25000`, `39000` (special)

Properties
----------

 *	`valve1`, `valve2` (rw, str)

	Valve position

	Values: "needle", "reservoir"

 *	`piston1`, `piston2` - Pistons.

Piston Properties
-----------------

 *	`status` (r, str)

	Piston status

	Values: "ready", "running", "error", "uninitialized", "missing", "paused", "waiting"

 * `target` (rw, float)

	Target piston volume in uL. Piston can aspirate or dispense.
	Set completes when the piston has finished moving.

 *	`volume` (r, float)

	Current piston volume in uL. Updates while the piston is moving.

Piston Methods
--------------

 *	`set_target(target, timely_start = False)`

	Equivalent to setting the target parameter. If `timely_start` is true, the piston will wait
	until the other piston is started to move. (See gilson documentation).

 *	`set_rate(rate)`

	Set the piston flow rate in mL/min.

 *	`aspirate(volume, timely_start = False)`

	Equivalent to `set_target(target.value + volume, timely_start)

 *	`dispense(volume, timely_start = False)`

	Equivalent to `set_target(target.value - volume, timely_start)

 *	`initialize()`

	Call this if the pump becomes uninitialised.


UV/Vis 151
==========

May also work with 155.

```python
gilson.UVVis151(master.gsioc(id))
```

Attributes
----------

These must be set before the machine connects.

 *	`analogue_sample_frequency` (float, in seconds, default 0.1)

	Sets the frequency at which the hardware ADC records samples.

 *	`analogue_sample_interval` (float, in seconds, default 0.5)

	Sets the frequency at which the software polls the 151 unit.

Properties
----------

 *	`power` (rw, str)

	Lamp power

	Values: "on", "off". Untested.

 *	`wavelength` (rw, int)

	Wavelength, between 170 and 700 nm

	Doesn't seem to work.

 *	`sensitivity1`, `sensitivity2` (r, float)

	Sensitivities 1 and 2, from 0.001 to 2 AUFS.

	Untested.

 *	`detection1`, `detection2` (r, float)

	Detection at sensitivity 1 and 2, in mAU.

 *	`transmittance` (r, float)

	Transmittance in %.

Methods
-------

 *	`zero()`

	Zero the readings.
