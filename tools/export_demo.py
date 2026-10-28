"""Export the chosen full SQLite workspace as a versionable SQL seed."""
from pathlib import Path
import argparse
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jobfit.demo_seed import SEED, export_workspace

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, default=SEED)
    parser.add_argument('--replace', action='store_true')
    args = parser.parse_args()
    source = args.source
    if source is None:
        try:
            import tkinter as tk
            from tkinter.filedialog import askopenfilename
            window = tk.Tk(); window.withdraw()
            try:
                selected = askopenfilename(title='Select your populated JobFit database or downloaded backup',
                    filetypes=[('SQLite database', '*.db *.sqlite *.sqlite3'), ('All files', '*.*')])
            finally:
                window.destroy()
        except Exception as exc:
            parser.error('File picker unavailable. Use --source "FULL DATABASE PATH". ' + str(exc))
        if not selected:
            parser.exit(1, 'No file selected. Nothing exported.\n')
        source = Path(selected)
    try:
        report = export_workspace(source, args.output, args.replace)
    except Exception as exc:
        parser.exit(1, 'Export stopped: ' + str(exc) + '\n')
    print(json.dumps({'jobs': report['tables']['jobs']['rows'],
                     'profiles': report['profiles'],
                     'skill_statements': report['tables']['candidate_skills']['rows'],
                     'languages': report['languages'],
                     'technical_reviews': report['tables']['navigator_reviews_v2']['rows'],
                     'output': str(args.output.resolve())}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
