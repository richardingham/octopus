if [ ! -d "/app/data/experiments" ]
then
  if [ -d "/app/octopus/tools" ] 
  then 
    python /app/octopus/tools/initialise.py
  elif [ -d "/src/octopus/tools" ] 
  then 
    python /src/octopus/tools/initialise.py 
  elif [ -d "/workspace/octopus/tools" ] 
  then 
    python /workspace/octopus/tools/initialise.py 
  fi
fi

twistd --nodaemon --pidfile=twistd.pid octopus-editor --wshost 127.0.0.1
