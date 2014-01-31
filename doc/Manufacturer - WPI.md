World Precision Instruments Aladdin-100 Syringe Pump
====================================================

```python
wpi.Aladdin(connection, syringe_diameter)
```

Connect using proprietary serial cable, or make your own according to the specification.

Baud rate set in pump configuration. 8N1.

`syringe_size` is the diameter of the currently installed syringe, in mm.

This driver works by programming a simple pumping program with no volume limit and default
zero rate. The pump speed is adjusted by altering the rate, and switching on and off the 
pump.

NB the communications protocol is relatively complex but currently works.

Properties
----------

 *	`status` (r, str)

	The current state. 

	Values: "infusing", "withdrawing", "program-stopped",
	"program-paused", "pause-phase", "trigger-wait", "alarm"

 *	`rate` (rw, int)

	Current rate in uL/min.

 *	`direction` (rw, str)

	Values: "infuse", "withdraw"

 *	`dispensed` (r, float)

	Current dispensed volume, mL.

 *	`withdrawn` (r, float)

	Current withdrawn volume, mL.


Methods
-------

None

