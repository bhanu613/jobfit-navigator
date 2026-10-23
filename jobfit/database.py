import sqlite3
from pathlib import Path
DEFAULT_DATABASE_PATH=Path(__file__).parent/'jobs.db'
def connect_database(*,database_path=None):
 c=sqlite3.connect(database_path if database_path is not None else DEFAULT_DATABASE_PATH,timeout=20)
 c.execute('PRAGMA foreign_keys=ON')
 if c.execute('PRAGMA foreign_keys').fetchone()!=(1,):c.close();raise RuntimeError('Foreign key enforcement unavailable.')
 return c
