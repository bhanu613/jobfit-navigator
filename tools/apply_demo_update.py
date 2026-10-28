"""Apply narrow startup/docs changes; validate all targets before writing."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import json
import shutil
ROOT=Path(__file__).resolve().parents[1]

def replace_once(text,old,new,name):
    if text.count(old)!=1:
        raise ValueError('Expected text differs in '+name+'. Nothing changed. Use the latest main checkout.')
    return text.replace(old,new,1)

def main():
    if not (ROOT/'demo/workspace.sql').is_file() or not (ROOT/'demo/workspace.json').is_file():
        raise ValueError('Export your populated workspace first: python tools/export_demo.py')
    marker='def public_demo():'
    workspace=(ROOT/'jobfit/workspace.py').read_text(encoding='utf-8')
    if marker in workspace:
        raise ValueError('Startup patch already exists. Do not apply it twice.')
    additions={}
    additions['jobfit/workspace.py']=workspace+'\n\ndef public_demo():\n from .demo_seed import open_workspace\n return open_workspace(setup)\n'
    app=(ROOT/'app.py').read_text(encoding='utf-8')
    additions['app.py']=replace_once(app,'st.session_state.workspace=ws.demo()',
                                      'st.session_state.workspace=ws.public_demo()','app.py')
    ui=(ROOT/'tests/test_ui.py').read_text(encoding='utf-8')
    ui=replace_once(ui,' def setUp(self):\n',' def setUp(self):\n  from unittest.mock import patch\n  from jobfit import workspace as ws\n  fixture=patch("jobfit.workspace.public_demo",side_effect=ws.demo)\n  fixture.start();self.addCleanup(fixture.stop)\n','tests/test_ui.py')
    additions['tests/test_ui.py']=ui
    gitignore=(ROOT/'.gitignore').read_text(encoding='utf-8')
    additions['.gitignore']=gitignore.rstrip()+'\n\n# Published demo seed; other database and SQL files remain ignored.\n!demo/workspace.sql\n'
    readme=(ROOT/'README.md').read_text(encoding='utf-8')
    old='The online demo uses fictional data in a temporary workspace. It is not intended for storing personal data permanently.'
    new='The demo opens with 22 saved listings, the `bhanu` and `test` profiles, and the skill notes, language records and reviews used during development. You can explore these examples or create a new profile. Changes stay in your session; **Reset demo workspace** restores the starting data.\n\nTo try it: select `bhanu`, search for `AWS`, open a comparison, or inspect German and English wording in `german comp. incl. bavaria`. Switch to `test` to see different profile statements.'
    readme=replace_once(readme,old,new,'README.md Live demo')
    readme=replace_once(readme,'Demo mode starts with temporary fictional data.',
                       'Demo mode creates a session copy of the published workspace seed.','README.md How it works')
    readme=replace_once(readme,'The demo uses fictional session data. Use the local launcher for a persistent workspace.',
                       'The demo loads the published workspace into a temporary session. Use the local launcher for a persistent workspace.','README.md Run a demo')
    readme=replace_once(readme,'All 64 automated tests passed on Windows with Python 3.12. Manual checks also covered sidebar navigation, requirement interpretation for a fictional listing and a real semantic search.',
                       'The previous release passed 64 automated tests on Windows with Python 3.12. Run the full suite for this update, including the published-workspace and session-isolation checks. The demo export also verifies that every exported table row survives a round trip.','README.md Testing')
    readme=replace_once(readme,'- `app.py`: Streamlit interface','- `demo/`: published workspace SQL seed and integrity manifest\n- `app.py`: Streamlit interface','README.md Project layout')
    additions['README.md']=readme
    arch=(ROOT/'docs/ARCHITECTURE.md').read_text(encoding='utf-8')
    additions['docs/ARCHITECTURE.md']=replace_once(arch,'- **Demo:** starts a temporary session with fictional data.',
        '- **Demo:** restores `demo/workspace.sql` into a new temporary database for each session. The seed includes listings, profiles, language statements, aliases and saved reviews. Reset creates a fresh copy. `workspace.demo()` remains the small automated-test fixture; the UI calls `workspace.public_demo()`.','docs/ARCHITECTURE.md')
    for name,content in additions.items():
        if name.endswith('.py'):ast.parse(content,filename=name)
    backup=ROOT/('release-backup-demo-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    backup.mkdir()
    written=[]
    try:
        for name in additions:
            target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
        for name,content in additions.items():
            written.append(name);(ROOT/name).write_text(content,encoding='utf-8')
    except Exception:
        for name in written:shutil.copy2(backup/name,ROOT/name)
        raise
    print(json.dumps({'updated':list(additions),'backup':str(backup)},indent=2))

if __name__=='__main__':main()
