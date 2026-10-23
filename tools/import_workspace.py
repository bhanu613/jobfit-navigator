from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from jobfit.workspace import import_database,setup
from jobfit.job_store import create_candidate
p=Path(__file__).resolve().parents[1]/'data/navigator_local.db'
source=input('Existing database path, or Enter for a new workspace: ').strip().strip('"')
if source:print('Copied to',import_database(source,p))
else:
 if p.exists():raise ValueError('Workspace already exists. Nothing overwritten.')
 p.parent.mkdir(parents=True,exist_ok=True);setup(p);create_candidate('My profile',database_path=p);print('Created',p)
