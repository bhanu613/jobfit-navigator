import unittest,tempfile,importlib.util,ast
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jobfit import workspace as w,navigator_service as s
ROOT=Path(__file__).resolve().parents[1]
class Packaging(unittest.TestCase):
 def test_updater_preserves_launcher_and_database(self):
  h,db=w.demo()
  try:
   target=Path(h.name)/'existing';(target/'data').mkdir(parents=True);(target/'app.py').write_text('original');(target/'Start-Local.ps1').write_text('original launcher');w.import_database(db,target/'data/navigator_local.db')
   spec=importlib.util.spec_from_file_location('release_updater',ROOT/'tools/update_existing.py');up=importlib.util.module_from_spec(spec);spec.loader.exec_module(up)
   backup=up.update(ROOT,target)
   self.assertEqual((backup/'app.py').read_text(),'original');self.assertEqual((backup/'Start-Local.ps1').read_text(),'original launcher');self.assertEqual((target/'Start-Local.ps1').read_text(),(ROOT/'Start-Local.ps1').read_text());self.assertTrue((backup/'navigator_local.db').is_file());self.assertEqual(len(s.list_jobs(database_path=target/'data/navigator_local.db')),3)
  finally:h.cleanup()
 def test_source_syntax(self):
  for path in ROOT.rglob('*.py'):
   if not any(part.startswith('.venv') or part.startswith('release-backup-') for part in path.parts):ast.parse(path.read_text(encoding='utf-8'))
