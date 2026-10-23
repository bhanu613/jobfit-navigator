import sqlite3,uuid,json,unicodedata
from pathlib import Path
from datetime import datetime,timezone
from .skill_mentions import normal

def add_concept(path,name,aliases):
 if not isinstance(aliases,list):raise ValueError('Aliases must be a list.')
 for x in [name]+aliases:
  if not isinstance(x,str) or not x.strip() or len(x)>200 or any(unicodedata.category(c) in ('Cc','Cs') for c in x):raise ValueError('Names/aliases require 1–200 characters without controls.')
 terms=list(dict.fromkeys(normal(x) for x in [name]+aliases))
 if len(terms)>30:raise ValueError('At most 30 aliases, including the canonical name.')
 c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=rw',uri=True,timeout=20)
 try:
  c.execute('PRAGMA foreign_keys=ON');c.execute('BEGIN IMMEDIATE')
  used={normal(r[0]) for r in c.execute('SELECT alias FROM skill_aliases')}|{normal(r[0]) for r in c.execute('SELECT canonical_name FROM skills')}
  if any(x in used for x in terms):raise ValueError('Name or alias conflicts with an existing concept. Nothing saved.')
  sid=c.execute('INSERT INTO skills(skill_key,canonical_name) VALUES(?,?)',('user-'+uuid.uuid4().hex,name.strip())).lastrowid
  c.executemany('INSERT INTO skill_aliases(alias,skill_id) VALUES(?,?)',[(x,sid) for x in terms])
  c.execute('CREATE TABLE IF NOT EXISTS jobfit_user_concepts(skill_id INTEGER PRIMARY KEY REFERENCES skills(skill_id),created_at TEXT NOT NULL,aliases_json TEXT NOT NULL,origin TEXT NOT NULL)')
  c.execute('INSERT INTO jobfit_user_concepts VALUES(?,?,?,?)',(sid,datetime.now(timezone.utc).isoformat(),json.dumps(terms,ensure_ascii=False),'explicit_user_entry'));c.commit();return sid
 except Exception:c.rollback();raise
 finally:c.close()
