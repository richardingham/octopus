Connecting to machines
======================

Devices with a serial port (9-pin or 25-pin D-sub) can be connected to the 
computer using either a port on the PC, a usb-to-serial converter or a 
serial-to-ethernet adapter.

USB/serial converters do not all work well with all computers. Those with
a Prolific chip (rather than FTDI) are rumoured to be more stable with 
Raspberry Pi. As with a direct to PC connection, the serial settings need to 
be configured at the time of use. On the computer, serial ports are named 
`COM1`, `COM2`, `COM3`... (Windows) or `/dev/ttyS0`, `/dev/ttyS1`... or 
`/dev/ttyUSB0`, `/dev/ttyUSB1`... (Linux and possibly Mac).

Serial/Ethernet converters from Brainboxes, Ltd. have been tested and work 
well. The serial settings need to be configured using the brainbox's web
interface, and then communication is via a TCP interface, for which you 
need to know the IP address of the brainbox and the port number allocated
to the serial port in question.

Within the "octopus" software, connections to are created using the 
following syntax:

```python
from octopus.transport.basic import serial, tcp

serial_connection = serial("/dev/ttyUSB0", baudrate=9600)
ethernet_connection = tcp("1921.68.15.151", 9001)
```

Serial parameters such as baudrate are passed in to serial(). For other
parameters, see: http://pyserial.sourceforge.net/pyserial_api.html
The default baudrate is 19200.

Serial parameters should be specified in the documentation for the 
device that you are connecting to.

Devices that connect by USB are generally more complicated and will have
to behave their own drivers or libraries to interface with Python.

Devices that connect by I2C, Modbus, GPIB, etc: it is theoretically 
possible to interact with these but they are not currently supported.


Instantiating objects to access machines
========================================

Once you have a connection object, this is passed into a new machine
(abstraction) object; for example:

```python
from octopus.manufacturer import knauer

my_knauer_pump = knauer.K120(connection)
```

This creates an object with all of the parameters of the machine that can 
be modified or accessed. 

