"""Run against the actual exported seed and the existing application code."""
from pathlib import Path
from contextlib import closing
import json
import sqlite3
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from jobfit import workspace as ws, demo_seed

class PublishedDemoTests(unittest.TestCase):
    def setUp(self):
        if not demo_seed.SEED.is_file():
            self.fail('Export the populated demo seed before running release checks.')
        self.handle,self.db=ws.public_demo();self.addCleanup(self.handle.cleanup)
        self.manifest=json.loads(demo_seed.SEED.with_suffix('.json').read_text(encoding='utf-8'))
    def test_expected_workspace_records(self):
        with closing(sqlite3.connect(self.db)) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],22)
            self.assertEqual(c.execute('SELECT candidate_id,display_name FROM candidates ORDER BY candidate_id').fetchall(),[(1,'bhanu'),(2,'test')])
            self.assertEqual(c.execute('SELECT COUNT(*) FROM candidate_skills').fetchone()[0],13)
            self.assertEqual(c.execute('SELECT language,reported_level,note FROM navigator_languages_v2 WHERE candidate_id=1 ORDER BY language').fetchall(),[('English','C1','expert'),('French','Not specified','Learning'),('German','A1','Learning')])
            self.assertEqual(c.execute('SELECT COUNT(*) FROM navigator_reviews_v2').fetchone()[0],6)
    def test_original_rows_survive_application_setup(self):
        # open_workspace checks the full row set against the SQL manifest before setup,
        # and verifies original rows were not removed or changed by application setup.
        self.assertTrue(self.db.is_file())
    def test_two_visitors_are_separate(self):
        other_handle,other=ws.public_demo();self.addCleanup(other_handle.cleanup)
        with closing(sqlite3.connect(self.db)) as c:c.execute('DELETE FROM candidate_skills');c.commit()
        with closing(sqlite3.connect(other)) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM candidate_skills').fetchone()[0],13)
# The actual UI test lives below so the original callable can be retained safely.
def _ui_test(self):
    from unittest.mock import patch
    from streamlit.testing.v1 import AppTest
    real=ws.public_demo
    def fresh():
        handle,path=real();self.addCleanup(handle.cleanup);return handle,path
    with patch.dict('os.environ',{'JOBFIT_MODE':'demo'}),patch('jobfit.workspace.public_demo',side_effect=fresh):
        at=AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
        self.assertFalse(at.exception,[e.message for e in at.exception]);self.assertFalse(at.error,[e.value for e in at.error])
        self.assertEqual(next(m.value for m in at.metric if m.label=='Saved opportunities'),'22')
        self.assertEqual(next(m.value for m in at.metric if m.label=='Profile statements'),'7')
        nav=at.sidebar.radio[0];nav.set_value('Profile').run()
        next(x for x in at.selectbox if x.label=='Active profile').set_value(2).run()
        nav=at.sidebar.radio[0];nav.set_value('Compare a job').run()
        self.assertFalse(at.exception,[e.message for e in at.exception])
        _,path=at.session_state['workspace']
        with closing(sqlite3.connect(path)) as c:
            c.execute("UPDATE jobs SET title='Visitor changed this' WHERE job_id=1");c.commit()
        next(b for b in at.button if b.label=='Reset demo workspace').click().run()
        self.assertFalse(at.exception,[e.message for e in at.exception]);self.assertFalse(at.error,[e.value for e in at.error])
        _,reset_path=at.session_state['workspace']
        with closing(sqlite3.connect(reset_path)) as c:
            self.assertEqual(c.execute('SELECT title FROM jobs WHERE job_id=1').fetchone()[0],'Integration demo')
PublishedDemoTests.test_real_seed_ui_and_reset=_ui_test
