from jinja2 import Environment, FileSystemLoader

import os
import json
from datetime import datetime

jinja_env = Environment(
	loader = FileSystemLoader(os.path.join(
		os.path.dirname(os.path.abspath(__file__)),
		"templates"
	))
)

get = jinja_env.get_template

def timeformat (value, format = "%d-%m-%Y %H:%M:%S"):
	d = datetime.fromtimestamp(value)
	return d.strftime(format)

jinja_env.filters["timeformat"] = timeformat
jinja_env.filters["tojson"] = json.dumps
