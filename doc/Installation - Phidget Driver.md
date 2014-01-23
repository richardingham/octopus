Installing Phidgets
===================

To use [phidgets devices](http://www.phidgets.com/) you will first
need to compile the drivers and install the Python interface.

```
$ sudo apt-get install libusb-1.0-0-dev
$ wget http://www.phidgets.com/downloads/libraries/libphidget.tar.gz
$ tar -xzvf libphidget.tar.gz
$ cd libphidget-...
$ ./configure
$ make
```

[ This will take a while ]

```
$ sudo make install
$ sudo cp udev/99-phidgets.rules /etc/udev/rules.d
```

If hotplug is installed:
```
$ sudo cp hotplug/* /etc/hotplug/usb
$ sudo chmod 755 /etc/hotplug/usb/phidgets
```

[ You might want to save libphidget-... somewhere to save 
  having to compile again on a raspberry pi ]

```
$ rm libphidget.tar.gz
$ rm -r libphidget-...
```

```
$ wget http://www.phidgets.com/downloads/libraries/PhidgetsPython.zip
$ unzip PhidgetsPython.zip
$ cd PhidgetsPython
$ sudo python setup.py install
$ rm -r PhidgetsPython
$ rm PhidgetsPython.zip
```

Check that installation was successful:

```python
>>> import Phidgets
```
