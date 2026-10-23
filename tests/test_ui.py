import unittest,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest
class UI(unittest.TestCase):
 def setUp(self):
  self.old=os.environ.get('JOBFIT_MODE');os.environ['JOBFIT_MODE']='demo';self.at=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=12).run();self.clean()
 def tearDown(self):
  if self.old is None:os.environ.pop('JOBFIT_MODE',None)
  else:os.environ['JOBFIT_MODE']=self.old
 def clean(self):self.assertFalse(self.at.exception,[x.message for x in self.at.exception]);self.assertFalse(self.at.error,[x.value for x in self.at.error])
 def go(self,p):self.at.sidebar.radio[0].set_value(p).run();self.clean()
 def choose(self,label,value):next(x for x in self.at.selectbox if x.label==label).set_value(value).run();self.clean()
 def click(self,label):next(x for x in self.at.button if x.label==label).click().run();self.clean()
 def test_all_pages(self):
  for p in ['Overview','Job library','Find opportunities','Compare a job','Collection insights','Profile','Manage concepts','About']:self.go(p)
 def test_comparison_persistence(self):
  self.go('Compare a job');self.choose('Choose saved listing',2);self.go('Profile');self.go('Compare a job');self.assertEqual(next(x.value for x in self.at.selectbox if x.label=='Choose saved listing'),2)
 def test_search_persistence_and_open(self):
  self.go('Find opportunities');next(x for x in self.at.text_input if x.label=='What are you looking for?').set_value('Python').run();self.click('Search saved jobs');self.go('Profile');self.go('Find opportunities');self.assertEqual(next(x.value for x in self.at.text_input if x.label=='What are you looking for?'),'Python');self.click('Open comparison');self.assertEqual(self.at.sidebar.radio[0].value,'Compare a job')
 def test_concept_creation_ui(self):
  self.go('Manage concepts');next(x for x in self.at.text_input if x.label=='New concept name').set_value('Rust').run();next(x for x in self.at.checkbox if x.label=='I checked the name and aliases for ambiguity').check().run();self.click('Add concept');self.go('Profile');self.assertTrue(any('Rust' in str(x.options) for x in self.at.selectbox))
 def test_profile_switch_no_search_leak(self):
  self.go('Find opportunities');next(x for x in self.at.text_input if x.label=='What are you looking for?').set_value('Python').run()
  next(x for x in self.at.text_input if x.label=='Display name').set_value('Second').run();self.click('Create profile');self.choose('Active profile',2)
  self.assertEqual(next(x.value for x in self.at.text_input if x.label=='What are you looking for?'),'')

 def test_creation_retains_each_page(self):
  for i,page in enumerate(['Job library','Find opportunities','Compare a job','Collection insights','Profile','Manage concepts','About']):
   self.go(page)
   next(x for x in self.at.text_input if x.label=='Display name').set_value('Profile '+str(i)).run()
   self.click('Create profile')
   self.assertEqual(self.at.sidebar.radio[0].value,page)
 def test_switch_back_restores_search(self):
  self.go('Find opportunities')
  next(x for x in self.at.text_input if x.label=='What are you looking for?').set_value('Python').run()
  next(x for x in self.at.text_input if x.label=='Display name').set_value('Second').run()
  self.click('Create profile');self.choose('Active profile',2)
  next(x for x in self.at.text_input if x.label=='What are you looking for?').set_value('SQL').run()
  self.choose('Active profile',1)
  self.assertEqual(next(x.value for x in self.at.text_input if x.label=='What are you looking for?'),'Python')
  self.choose('Active profile',2)
  self.assertEqual(next(x.value for x in self.at.text_input if x.label=='What are you looking for?'),'SQL')

 def test_metadata_filter_browse(self):
  self.go('Job library');self.assertTrue(any(x.value=='Location' for x in self.at.caption));self.go('Find opportunities')
  next(x for x in self.at.multiselect if x.label=='Location').set_value(['Berlin']).run();self.click('Search saved jobs')
  self.assertTrue(any(x.value=='Fictional data role' for x in self.at.subheader));self.assertFalse(any(x.value=='Fictional NLP internship' for x in self.at.subheader));self.assertEqual(len(self.at.json),0)
 def test_empty_query_browses(self):
  self.go('Find opportunities');self.click('Search saved jobs');self.assertEqual(sum(x.label=='Open comparison' for x in self.at.button),3)
 def test_no_results(self):
  self.go('Find opportunities');next(x for x in self.at.text_input if x.label=='What are you looking for?').set_value('zzzxxyyynotfound').run();self.click('Search saved jobs');self.assertTrue(any('No matching' in x.value for x in self.at.info))
 def test_search_edit_requires_resubmit(self):
  self.go('Find opportunities');self.click('Search saved jobs');next(x for x in self.at.text_input if x.label=='What are you looking for?').set_value('SQL').run();self.assertTrue(any('Settings changed' in x.value for x in self.at.info))
 def test_job6_ui_to_collection(self):
  self.go('Job library')
  next(x for x in self.at.text_input if x.label=='Role title').set_value('Job 6 fixture')
  next(x for x in self.at.text_area if x.label=='Listing text').set_value('needed seaborn.\nrequired pytorch.\nplus pandas.\ndesirable excel.\nnot needed git.\nnot required kubernetes')
  next(x for x in self.at.text_input if x.label=='Source description').set_value('Synthetic fixture')
  self.click('Save listing');self.go('Compare a job');self.choose('Choose saved listing',4)
  self.assertTrue(any(x.label=='pandas: Desirable' for x in self.at.expander));self.go('Collection insights')
  frame=self.at.dataframe[0].value;row=frame[frame['Concept']=='pandas'].iloc[0];self.assertEqual(row['Desirable'],1);self.assertEqual(row['Needs review'],0)
 def test_custom_concept_full_ui_workflow(self):
  self.go('Job library');next(x for x in self.at.text_input if x.label=='Role title').set_value('Custom concept fixture')
  next(x for x in self.at.text_area if x.label=='Listing text').set_value('plus CustomZephyr.')
  next(x for x in self.at.text_input if x.label=='Source description').set_value('Synthetic fixture');self.click('Save listing')
  self.go('Manage concepts');next(x for x in self.at.text_input if x.label=='New concept name').set_value('CustomZephyr').run()
  next(x for x in self.at.checkbox if x.label=='I checked the name and aliases for ambiguity').check().run();self.click('Add concept')
  self.go('Compare a job');self.choose('Choose saved listing',4);self.assertTrue(any(x.label=='CustomZephyr: Desirable' for x in self.at.expander))
  self.go('Collection insights');frame=self.at.dataframe[0].value;self.assertEqual(frame[frame['Concept']=='CustomZephyr'].iloc[0]['Desirable'],1)
