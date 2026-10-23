import unittest,sys,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jobfit import workspace as w,jobfit_navigation_engine as n,job_store as j,language_reviews as lr,navigator_extensions as ext,navigator_broader as broad
class ReleaseRegressions(unittest.TestCase):
 def setUp(self):self.handle,self.db=w.demo()
 def tearDown(self):self.handle.cleanup()
 def language_job(self):return next(x for x in n.candidate_report(self.db,1)['jobs'] if x['languages'])
 def test_empty_new_profile(self):
  cid=j.create_candidate('Second',database_path=self.db);r=n.candidate_report(self.db,cid);self.assertEqual(len(r['jobs']),3);self.assertEqual(r['profile'],[])
 def test_language_source_change_invalidates(self):
  job=self.language_job();l=job['languages'][0];original=job['job'];source=original['description_text'];jid=original['job_id']
  lr.save(self.db,jid,source,l['language'],l['start'],l['end'],'desirable','Review fixture')
  self.assertEqual(next(x for x in n.candidate_report(self.db,1)['jobs'] if x['job']['job_id']==jid)['languages'][0]['effective_status'],'desirable')
  values={k:original[k] for k in ('title','description_text','source_description','source_url')};values['description_text']=source+' New source.'
  w.save_listing(self.db,jid,values,broad.get_metadata(self.db,jid),w.fingerprint(original))
  changed=next(x for x in n.candidate_report(self.db,1)['jobs'] if x['job']['job_id']==jid)['languages'][0];self.assertFalse(changed['review_sources'])
 def test_language_stale_save_refused(self):
  job=self.language_job();l=job['languages'][0]
  with self.assertRaises(ValueError):lr.save(self.db,job['job']['job_id'],job['job']['description_text']+' changed',l['language'],l['start'],l['end'],'required','Stale')
 def test_delete_cascades_language_reviews(self):
  job=self.language_job();l=job['languages'][0];jid=job['job']['job_id'];lr.save(self.db,jid,job['job']['description_text'],l['language'],l['start'],l['end'],'required','Fixture');ext.delete_job(self.db,jid)
  con=sqlite3.connect(self.db)
  try:self.assertEqual(con.execute('SELECT COUNT(*) FROM navigator_language_reviews_v4 WHERE job_id=?',(jid,)).fetchone()[0],0)
  finally:con.close()