Important: the machine object and its parameters only become active once a
successful connection to the machine itself has been established. Octopus
is built using a library called [Twisted] (http://www.twistedmatrix.com/)
which allows a program to do several things (effectively) at the same time.
This means that you will be able to change parameters on any number of 
connected machines whilst at the same time their parameters are updated and
all data is logged.

The consequence of this is that it is not possible to use octopus machine
objects in a standard python or ipython shell. You must either:

1. Create a sequence of steps (see below) and run them within and 
   experiment.
2. Use the octopus interactive shell, accessible by:

```
$ python -m octopus
```

(Note. This is a derivative of `twisted.conch.stdio` with some useful 
modules pre-imported)


Octopus Command Line
====================

Once a machine has been created with a valid connection, we can interact with it
using either a command-line interface or as part of a scripted program.

As mentioned above, octopus includes a command-line environment with a number of
useful modules pre-imported. (Unlike the standard Python shell, this console is 
running inside a Twisted event loop and so connections to machines can be 
established immediately).

```
$ python -m octopus
```

You are presented with a console prompt as you might expect:

```
>>>
```

The pre-imported modules are:
 * serial, tcp from octopus.transport.basic
 * vapourtec, knauer, gilson from octopus.manufacturer
 * octopus.sequence.shortcuts as s
 
Example - Knauer K120
---------------------

Imagine we have a Knauer K120 connected by serial on `/dev/ttyUSB0`. We can 
connect to this pump as described earlier:

```python
>>> pump = knauer.K120(serial("/dev/ttyUSB0", baudrate = 9600))
``` 

The Knauer K120 has the following properties:

`pump.status` - Read-only string, can have values `"ok"`, 
                `"motor-blocked"` or `"manual-stop"`.
`pump.power`  - Read/Write string, can be `"on"` or `"off"`.
`pump.target` - Read/Write integer, units of uL/min. Sets the desired 
                flow rate.
`pump.rate`   - Read-only integer, units of uL/min. Equal to `pump.target`
                if `pump.power` is `"on"`, or `0` if `pump.power` is `"off"`.

We can interact with the pump using the Python object that we have created,
using the properties listed above:

```python
>>> pump.power
<Property at a1e567cb current value: off>
>>> pump.status
<Property at 34de01a2 current value: ok>
>>> pump.target = 100
>>> pump.power = "on"
>>> pump.rate
<Property at df12a1b7 current value: 100>
```

Aside - Setting Properties 
--------------------------

Note that `Machine` objects such as instances of `knauer.K120` override 
the [`__setattr__` method][setattr] which means that assignment operations are 
delegated to the property's `set` method. i.e. `pump.power = "on"` is equivalent 
to `pump.power.set("on")` (except that no value is returned). This feature uses 
Python's object model and so can only be implemented for attributes of `Machine`
objects. A property on its own (not part of a `Machine` object) must be updated 
using its `set` method, otherwise the variable will just be reassigned:

[setattr]: http://docs.python.org/2/reference/datamodel.html#customizing-attribute-access 

```python
>>> pump.power
<Property at a1e567cb current value: on>
>>> my_p = pump.power
>>> my_p
<Property at a1e567cb current value: on>
>>> my_p = "off"
>>> my_p
"off"
>>> pump.power
<Property at a1e567cb current value: on>
>>> my_p = pump.power
>>> my_p
<Property at a1e567cb current value: on>
>>> my_p.set("off")
<Deferred #0>
Deferred #0 returned result: ok
>>> my_p
<Property at a1e567cb current value: off>
>>> pump.power
<Property at a1e567cb current value: off>
```

Sequences
=========

Using the command line is useful for interacting with machines and for testing 
purposes, but to run an experiment we will probably want to define a sequence of
instructions and save them as a program to run over and over again.

The `octopus.sequence` module provides tools to generate lists of instructions 
that will be carried out in sequence. For example: 

```python
from twisted.internet import reactor
from octopus.sequence import Sequence, LogStep, WaitStep

seq = Sequence([
	LogStep("This is the first step"),
	WaitStep(5),
	LogStep("This is the third step"),
])

import sys
from twisted.python import log
log.startLogging(sys.stdout)
seq.log += log

reactor.callWhenRunning(seq.run)
seq.addCallback(reactor.stop)
reactor.run()
```

Note. `reactor` is part of [Twisted][twisted], a library which `octopus` is 
built upon in order to perform asynchronous processing. `reactor` is an 
[event loop][wp-event-loop] and must be started before sequences can be run 
or machines can be connected to, otherwise nothing will happen. The event loop 
must also be stopped once the sequence has finished, otherwise the program 
will never end. Starting and stopping `reactor` is performed for you in the 
octopus command line environment, but in a script you have to do this yourself.

[twisted]: http://www.twistedmatrix.com/
[wp-event-loop]: http://en.wikipedia.org/wiki/Event_loop

Further reading:
 - [Twisted Event Loop](http://twistedmatrix.com/documents/current/core/howto/reactor-basics.html)
 - [Deferred callbacks](http://twistedmatrix.com/documents/current/core/howto/defer-intro.html)
 
If the above example were to be run using python (i.e. `$ python example.py`), 
then `"This is the first step"` would be displayed, and then after a five second 
pause, `"This is the third step"` would be displayed. (Along with some other
messages).

`Sequence.run` calls each of its child `Step`s in turn using their own `run` 
methods. A `LogStep()` will complete almost immediately, whereas a `WaitStep(5)`
will generate a five second delay before the subsequent step is run. 

`Sequence` is itself a `Step`, and completes only after its last child has
completed.

`octopus.sequence.Parallel` is analogous to `Sequence`, except that each child
step is started simultaneously. `Parallel` completes after the slowest child has
finished. 

```python
from twisted.internet import reactor
from octopus.sequence import Parallel, LogStep, WaitStep

seq = Parallel([
	LogStep("This is the first step"),
	WaitStep(5),
	LogStep("This is the third step"),
])

import sys
from twisted.python import log
log.startLogging(sys.stdout)
seq.log += log

reactor.callWhenRunning(seq.run)
seq.addCallback(reactor.stop)
reactor.run()
```

In this case, `"This is the first step"` and `"This is the third step"` would be 
displayed immediately, and then `seq` would complete after a five-second delay.


Expressions
===========

Since `Step`s may be created a long time before they are run, the value of any
parameters passed in must be evaluated at run-time rather than when the 
sequence is defined.

So, any expression involving a machine parameter such as `pump.rate` does not
return a value; instead it returns an `octopus.data.Expression` object which
keeps an updated value based on real-time data.

```python
>>> deriv = pump.rate + 100
>>> deriv
<AddExpression at 34f21a78 current value: 100>
>>> pump.target = 200
>>> pump.power = "on"
<AddExpression at 34f21a78 current value: 300>
```

Unlike in standard Python expressions, any addition expression involving a
string value will generate a concatenated string, coercing any numbers to 
strings.

```python
>>> deriv = "Pump rate is: " + pump.rate
>>> deriv
<AddExpression at 658a2bd1 current value: "Pump rate is: 200">
```

Experiments
===========

The `octopus.experiment` module provides the `Experiment` class. This can be 
used to wrap a sequence to provide some additional functionality:

 * Any `Machine`s involved in the experiment are reset to a default state
   before the sequence is run.
 * A log of each variable (machine properties or other variables) involved in 
   the experiment is automatically stored.
 * By setting the experiment's `id` (and optionally it's `title`) remote
   monitoring of the experiment is enabled.    

Here is a simple `Experiment` using the `knauer.K120` machine referred to
earlier:

```python
from twisted.internet import reactor
from octopus.experiment import Experiment
from octopus.sequence import Sequence, LogStep, WaitStep
from octopus.transport.basic import serial
from octopus.manufacturer import knauer

pump = knauer.K120(serial("/dev/ttyUSB0", baudrate = 9600))

exp = Experiment()
exp.register_machine(pump)

seq = Sequence([
	LogStep("Starting pump"),
	SetStep(pump.target, 200),
	SetStep(pump.power, "on"),
	WaitStep("30s"),
	LogStep("Stopping pump"),
	SetStep(pump.power, "off"),
])

reactor.callWhenRunning(exp.run)
exp.finished += reactor.stop
reactor.run()
```

`SetStep(variable, value)` creates a `Step` which calls `variable.set(value)`
when it is run, and then completes as soon as this assignment is successful.
Some `set` operations may be immediate, some may take some time - for example if 
the machine's driver carries out a check to make sure that the update has been 
carried out successfully. 
 
If we run `$ python simple_experiment.py` then the pump will be switched on and
run for 30 seconds before being switched off. 

Note that as an alternative to an integer in seconds, `WaitStep` can be given a 
formatted string with hours, minutes, seconds or millisecond components. The 
allowed format is (relatively) permissive. Examples:

- "2h"
- "20m 30s"
- "3s500ms"
- "15 minutes"
- "1 minute 20 seconds"


Shortcuts
---------

To save some typing, Octopus provides some shortcuts to make your programs 
shorter. 

 * `octopus.sequence.shortcuts` contains functions that create the various
   `Step` objects.
 * `octopus.runtime` deals with creating a single experiment, registering
   any machines that you instantiate, and starting and stopping the reactor.
   It also imports all of the sequence shortcuts.
 * `octopus.run` deals with starting and stopping the reactor if you are
   not using `octopus.runtime`.

The previous examples could equally have been written as:

```python
import octopus
from octopus.sequence.shortcuts import *

seq = sequence(
	log("This is the first step"),
	wait(5),
	log("This is the third step"),
)

octopus.run(seq)
```

```python
from octopus.runtime import *
from octopus.transport.basic import serial
from octopus.manufacturer import knauer

pump = knauer.K120(serial("/dev/ttyUSB0", baudrate = 9600))

seq = sequence(
	log("Starting pump"),
	set(pump.target, 200),
	set(pump.power, "on"),
	wait("30s"),
	log("Stopping pump"),
	set(pump.power, "off"),
)

run(seq)
```

Steps that can be used in a Sequence
------------------------------------

These are the available Step `objects` and their shortcuts.

 *	`sequence.Sequence(steps)` or  
	`shortcuts.sequence(*steps)`:

	A sequence of steps that will be run one after another, in order.

 *	`sequence.Parallel(steps)` or  
	`shortcuts.parallel(*steps)`:

	A sequence of steps that will all be run simultaneously.

 *	`sequence.SetStep(variable, value)` or  
	`shortcuts.set(variable, value)`:  

	A Step that will set `variable` to `value` when run.

 *	`shortcuts.increment(variable)`:  

	Equivalent to `sequence.SetStep(variable, variable + 1)`

 *	`shortcuts.decrement(variable)`:

	Equivalent to `sequence.SetStep(variable, variable - 1)`

 *	`sequence.WaitStep(duration)` or  
	`shortcuts.wait(duration)`:

	A Step that pause execution of the sequence for the specified time.
	`duration` may be a time in seconds, or a formatted string (see above).

	A `WaitStep` has a `delay(time)` method which can be called while the 
	step is	running to make the step wait for longer before completing. 
	`time` is in seconds. Negative values of `time` have no effect.

	There is also a `restart()` method which starts the wait timer again
	from the beginning.

 *	`sequence.WaitUntilStep(expression, [interval])` or  
	`shortcuts.wait_until(expression, [interval])`:

	A Step that pause execution of the sequence until `expression` 
	evaluates to `True`. By default, `expression` is evaluated every 100 ms, 
	but this can be changed by passing a named parameter `interval`, 
	for example: 

	```python
	wait_until(pump.power == "off", interval = 5)
	``` 

	which will evaluate `expression` every 5 seconds.

 *	`sequence.WhileStep(expression, sequence, [min_calls])` or  
	`shortcuts.loop_while(expression, sequence, [min_calls])`:

	When this step is run, `sequence` is run over and over again as long as
	`expression` evaluates to `True`. Each time `sequence` completes, 
	`expression` is tested and if it is still `True`, `sequence` is run again.

	`WhileStep` completes as soon as `sequence` finishes and `expression` 
	is `False`.

	If `expression` is initially `False`, then `sequence` will never run. 
	If you would like `sequence` to run at least once (or any other number 
	of times) then pass in an optional named parameter, `min_calls`.

 *	`shortcuts.loop_until(expression, sequence, [min_calls])`: 

	Equivalent to `sequence.WhileStep(expression == False, sequence, [min_calls])` 

 *	`sequence.IfStep(expression, sequence_if_true, sequence_if_false)` or  
	`shortcuts.do_if(expression, sequence_if_true, [sequence_if_false])`:

	When this step is run, `expression` is evaluated. If it is `True` then 
	`sequence_if_true` is run, otherwise `sequence_if_false` is run. In the 
	shortcut, `sequence_if_false` is an optional parameter.

 *	`sequence.CancelStep(runnable)` or  
	`shortcuts.cancel(runnable)`:  

	When this step is run, `runnable.cancel()` is called. If `runnable` is a 
	`Step` then it will attempt to complete immediately. Use with care.

 *	`sequence.LogStep(message)` or  
	`shortcuts.log(message)`:  
 
	Writes a message to the log. Depending on how the sequence is being run, 
	this may be on-screen, to an experiment log, both, or something else.

 *	`sequence.CallStep(callable, *args, **kwargs)` or  
	`shortcuts.call(callable, *args, **kwargs)`:  

	`callable` is a function which is called with `*args, **kwargs` when 
	`CallStep` is run. If `callable` returns a `Sequence` or `Step` then that
	is run and then	`CallStep` completes. If `callable` returns a `Deferred`,
	then `CallStep` waits for the deferred to return a value before 
	completing. Otherwise, `CallStep` completes with the return value of 
	`callable`. 


Running, Pausing, Resuming, Cancelling
======================================

(For implementation see `octopus.sequence.util`)

Sequences and Steps are defined as `Runnable`, `Pausable` and `Cancellable`
objects.

"Runnable" objects have `run` and `reset` methods. "Pausable" objects have
`pause` and `resume` methods. "Cancellable" objects have `cancel` and `abort`
methods. They all have a `state` property, which determines which of these
methods may be called.

Allowed Transitions
-------------------

State.READY -> run() -> State.RUNNING
State.{READY, COMPLETE, CANCELLED, ERROR} -> reset() -> State.READY
State.RUNNING -> pause() -> State.PAUSED
State.PAUSED -> resume() -> State.RUNNING
State.{RUNNING, PAUSED} -> cancel() -> State.CANCELLED
State.{RUNNING, PAUSED} -> abort() -> State.CANCELLED

When a step finishes it becomes State.READY or State.ERROR depending
on the result.

Attmepting to call a method when the step is not in an amenable state
will raise an exception: `AlreadyRunning`, `NotRunning` or `NotPaused`.


Run and Reset
-------------

Each Runnable can only be run once. It must be reset() before it can be run 
again.


Pause and Resume
----------------

The behaviour of `pause()` depends on the step. Immediate steps such as 
`SetStep` and `LogStep` are not significantly affected. Sequences will pause 
all of their child steps, and not run any new ones until they are resumed.

While and If steps will pause their child steps and not start any loops
until they are resumed.

WaitUntil steps will not check their expressions until they are resumed.

WaitSteps will keep a record of how much time is left to wait, and then
wait for that long after being resumed.

Experiments will pause their sequence, and also call pause on all of the
registered machines. This should cause all of the machines to stop their
pumps, heaters etc. until resume is called.


Cancel and Abort
----------------

The difference between `cancel()` and `abort()` is that cancel is used to
"gracefully" stop a sequence or step - for example, to cancel a WaitStep and
move onto the next step, or stop a WhileStep after the current iteration. 

Abort is a forceful, "emergency" stop which will immediately halt the step
and any children, and then raise an error which will halt the whole sequence
and experiment if it is attached to one.
 

Dependents
==========

A sequence or step may have "pendant" objects which run whilst the step is 
running. These are assigned to a step using the `Step.dependents.add()` method, 
and then they are automatically run, paused, resumed and stopped with the step. 
They are cancelled automatically when the step finishes.

Note. The step will not complete (allowing subsequent steps to run) until all of
its dependents have been successfully cancelled.

Note. Each dependent object can currently only be attached to one Step object.

The most common examples of dependents are "Triggers" and "Ticks".

For other dependents, such as `PID` for PID control, and `StateMonitor` see
`octopus.sequence.control`.


Triggers
--------

```python
from octopus.sequence.util import Trigger

main_seq = sequence(
	wait("10m"),
)

expression = my_var > 2

trigger_seq = sequence(
	log("Trigger Fired")
)

trigger = Trigger(expression, trigger_seq)
main_seq.dependents.add(trigger)

main_seq.run() 
```

A Trigger runs `sequence` whenever `expression` evaluates to `True`. 

Note. Whilst the sequence will only run again once it has finished, for a 
short sequence this could well be immediate if `expression` still evaluates
to `True`! Consider adding a `WaitStep` if you want to enforce a minimum time 
between subsequent calls.

To restrict the number of times that `sequence` can run, pass in the named
parameter `max_calls`. Default is `None` (no limit).

To alter the frequency at which `expression` is evaluated, pass in the named
parameter `interval` (in seconds). The default is 0.1, which can be overridden 
for all triggers by setting `Trigger.interval`. NB. This has a different
effect to adding a `WaitStep` to the sequence.


Ticks
-----

A Tick is essentially a Trigger with `expression` fixed to True.

```python
from octopus.sequence.util import Tick

tick = Tick(fn, interval)
```

`fn` can be a Sequence or a python function. If the function returns a 
`Deferred` then the Tick waits for the deferred to return a value before 
it can continue.

`interval` is a mandatory parameter.

`max_calls` is an optional parameter, with the same effect as for Trigger.


