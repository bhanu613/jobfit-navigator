from contextlib import closing
import unittest,sys,sqlite3,hashlib,tempfile,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jobfit import workspace as w,jobfit_navigation_engine as n
from jobfit.concept_management import add_concept
ROOT=Path(__file__).resolve().parents[1]
class Final(unittest.TestCase):
 def setUp(self):self.h,self.db=w.demo()
 def tearDown(self):self.h.cleanup()
 def terms(self):
  for name in ['Java','JavaScript','Transformers','Hugging Face','Agentic AI','Prompt engineering']:add_concept(self.db,name,[])
 def states(self,text):
  jid=w.save_listing(self.db,None,dict(title='Fixture',description_text=text,source_description='Synthetic',source_url=None),dict(company='',location='',work_type='',source_language=''))
  row=next(j for j in n.candidate_report(self.db,1)['jobs'] if j['job']['job_id']==jid)
  return {c['canonical_name']:c['effective_status'] for c in row['concepts']}
 def test_plus_comma(self):
  s=self.states('python, sql, aws, powerbi are a plus.');self.assertEqual(len(s),4);self.assertEqual(set(s.values()),{'desirable'})
 def test_unknown(self):self.assertEqual(self.states('Python, UnknownZephyr are a plus.')['Python'],'uncertain')
 def test_unknown_between_known(self):self.assertEqual(set(self.states('Python, UnknownZephyr, SQL are a plus.').values()),{'uncertain'})
 def test_java(self):
  self.terms();self.assertEqual(self.states('i need a guy experienced in java and javascript'),{'Java':'required','JavaScript':'required'})
 def test_nlp(self):
  self.terms();s=self.states('transformers, hugging face, llms knowledge is needed.\npython, sql, aws, powerbi are a plus.\nstrictly need someone with experience in agentic ai, prompt engineering')
  for name in ['Transformers','Hugging Face','Large language models','Agentic AI','Prompt engineering']:self.assertEqual(s[name],'required')
  for name in ['Python','SQL','Amazon Web Services','Power BI']:self.assertEqual(s[name],'desirable')
 def test_negation(self):self.assertEqual(set(self.states('Python and SQL are not required.').values()),{'not_required'})
 def test_learning(self):self.assertEqual(set(self.states('we need someone willing to learn Python and SQL').values()),{'uncertain'})
 def test_mixed(self):self.assertEqual(self.states('Python is required. Python is desirable.')['Python'],'uncertain')
 def test_plus_but(self):self.assertNotIn('desirable',self.states('Python, SQL are a plus but not required.').values())
 def test_launcher(self):
  self.assertNotIn('pip install',(ROOT/'Start-Local.ps1').read_text());t=(ROOT/'launch.py').read_text();self.assertLess(t.index('import torch'),t.index('runpy.run_module'))
 def test_existing_alias_collision(self):
  sid=add_concept(self.db,'JVM fixture',['Java'])
  with self.assertRaises(ValueError):add_concept(self.db,'Java',[])
  with closing(sqlite3.connect(self.db)) as c:self.assertEqual(c.execute('SELECT skill_id FROM skill_aliases WHERE alias=?',('java',)).fetchone()[0],sid)
 def test_update_preserves_bytes_and_environment(self):
  with tempfile.TemporaryDirectory() as d:
   t=Path(d);(t/'app.py').write_text('old');(t/'data').mkdir();w.import_database(self.db,t/'data/navigator_local.db');(t/'.venv').mkdir();(t/'.venv/sentinel').write_text('keep');before=hashlib.sha256((t/'data/navigator_local.db').read_bytes()).hexdigest()
   spec=importlib.util.spec_from_file_location('update_final',ROOT/'tools/update_existing.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u);backup=u.update(ROOT,t)
   self.assertEqual(before,hashlib.sha256((t/'data/navigator_local.db').read_bytes()).hexdigest());self.assertEqual((t/'.venv/sentinel').read_text(),'keep');self.assertEqual((backup/'app.py').read_text(),'old');self.assertTrue((t/'launch.py').exists())
