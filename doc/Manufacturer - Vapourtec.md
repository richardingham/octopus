Vapourtec R2+/R4
================

NB. This control file is currently not included in the distribution, because 
Vapourtec have requested that we do not publish it. Documentation for the 
serial command API is available from [Vapourtec](http://www.vapourtec.co.uk), 
using which a virtual instrument can be created.


```python
vapourtec.R2R4(connection)
```

Serial Parameters: Baud rate 19200. 8N1.

If only the R2 is connected, the heaters will show up as "off".

Connecting a second R1/R2 is not supported. Second unit will be ignored.

Results with an R1 unit are unknown.

Properties
----------

 *	`status` (r, str)

	Current status. 

	Values: "off", "running", 
	"system overpressure", "pump 1 overpressure", "pump 2 overpressure",
	"system underpressure", "pump 1 underpressure", "pump 2 underpressure"

 *	`power` (rw, str)

	System Power. 

	Values: "on", "off". 

	Default: "off".

 *	`pressure` (r, int)

	System pressure in mbar.

 *	`pressure_limit` (rw, int) 

	System pressure limit in mbar. 

	Default: 15000.

 *	`output` (rw, str) 

	Position of output valve. 

	Values: "waste", "collect". 

	Default: "waste".

 *	`loop1`, `loop2` (rw, str)

	Position of loop valves. 

	Values: "load", "inject". 

	Default: "load".

 *	`pump1` ... `pump4` - Pumps

	 *	`pump1.target` (rw, int)

		Target flow rate in uL/min.

	 *	`pump1.input` (rw, str)

		Pump input valve position. 

		Values "solvent", "reagent". 

		Default "solvent".

	 *	`pump1.rate` (r, int)

		Current flow rate in uL/min.

	 *	`pump1.pressure` (r, int)

		Current pressure in mbar.

	 *	`pump1.airlock` (r, int)

		Current airlock value.  

		Unknown unit. > ~ 10000 is bad.

 *	`heater1` ... `heater4` - Heaters

	 *	`heater1.target` (rw, int)

		Target Temperature. Allowed values depend on connected heater/cooler.

		Default -1000 (off). 

	 *	`heater1.mode` (r, str)

		Current heating mode. 

		Values: "off", "cooling", "heating", "stable unheated", "stable heated".

	 *	`heater1.power` (r, int)

		Current power draw in W.

	 *	`heater1.temp` (r, int)

		Current temperature in degrees C.


Methods
-------

 * `gsioc(id)`

	Builds a connection object to refer to an instrument connected on the R2's GSIOC port.

	`id` is the GSIOC id of the desired connection. (You have to create a new connection for each device)

	```python
	r = vapourtec.R2R4(connection)
	g = gilson.UVVis151(r.gsioc(15))
	```

