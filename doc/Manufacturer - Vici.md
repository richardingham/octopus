Valco Vici Multiposition Valve
==============================

```python
vici.MultiValve(connection)
```

Connect using proprietary serial cable, or make your own according to the specification. The manual controller does not need to be connected.

Baud rate 9600 (can be changed). 8N1.

Properties
----------

*	`position` (rw, int)

	The current position. Default 0.


Methods
-------

 *	`move(position, direction)`
 
	Move to `position`. Direction can be `c|cw|clockwise`, `a|cc|counterclockwise` or `f|fastest`.

 *	`advance(positions)`
 
	Increment `position` by `positions`.

