import unittest,tempfile,sqlite3,sys,json,re,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jobfit import workspace as w,jobfit_navigation_engine as n,navigator_service as svc,job_store as store,language_reviews as lr,completion_services as completion,navigator_extensions as ext
from jobfit.concept_management import add_concept
from jobfit.skill_mentions import find_skill_mentions

class Backend(unittest.TestCase):
 def setUp(self):self.handle,self.db=w.demo()
 def tearDown(self):self.handle.cleanup()
 def listing(self,text='Rust is required. pandas usage. Deutsch B2 ist erforderlich.'):
  return w.save_listing(self.db,None,dict(title='Fictional Rust',description_text=text,source_description='Fictional test',source_url=None),dict.fromkeys(('company','location','work_type','source_language'),''))
 def reportjob(self,jid):return next(x for x in n.candidate_report(self.db,1)['jobs'] if x['job']['job_id']==jid)
 def test_demo_and_idempotent_setup(self):
  before=svc.list_jobs(database_path=self.db);w.setup(self.db);self.assertEqual(before,svc.list_jobs(database_path=self.db));self.assertEqual(len(before),3);self.assertGreaterEqual(len(svc.list_skills(database_path=self.db)),50)
 def test_concept_no_profile_claim(self):
  before=store.read_candidate_skills(1,database_path=self.db);add_concept(self.db,'Rust',['rustlang']);jid=self.listing();r=n.candidate_report(self.db,1)
  self.assertEqual(before,store.read_candidate_skills(1,database_path=self.db));self.assertTrue(any(x['concept']=='Rust' and jid in x['required_jobs'] for x in r['priorities']))
 def test_uncertain_only_in_collection(self):
  jid=self.listing();self.assertTrue(any(x['concept']=='pandas' and jid in x['review_jobs'] for x in n.candidate_report(self.db,1)['priorities']))
 def test_unicode_conflict_atomic(self):
  before=len(svc.list_skills(database_path=self.db))
  with self.assertRaises(ValueError):add_concept(self.db,'Rust',['ＰＹＴＨＯＮ'])
  self.assertEqual(len(svc.list_skills(database_path=self.db)),before)
  with self.assertRaises(ValueError):add_concept(self.db,'Ｐｙｔｈｏｎ',[])
 def test_invalid_concept_inputs(self):
  for name,aliases in [('',[]),('bad\x00',[]),('Rust','rust'),('x'*201,[])]:
   with self.assertRaises(ValueError):add_concept(self.db,name,aliases)
 def test_unicode_offsets_retirement(self):
  sid=next(x['skill_id'] for x in svc.list_skills(database_path=self.db) if x['skill_key']=='python');text='Ｐｙｔｈｏｎ and SQL';before=find_skill_mentions(text,database_path=self.db)
  self.assertEqual(len(before),2);self.assertTrue(all(text[x['start']:x['end']]==x['matched_text'] for x in before))
  completion.change_alias(self.db,sid,'python',False,'test');after=find_skill_mentions(text,database_path=self.db);self.assertEqual([x['canonical_name'] for x in after],['SQL'])
 def test_longest_overlap_and_boundaries(self):
  add_concept(self.db,'Rust',[]);self.assertEqual(len(find_skill_mentions('rustic',database_path=self.db)),0)
  add_concept(self.db,'Learning',[]);self.assertEqual([x['canonical_name'] for x in find_skill_mentions('Machine learning',database_path=self.db)],['Machine learning'])
 def test_language_context_and_profile(self):
  ext.save_language(self.db,1,'German','B1','Fictional practice');jid=self.listing();l=self.reportjob(jid)['languages'][0]
  self.assertEqual(l['cefr_candidate'],'B2');self.assertIn('B2',l['context_text']);self.assertEqual(l['profile_level'],'B1')
 def test_language_conflict_resolve_remove(self):
  jid=self.listing();j=self.reportjob(jid);l=j['languages'][0];source=j['job']['description_text'];con=sqlite3.connect(self.db)
  for table,status in [('completion_language_reviews','desirable'),('jf_batch_language','required')]:
   exists=con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
   if not exists:con.execute('CREATE TABLE '+table+'(job_id INTEGER,source_hash TEXT,language TEXT,start_offset INTEGER,end_offset INTEGER,status TEXT)')
   values=dict(job_id=jid,source_hash=lr.digest(source),language=l['language'],start_offset=l['start'],end_offset=l['end'],status=status)
   for info in con.execute('PRAGMA table_info('+table+')').fetchall():
    name,typ,required,default,pk=info[1:]
    if name not in values and required and default is None:values[name]='{}' if name.endswith('_json') else 0 if 'INT' in typ.upper() else 'fixture'
   con.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',tuple(values.values()))
  con.commit();con.close();self.assertTrue(self.reportjob(jid)['languages'][0]['review_conflict'])
  lr.save(self.db,jid,source,l['language'],l['start'],l['end'],'required','Resolve source wording');self.assertFalse(self.reportjob(jid)['languages'][0]['review_conflict']);self.assertEqual(self.reportjob(jid)['languages'][0]['effective_status'],'required')
  lr.remove(self.db,jid,source,l['language'],l['start'],l['end']);self.assertTrue(self.reportjob(jid)['languages'][0]['review_conflict'])
 def test_search_preparation_identity(self):
  r=n.candidate_report(self.db,1);q=n.search(r,'Python');self.assertTrue(q['results'])
  for row in q['results']:self.assertEqual(row['actions'],next(x['actions'] for x in r['jobs'] if x['job']['job_id']==row['job_id']))
 def test_documentation_consistency(self):
  sid=next(x['skill_id'] for x in svc.list_skills(database_path=self.db) if x['skill_key']=='sql');store.save_candidate_skill(1,sid,'evidenced','Fictional SQL project',database_path=self.db);r=n.candidate_report(self.db,1)
  self.assertEqual(next(x['profile_status'] for x in r['priorities'] if x['skill_id']==sid),'evidenced')
  for j in r['jobs']:
   for c in j['concepts']:
    if c['skill_id']==sid:self.assertEqual(c['profile_status'],'evidenced')
 def test_mixed_and_not_required(self):
  jid=self.listing('Python is required. Python is desirable. Docker is not required.');r=n.candidate_report(self.db,1)
  self.assertTrue(any(x['concept']=='Python' and jid in x['review_jobs'] for x in r['priorities']));self.assertTrue(any(x['concept']=='Docker' and jid in x['not_required_jobs'] for x in r['priorities']))
 def test_revision_stale_and_invalid_url(self):
  job=svc.list_jobs(database_path=self.db)[0];v={k:job[k] for k in ('title','description_text','source_description','source_url')};v['description_text']='SQL is desirable.';meta=dict.fromkeys(('company','location','work_type','source_language'),'')
  w.save_listing(self.db,job['job_id'],v,meta,w.fingerprint(job))
  with self.assertRaises(ValueError):w.save_listing(self.db,job['job_id'],v,meta,w.fingerprint(job))
  con=sqlite3.connect(self.db);self.assertEqual(con.execute('SELECT COUNT(*) FROM jobfit_revisions').fetchone()[0],1);con.close()
  v['source_url']='javascript:alert(1)'
  with self.assertRaises(ValueError):w.save_listing(self.db,None,v,meta)
 def test_safe_copy_and_backup(self):
  dest=Path(self.handle.name)/'copy.db';w.import_database(self.db,dest);self.assertEqual(len(svc.list_jobs(database_path=dest)),3)
  with self.assertRaises(ValueError):w.import_database(self.db,dest)
  self.assertTrue(w.backup_bytes(self.db).startswith(b'SQLite format 3'))
 def test_semantic_hybrid_test_double(self):
  import numpy as np
  class Tokenizer:
   def num_special_tokens_to_add(self,pair=False):return 2
   def __call__(self,t,add_special_tokens=False,**kw):
    offsets=[m.span() for m in re.finditer(r'\S+',t)];return dict(input_ids=list(range(len(offsets)+(2 if add_special_tokens else 0))),offset_mapping=offsets)
  class Encoder:
   max_seq_length=14;tokenizer=Tokenizer()
   def encode(self,texts,**kw):return np.array([[float('python' in x.casefold()),float('sql' in x.casefold()),1.] for x in texts])
  r=n.candidate_report(self.db,1)
  for mode in ['Semantic','Hybrid']:
   q=n.search(r,'Python',mode=mode,encoder=Encoder());self.assertTrue(q['results']);self.assertTrue(all(x.get('semantic',{}).get('passage') for x in q['results']))
  from jobfit.semantic_retrieval import rank
  with self.assertRaises(ValueError):rank([], ' '.join(['word']*20),Encoder())
 def test_profile_expansion_unseen_in_jobs(self):
  sid=add_concept(self.db,'Rust',[]);store.save_candidate_skill(1,sid,'developing','Learning fixture',database_path=self.db);r=n.candidate_report(self.db,1)
  q=n.search(r,'SQL',categories=['developing']);self.assertIn('Rust',q['effective_query'])
