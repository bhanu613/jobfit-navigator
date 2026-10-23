import sqlite3,json,hashlib
from datetime import datetime,timezone
STATES=('required','desirable','not_required','uncertain')
def digest(t):return hashlib.sha256(t.encode()).hexdigest()
def initialise(path):
 c=sqlite3.connect(path)
 try:
  c.execute("CREATE TABLE IF NOT EXISTS navigator_language_reviews_v4(job_id INTEGER NOT NULL REFERENCES jobs(job_id) ON DELETE CASCADE,source_hash TEXT NOT NULL,language TEXT NOT NULL,start_offset INTEGER NOT NULL,end_offset INTEGER NOT NULL,status TEXT NOT NULL CHECK(status IN ('required','desirable','not_required','uncertain')),reason TEXT NOT NULL,automatic_json TEXT NOT NULL,reviewed_at TEXT NOT NULL,PRIMARY KEY(job_id,source_hash,language,start_offset,end_offset))");c.commit()
 finally:c.close()
def automatic(r):return dict(status=r['requirement_status'],rule_id=r.get('rule_id'),cefr_candidate=r.get('cefr_candidate'))
def apply(c,jid,text,rows):
 c.row_factory=sqlite3.Row;tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")};records=[]
 for table in ('jf_batch_language','completion_language_reviews','navigator_language_reviews_v4'):
  if table in tables:
   columns={r[1] for r in c.execute('PRAGMA table_info('+table+')')}
   if {'job_id','source_hash','language','start_offset','end_offset','status'}<=columns:
    records.extend(dict(dict(r),ledger=table) for r in c.execute('SELECT * FROM '+table+' WHERE job_id=? AND source_hash=?',(jid,digest(text))))
 for r in rows:
  matches=[x for x in records if (x['language'],x['start_offset'],x['end_offset'])==(r['language'],r['start'],r['end'])]
  explicit=next((x for x in matches if x['ledger']=='navigator_language_reviews_v4'),None);statuses={x['status'] for x in matches}
  conflict=not explicit and (len(statuses)>1 or bool(statuses-set(STATES)))
  r.update(review_sources=matches,review_conflict=bool(conflict),review=explicit or (matches[0] if len(statuses)==1 else None),effective_status=explicit['status'] if explicit else 'uncertain' if conflict else next(iter(statuses)) if statuses else r['requirement_status'],review_drift=False)
  if explicit:
   try:r['review_drift']=json.loads(explicit['automatic_json'])!=automatic(r)
   except (ValueError,KeyError):r['review_drift']=True
 return rows

def save(path,jid,source,language,start,end,status,reason):
 if status not in STATES or not isinstance(reason,str) or not reason.strip():raise ValueError('Valid status and nonblank rationale required.')
 from .navigator_broader import analyse_languages
 row=next((r for r in analyse_languages(source) if (r['language'],r['start'],r['end'])==(language,start,end)),None)
 if row is None:raise ValueError('Review must match a detected language span.')
 c=sqlite3.connect(path);c.execute('PRAGMA foreign_keys=ON')
 try:
  c.execute('BEGIN IMMEDIATE');current=c.execute('SELECT description_text FROM jobs WHERE job_id=?',(jid,)).fetchone()
  if current is None or current[0]!=source:raise ValueError('Source changed; reload before reviewing.')
  c.execute('INSERT INTO navigator_language_reviews_v4 VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(job_id,source_hash,language,start_offset,end_offset) DO UPDATE SET status=excluded.status,reason=excluded.reason,automatic_json=excluded.automatic_json,reviewed_at=excluded.reviewed_at',(jid,digest(source),language,start,end,status,reason.strip(),json.dumps(automatic(row),sort_keys=True),datetime.now(timezone.utc).isoformat()));c.commit()
 except Exception:c.rollback();raise
 finally:c.close()
def remove(path,jid,source,language,start,end):
 c=sqlite3.connect(path)
 try:
  c.execute('DELETE FROM navigator_language_reviews_v4 WHERE job_id=? AND source_hash=? AND language=? AND start_offset=? AND end_offset=?',(jid,digest(source),language,start,end));c.commit()
 finally:c.close()
