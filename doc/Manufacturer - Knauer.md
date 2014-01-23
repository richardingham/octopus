Knauer K120
===========

```python
knauer.K120(connection)
```

Serial Parameters: Baud rate 9600. 8N1. Requires a crossover cable.

Properties
----------

 *	`status` (r, str)

	Current status.  

	Values: "ok", "motor-blocked", "manual-stop"  
	Can't figure out how to acheive "manual-stop"

 *	`power` (rw, str)
 
	System Power.  

	Values: "on", "off".  
	Default: "off".

 *	`target` (rw, int)

	Target flow rate in uL/min.

 *	`rate` (r, int)
 
	Current flow rate in uL/min.


Methods
-------

 *	`allowKeypad(allow)`

	if `allow` is `False`, locks the keypad. `True` to unlock.


Knauer S100
===========

```python
knauer.S100(connection)
```

Serial Parameters: Baud rate 9600. 8N1. Requires a crossover cable.

Properties
----------

 *	`status` (r, str)

	Current status.  

	Values: "idle", "running", "overpressure", "underpressure", "overcurrent", "undercurrent"

 *	`power` (rw, str)
 
	System Power.  

	Values: "on", "off".  
	Default: "off".

 *	`target` (rw, int)

	Target flow rate in uL/min.

 *	`rate` (r, int)

	Current flow rate in uL/min.

 *	`pressure` (r, int)

	Current pressure in mbar .

Methods
-------

 *	`allowKeypad(allow)`

	if `allow` is `False`, locks the keypad. `True` to unlock.

