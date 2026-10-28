"""Standalone tests of complete export, restoration and per-session copies."""
from contextlib import closing
from pathlib import Path
import importlib.util
import json
import sqlite3
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('demo_seed_under_test', ROOT / 'jobfit/demo_seed.py')
seed = importlib.util.module_from_spec(spec); spec.loader.exec_module(seed)

class DemoSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.db = self.root/'source.db'; self.sql=self.root/'workspace.sql'
        with closing(sqlite3.connect(self.db)) as c:
            c.executescript("""
            CREATE TABLE candidates(candidate_id INTEGER PRIMARY KEY,display_name TEXT);
            CREATE TABLE skills(skill_id INTEGER PRIMARY KEY,canonical_name TEXT);
            CREATE TABLE candidate_skills(candidate_id INTEGER,skill_id INTEGER,evidence_status TEXT,evidence_note TEXT,
              FOREIGN KEY(candidate_id) REFERENCES candidates(candidate_id), FOREIGN KEY(skill_id) REFERENCES skills(skill_id));
            CREATE TABLE jobs(job_id INTEGER PRIMARY KEY,title TEXT,description_text TEXT);
            CREATE TABLE skill_aliases(alias TEXT,skill_id INTEGER);
            CREATE TABLE navigator_languages_v2(candidate_id INTEGER,language TEXT,reported_level TEXT,note TEXT);
            CREATE TABLE navigator_preferences_v3(candidate_id INTEGER,payload TEXT);
            CREATE TABLE navigator_metadata_v3(job_id INTEGER,location TEXT);
            CREATE TABLE navigator_reviews_v2(job_id INTEGER,source_hash TEXT,note TEXT);
            CREATE TABLE jobfit_revisions(revision_id INTEGER,record_json TEXT);
            CREATE TABLE empty_history(value TEXT);
            INSERT INTO candidates VALUES(1,'bhanu'),(2,'test');
            INSERT INTO skills VALUES(1,'Python');
            INSERT INTO candidate_skills VALUES(1,1,'evidenced','Coursework Project');
            INSERT INTO navigator_languages_v2 VALUES(1,'German','A1','Learning');
            INSERT INTO skill_aliases VALUES('python',1);
            INSERT INTO navigator_preferences_v3 VALUES(1,'{"role_areas":["NLP"],"locations":["Trier"],"work_types":["Internship"]}');
            INSERT INTO navigator_metadata_v3 VALUES(1,'Trier');
            INSERT INTO navigator_reviews_v2 VALUES(1,'exact-original-hash','keep');
            INSERT INTO jobfit_revisions VALUES(1,'{"original":"unchanged"}');
            """)
            c.execute('INSERT INTO jobs VALUES(?,?,?)',(1,"German's role",'Python is required. \nDeutsch B2 ist erforderlich.\n'))
            c.execute('INSERT INTO jobs VALUES(?,?,?)',(7,'Second role',None)); c.commit()
    def export(self): return seed.export_workspace(self.db,self.sql)
    def open(self, initialise=lambda p: None):
        h,p=seed.open_workspace(initialise,self.sql); self.addCleanup(h.cleanup); return p
    def state(self,path):
        with closing(sqlite3.connect(path)) as c: return seed.logical_state(c)
    def test_all_rows_round_trip(self):
        self.export(); self.assertEqual(self.state(self.db),self.state(self.open()))
    def test_source_is_unchanged(self):
        before=self.db.read_bytes(); self.export(); self.open(); self.assertEqual(self.db.read_bytes(),before)
    def test_profiles_languages_notes_and_preferences(self):
        self.export(); p=self.open()
        with closing(sqlite3.connect(p)) as c:
            self.assertEqual(c.execute('SELECT display_name FROM candidates ORDER BY candidate_id').fetchall(),[('bhanu',),('test',)])
            self.assertEqual(c.execute('SELECT language,reported_level,note FROM navigator_languages_v2').fetchone(),('German','A1','Learning'))
            self.assertEqual(c.execute('SELECT evidence_note FROM candidate_skills').fetchone(),('Coursework Project',))
            self.assertEqual(json.loads(c.execute('SELECT payload FROM navigator_preferences_v3').fetchone()[0])['locations'],['Trier'])
    def test_session_edits_are_separate(self):
        self.export(); a=self.open(); b=self.open()
        with closing(sqlite3.connect(a)) as c: c.execute('DELETE FROM jobs'); c.commit()
        with closing(sqlite3.connect(b)) as c: self.assertEqual(c.execute('SELECT COUNT(*) FROM jobs').fetchone()[0],2)
    def test_reopening_restores_starting_data(self):
        self.export(); a=self.open()
        with closing(sqlite3.connect(a)) as c: c.execute('DELETE FROM jobs'); c.commit()
        self.assertEqual(self.state(self.open()),self.state(self.db))
    def test_seed_bytes_do_not_change(self):
        self.export(); before=self.sql.read_bytes(); self.open(); self.assertEqual(self.sql.read_bytes(),before)
    def test_text_and_null_preserved(self):
        self.export(); p=self.open()
        with closing(sqlite3.connect(p)) as c:
            rows=c.execute('SELECT job_id,description_text FROM jobs ORDER BY job_id').fetchall()
        self.assertEqual(rows,[(1,'Python is required. \nDeutsch B2 ist erforderlich.\n'),(7,None)])
    def test_manifest_mismatch_fails(self):
        self.export(); self.sql.write_text(self.sql.read_text(encoding='utf-8')+'\n',encoding='utf-8')
        with self.assertRaises(ValueError): self.open()
    def test_missing_seed_fails(self):
        with self.assertRaises(FileNotFoundError): self.open()
    def test_existing_export_not_overwritten(self):
        self.export()
        with self.assertRaises(FileExistsError): self.export()
    def test_initialiser_may_add_but_not_rewrite_records(self):
        self.export()
        def add(p):
            with closing(sqlite3.connect(p)) as c: c.execute('INSERT INTO skills VALUES(2,"SQL")'); c.commit()
        self.open(add)
        def change(p):
            with closing(sqlite3.connect(p)) as c: c.execute('UPDATE candidates SET display_name="changed" WHERE candidate_id=1'); c.commit()
        with self.assertRaises(ValueError): self.open(change)
    def test_invalid_foreign_key_fails_export(self):
        with closing(sqlite3.connect(self.db)) as c: c.execute('INSERT INTO candidate_skills VALUES(99,1,"developing",NULL)'); c.commit()
        with self.assertRaises(ValueError): self.export()
    def test_empty_tables_preserved(self):
        self.export(); self.assertIn('empty_history',self.state(self.open()))

if __name__ == '__main__': unittest.main()
