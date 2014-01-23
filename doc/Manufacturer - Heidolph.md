Heidolph Hei-End Stirrer Hotplate
=================================

```python
heidolph.HeiEnd(connection)
```

Connect using proprietary serial cable.

Baud rate 9600. 7 data bits. Even Parity. One Stop Bit.


Properties
----------

 *	`heater`

	 *	`power` (rw, str)

		Values: "on", "off"

	 *	`safetydelta` (rw, int)

		Safety delta value (degree C)

	 *	`mediumtemp` (r, float)

		Current temperature as measured by external Pt-1000 thermocouple.

	 *	`mediumsafetytemp` (r, float)

		Reading from second external thermocouple (the Pt-1000 has two).

	 *	`hotplatetemp` (r, float)

		Current temperature as measured by internal thermocouple.

	 *	`hotplatesafetytemp` (r, float)

		Reading from second internal thermocouple.

 *	`stirrer`

	 *	`power` (rw, str)

		Values: "on", "off"
 
	 *	`target` (rw, int)

		Target stirrer speed in rpm.

	 *	`speed` (r, int)

		Current speed in rpm.


Methods
-------

None

