import sqlite3
from os.path import join, dirname

def createdb (dir):
	print ("Creating database " + join(dir, 'octopus.db'))

	# Create Database
	conn = sqlite3.connect(join(dir, 'octopus.db'))

	# Create tables
	conn.execute('''CREATE TABLE sketches (
		guid text,
		title text,
		user_id integer,
		created_date integer,
		modified_date integer,
		deleted integer DEFAULT 0
	)''')

	conn.execute('''CREATE TABLE experiments (
		guid text,
		sketch_guid text,
		title text,
		user_id integer,
		started_date integer,
		finished_date integer DEFAULT 0,
		deleted integer DEFAULT 0
	)''')

# By default, create in the ../data directory.
if __name__ == "__main__":
	createdb(join(dirname(dirname(__file__)), 'data'))
