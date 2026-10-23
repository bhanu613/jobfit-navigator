from .database import connect_database
from .text_processing import alias_spans
import unicodedata
def normal(x):return ' '.join(unicodedata.normalize('NFKC',x).casefold().split())
def find_skill_mentions(description_text,*,database_path=None):
 if not isinstance(description_text,str) or not description_text.strip():raise ValueError('description_text must be nonblank text.')
 c=connect_database(database_path=database_path)
 try:
  aliases=c.execute('SELECT a.alias,s.skill_id,s.skill_key,s.canonical_name FROM skill_aliases a JOIN skills s ON s.skill_id=a.skill_id ORDER BY a.alias').fetchall()
  exists=c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='completion_alias_state'").fetchone()
  retired={(normal(a),sid) for a,sid in c.execute('SELECT alias,skill_id FROM completion_alias_state WHERE active=0')} if exists else set()
 finally:c.close()
 candidates=[]
 for alias,sid,key,name in aliases:
  if (normal(alias),sid) in retired:continue
  for start,end in alias_spans(description_text,alias):
   left=description_text.rfind('\n',0,start)+1;right=description_text.find('\n',end)
   if right<0:right=len(description_text)
   candidates.append(dict(skill_id=sid,skill_key=key,canonical_name=name,matched_alias=alias,matched_text=description_text[start:end],start=start,end=end,evidence_text=description_text[left:right],evidence_start=left,evidence_end=right))
 candidates.sort(key=lambda r:(-(r['end']-r['start']),r['start'],r['matched_alias']))
 result=[]
 for r in candidates:
  if not any(r['start']<x['end'] and x['start']<r['end'] for x in result):result.append(r)
 return sorted(result,key=lambda r:(r['start'],r['end']))
