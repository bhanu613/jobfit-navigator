from pathlib import Path
import sqlite3,sys,shutil,ast,json
from datetime import datetime,timezone

def update(source,target):
 source=Path(source).resolve();target=Path(target).resolve()
 if source==target or source in target.parents or target in source.parents or not (target/'app.py').is_file():raise ValueError('Extract separately and select an existing application folder containing app.py.')
 managed=['app.py', 'launch.py', 'requirements.txt', 'requirements-semantic.txt', 'Start-Local.ps1', 'Start-Local.cmd', 'Setup-Local.ps1', 'Setup-Local.cmd', 'Install-Semantic.ps1', 'README.md', '.gitignore', '.streamlit/config.toml']
 files=managed+[str(p.relative_to(source)) for p in (source/'docs').rglob('*.md')]+[str(p.relative_to(source)) for folder in ['jobfit','tests','tools'] for p in (source/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.json')]
 for name in files:
  if not (source/name).is_file():raise ValueError('Package file missing: '+name)
  if name.endswith('.py'):ast.parse((source/name).read_text(encoding='utf-8'))
 backup=target/('release-backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));backup.mkdir()
 db=target/'data/navigator_local.db'
 if db.exists():
  a=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True);b=sqlite3.connect(backup/'navigator_local.db')
  try:
   if a.execute('PRAGMA quick_check').fetchone()!=('ok',):raise ValueError('Existing database integrity check failed.')
   a.backup(b)
  finally:a.close();b.close()
 manifest={}
 for name in files:
  p=target/name;manifest[name]=p.exists()
  if p.exists():
   dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 (backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
 written=[]
 try:
  for name in files:
   dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True);written.append(name);shutil.copy2(source/name,dest)
 except Exception:
  for name in reversed(written):
   if manifest[name]:shutil.copy2(backup/name,target/name)
   else:(target/name).unlink(missing_ok=True)
  raise
 return backup
if __name__=='__main__':print('Application source updated; database and environment retained. Backup:',update(Path(__file__).resolve().parents[1],sys.argv[1]))
