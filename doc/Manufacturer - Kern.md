Kern PCB Balance
================

```python
kern.PCB(connection)
```

Connect using serial cable with one male and one female end. NB neets to be a DTS-DTE cable, not a straight-through.

Baud rate 19200 (can be changed). 8N1.
Make sure that the "ignore small changes" setting is switched off.

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
