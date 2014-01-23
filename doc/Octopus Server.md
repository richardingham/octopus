
Running Octopus Server
======================

(Assumes you have set up octopus to be on the python 
path as per general installation instructions).

Install Prerequisites
---------------------

```
$ sudo pip install autobahn
$ sudo pip install jinja2
```

Install Authbind
----------------

Authbind allows scripts run under a user to bind to
privileged ports.

```
$ sudo apt-get install authbind
$ sudo touch /etc/authbind/byport/80
$ sudo chown pi /etc/authbind/byport/80
$ sudo chmod u+x /etc/authbind/byport/80
```

NB substitute `pi` in the third line with whichever user
you want to run the server under.


Option 1: Just run in a console window
--------------------------------------

```
$ twistd -n octopus --port 80
```

Alternatively, to run as a daemonised process,

```
$ twistd octopus --port 80
```


Option 2: Create an init.d script
---------------------------------

/etc/init.d/octopus.sh

```bash
#! /bin/bash
### BEGIN INIT INFO
# Provides:          octopus
# Required-Start:    $local_fs $remote_fs $network $syslog
# Required-Stop:     $local_fs $remote_fs $network $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start/stop octopus server
### END INIT INFO

logger "octopus: Start script executed"
SERVER_PATH="/home/pi/twistd"

case "$1" in
  start)
    logger "octopus: Starting"
    echo "Starting octopus..."
    authbind twistd --logfile="$SERVER_PATH/octopus.log" --pidfile="$SERVER_PATH/twistd.pid" octopus --port 80
    ;;
  stop)
    logger "octopus: Stopping"
    echo "Stopping octopus..."
    kill `cat $SERVER_PATH/twistd.pid`
    ;;
  *)
    logger "octopus: Invalid usage"
    echo "Usage: /etc/init.d/octopus {start|stop}"
    exit 1
    ;;
esac

exit 0
```

Set to start when the computer starts up
----------------------------------------

```
$ sudo update-rc.d octopus.sh defaults 91
```

Command Line Parameters
=======================

 *  `--wampport` (Default 9000). Listening port for websockets.
 *  `--pbport` (Default 8789). Listening port for Perspective Broker.
 *  `--port` (Default 8001). HTTP listening port.


Running octopus server on a different machine
=============================================

By default an experiment will attempt to connect to the server
on the same computer. If the server is to be run in a different
machine, this can be defined in the control script.

```python
from octopus.experiment import marshal
marshal.HOST = "192.168.1.10"
```

Communication is using the Twisted Perspective Broker, which uses
port 8789 by default. If necessary this can be changed as well.
(NB the option must be passed in to the server as well).

```python
marshal.PORT = 8790
```
