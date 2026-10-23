import unittest,sys,sqlite3,json,hashlib,importlib.util,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jobfit import workspace as w,jobfit_navigation_engine as n,navigator_extensions as ext,navigator_service as svc
from jobfit.concept_management import add_concept
from jobfit.release_features import search_listings
class Refinement(unittest.TestCase):
 def setUp(self):self.h,self.db=w.demo()
 def tearDown(self):self.h.cleanup()
 def add(self,text,location='Bonn',work_type='Contract'):
  return w.save_listing(self.db,None,dict(title='Regression job',description_text=text,source_description='Synthetic test',source_url=None),dict(company='Example',location=location,work_type=work_type,source_language='English'))
 def report(self):return n.candidate_report(self.db,1)
 def job(self,jid):return next(x for x in self.report()['jobs'] if x['job']['job_id']==jid)
 def test_job6_and_counts(self):
  jid=self.add('needed seaborn.\nrequired pytorch.\nplus pandas.\ndesirable excel.\nnot needed git.\nnot required kubernetes');j=self.job(jid)
  self.assertEqual({c['canonical_name']:c['effective_status'] for c in j['concepts']},{'Seaborn':'required','PyTorch':'required','pandas':'desirable','Excel':'desirable','Git':'not_required','Kubernetes':'not_required'})
  p=next(x for x in self.report()['priorities'] if x['concept']=='pandas');self.assertIn(jid,p['desirable_jobs']);self.assertNotIn(jid,p['review_jobs'])
 def test_custom_concept_existing_listing(self):
  jid=self.add('plus CustomZephyr.');add_concept(self.db,'CustomZephyr',[]);p=next(x for x in self.report()['priorities'] if x['concept']=='CustomZephyr');self.assertIn(jid,p['desirable_jobs'])
 def test_custom_alias(self):
  jid=self.add('CZLang is required.');add_concept(self.db,'CustomZephyr',['CZLang']);p=next(x for x in self.report()['priorities'] if x['concept']=='CustomZephyr');self.assertIn(jid,p['required_jobs'])
 def test_plus_variants(self):
  for text in ['Plus: pandas.','- plus pandas.','plus pandas and Excel.']:
   jid=self.add(text);self.assertTrue(all(x['effective_status']=='desirable' for x in self.job(jid)['concepts']))
 def test_plus_not_general_proximity(self):
  for text in ['not plus pandas.','pandas plus experience.','plus pandas is not required.']:
   jid=self.add(text);self.assertNotEqual(self.job(jid)['concepts'][0]['effective_status'],'desirable')
 def test_filter_only_metadata(self):
  jid=self.add('Python is required.');rows=search_listings(self.report(),'',selected_locations=['bonn'],selected_work_types=['Contract'])['results'];self.assertEqual([x['job_id'] for x in rows],[jid]);self.assertEqual(rows[0]['metadata']['company'],'Example');self.assertEqual(rows[0]['description_text'],'Python is required.')
 def test_query_with_metadata(self):
  jid=self.add('Python is required.');self.assertEqual([x['job_id'] for x in search_listings(self.report(),'Python',selected_locations=['Bonn'])['results']],[jid])
 def test_missing_metadata(self):
  jid=self.add('Python is required.','','');r=self.report()
  self.assertNotIn(jid,[x['job_id'] for x in search_listings(r,'',selected_locations=['Bonn'])['results']]);self.assertIn(jid,[x['job_id'] for x in search_listings(r,'',selected_locations=['Bonn'],include_unknown=True)['results']])
 def test_review_preserved(self):
  jid=self.add('plus pandas.');j=self.job(jid);m=j['concepts'][0]['evidence'][0]
  ext.save_review(self.db,jid,j['job']['description_text'],dict(m,requirement_status=m['automatic_status']),'required','Manual fixture')
  self.assertEqual(self.job(jid)['concepts'][0]['effective_status'],'required')
 def test_mixed_mentions_review(self):
  jid=self.add('pandas is required. plus pandas.');self.assertEqual(self.job(jid)['concepts'][0]['effective_status'],'uncertain')
 def test_browse_empty_collection(self):
  r=self.report();r['jobs']=[];self.assertEqual(search_listings(r,'')['results'],[])
 def test_metadata_no_false_keyword_match(self):
  self.add('Python is required.');self.assertEqual(search_listings(self.report(),'Bonn')['results'],[])
