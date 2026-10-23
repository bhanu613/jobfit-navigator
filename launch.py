"""Persistent local startup; load torch before Streamlit."""
import os,sys,runpy
from pathlib import Path

def main():
 os.chdir(Path(__file__).resolve().parent)
 os.environ['JOBFIT_MODE']='local'
 os.environ.setdefault('JOBFIT_DB',str(Path('data/navigator_local.db').resolve()))
 try:
  import torch
 except Exception as exc:
  print('Semantic runtime unavailable; BM25 remains available:',exc,file=sys.stderr)
 sys.argv=['streamlit','run','app.py','--server.address=127.0.0.1','--server.fileWatcherType=none']
 runpy.run_module('streamlit',run_name='__main__')
if __name__=='__main__':main()
