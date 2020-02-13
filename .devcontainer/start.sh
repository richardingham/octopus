if [ ! -d "/workspaces/octopus/data/experiments" ]
then
  python /workspaces/octopus/tools/initialise.py
fi

twistd --nodaemon --pidfile=twistd.pid octopus-editor --wshost 127.0.0.1
