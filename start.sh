if [ ! -d "/app/data/experiments" ]
then
  python /src/octopus/tools/initialise.py
fi

twistd --nodaemon --pidfile=twistd.pid octopus-editor --wshost 127.0.0.1
