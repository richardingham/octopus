SICS Balance
============

```python
mt.SICSBalance(connection)
```

Connect using serial cable.

Properties
----------

*	`weight` (r, float)

	The current weight in grams.


Methods
-------

 *	`getStableWeight()`
 
	Returns a Deferred which calls back with a weight as soon as it is stable.

 *	`tare()`
 
	Tares the balance. Returns a Deferred that calls back after 5s.


ICIR Connection
===============

iC IR is running on a computer that is accessible via LAN.
Connector Server is running (see tools/iCIR_server in octopus distribution)

Connect via TCP on port 8124.

```python
mt.ICIR(connection, stream_names)
```

`stream_names` is a list of named peaks as configured within iC IR. It is recommended to give the peaks simple names
such as "starting_material" and "product". 

 *	A parameter is created for each stream, with units of mAU. (r, float)

	The name of this parameter is modified from the name passed in, to make it a valid attribute name:

	Characters other than [a-zA-Z0-9_] will be removed.  
	If the first character of the name is not [a-zA-Z] the name will be prefixed with "stream_"

 *	The machine object also has an attribute, `streams`, which is a list of all streams with their original names as passed in.
