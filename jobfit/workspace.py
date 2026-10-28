import sqlite3,json,hashlib,tempfile,unicodedata
from pathlib import Path
from datetime import datetime,timezone
from . import navigator_service as svc,job_store as store,navigator_extensions as ext,navigator_broader as broad

def text(value,limit=100000,required=True):
 if not isinstance(value,str) or len(value)>limit or (required and not value.strip()):raise ValueError('Missing, invalid or oversized text.')
 if any(unicodedata.category(c) in ('Cc','Cs') and c not in '\n\r\t' for c in value):raise ValueError('Unsupported control character.')
 return value

def setup(path):
 svc.prepare_application(database_path=path);ext.initialise_extensions(path);broad.initialise(path)
 from . import completion_services,language_reviews
 completion_services.initialise(path);language_reviews.initialise(path);broad.load_catalogue(path)

def fingerprint(job):return hashlib.sha256(json.dumps(dict(job),sort_keys=True).encode()).hexdigest()

def save_listing(path,jid,values,metadata,expected=None):
 for key,limit in [('title',250),('description_text',100000),('source_description',1000)]:text(values[key],limit)
 store.validate_job_input(values['title'],values['description_text'],values['source_description'],values.get('source_url') or None)
 if set(metadata)!=set(broad.METADATA_FIELDS):raise ValueError('Missing metadata.')
 for value in metadata.values():text(value,1000,False)
 c=sqlite3.connect(path,timeout=20);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 try:
  c.execute('BEGIN IMMEDIATE')
  if jid is not None:
   old=c.execute('SELECT * FROM jobs WHERE job_id=?',(jid,)).fetchone()
   if old is None:raise ValueError('Listing no longer exists.')
   if fingerprint(dict(old))!=expected:raise ValueError('Listing changed since opening. Reload before saving.')
   meta=c.execute('SELECT * FROM navigator_metadata_v3 WHERE job_id=?',(jid,)).fetchone()
   c.execute('CREATE TABLE IF NOT EXISTS jobfit_revisions(revision_id INTEGER PRIMARY KEY,job_id INTEGER NOT NULL,saved_at TEXT NOT NULL,record_json TEXT NOT NULL,metadata_json TEXT NOT NULL)')
   c.execute('INSERT INTO jobfit_revisions(job_id,saved_at,record_json,metadata_json) VALUES(?,?,?,?)',(jid,datetime.now(timezone.utc).isoformat(),json.dumps(dict(old)),json.dumps(dict(meta) if meta else {})))
  params=tuple(values[k] for k in ('title','description_text','source_description'))+(values.get('source_url') or None,)
  if jid is None:jid=c.execute('INSERT INTO jobs(title,description_text,source_description,source_url) VALUES(?,?,?,?)',params).lastrowid
  else:c.execute('UPDATE jobs SET title=?,description_text=?,source_description=?,source_url=? WHERE job_id=?',params+(jid,))
  c.execute('INSERT INTO navigator_metadata_v3 VALUES(?,?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET company=excluded.company,location=excluded.location,work_type=excluded.work_type,source_language=excluded.source_language',(jid,*(metadata[k].strip() for k in broad.METADATA_FIELDS)));c.commit();return jid
 except Exception:c.rollback();raise
 finally:c.close()

def import_database(source,destination):
 source=Path(source).resolve();destination=Path(destination).resolve()
 if not source.is_file() or source==destination:raise ValueError('Choose a different existing database.')
 if destination.exists():raise ValueError('Destination exists. Nothing overwritten.')
 src=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)
 try:
  if src.execute('PRAGMA quick_check').fetchone()!=('ok',):raise ValueError('Database integrity failed.')
  for table,cols in [('jobs',{'job_id','title','description_text','source_description','source_url','date_added','application_status'}),('candidates',{'candidate_id','display_name'})]:
   if not cols<={r[1] for r in src.execute('PRAGMA table_info('+table+')')}:raise ValueError('Incompatible '+table+' schema.')
  destination.parent.mkdir(parents=True,exist_ok=True)
  with destination.open('xb'):pass
  try:
   dst=sqlite3.connect(destination)
   try:src.backup(dst)
   finally:dst.close()
  except Exception:destination.unlink(missing_ok=True);raise
 finally:src.close()
 return destination

def demo():
 handle=tempfile.TemporaryDirectory(prefix='jobfit-demo-');p=Path(handle.name)/'workspace.db';setup(p)
 cid=store.create_candidate('Demo visitor',database_path=p);sid=next(s['skill_id'] for s in svc.list_skills(database_path=p) if s['skill_key']=='python')
 store.save_candidate_skill(cid,sid,'developing','Fictional learning statement',database_path=p)
 for title,description,location in [('Fictional NLP internship','Python is required. SQL is desirable. Docker is not required.','Trier'),('Fiktive Werkstudentenstelle','Python und SQL sind erforderlich. Git ist von Vorteil. Deutsch B2 ist erforderlich.','Mainz'),('Fictional data role','SQL is required. Python is desirable. English is desirable.','Berlin')]:
  save_listing(p,None,dict(title=title,description_text=description,source_description='Original fictional demo. Not a real vacancy.',source_url=None),dict(company='Fictional organisation',location=location,work_type='Internship',source_language='Unknown'))
 return handle,p

def backup_bytes(path):
 with tempfile.TemporaryDirectory() as d:
  target=Path(d)/'backup.db';a=sqlite3.connect(path);b=sqlite3.connect(target)
  try:a.backup(b)
  finally:b.close();a.close()
  return target.read_bytes()

def signature(path):
 c=sqlite3.connect(path)
 try:return hashlib.sha256('\n'.join(c.iterdump()).encode()).hexdigest()
 finally:c.close()


def public_demo():
 from .demo_seed import open_workspace
 return open_workspace(setup)
