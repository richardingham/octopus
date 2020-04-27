import sqlite3
from os.path import join, dirname

def updatedb (dir):
	print ("Upgrading database " + join(dir, 'octopus.db'))

	# Create Database
	conn = sqlite3.connect(join(dir, 'octopus.db'))

	# Create tables
	conn.execute("ALTER TABLE sketches ADD COLUMN deleted integer DEFAULT 0")

# By default, create in the ../data directory.
if __name__ == "__main__":
	updatedb(join(dirname(dirname(__file__)), 'data'))
