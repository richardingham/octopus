import sqlite3
from os.path import join, dirname

def updatedb (dir):
	print ("Upgrading database " + join(dir, 'octopus.db'))

	# Create Database
	conn = sqlite3.connect(join(dir, 'octopus.db'))

	# Modify table
	conn.execute("ALTER TABLE experiments ADD COLUMN finished_date integer DEFAULT 0")
	conn.execute("ALTER TABLE experiments ADD COLUMN deleted integer DEFAULT 0")
	conn.execute("UPDATE experiments SET finished_date = started_date")
	conn.commit()

# By default, create in the ../data directory.
if __name__ == "__main__":
	updatedb(join(dirname(dirname(__file__)), 'data'))
