"""Serve the React build on 8797 with a throwaway store, for the R1 browser evidence."""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import Workspace, make_server

store = ROOT / 'tmp/r1-browser'
store.mkdir(parents=True, exist_ok=True)
for stale in store.glob('*'):
    stale.unlink()
shutil.copyfile(ROOT / 'data/runtime/ingestion/ingestion.sqlite', store / 'ingestion.sqlite')
server = make_server(Workspace(database=store / 'ingestion.sqlite', frontend='react'), 8797)
print('react shell on http://127.0.0.1:8797', flush=True)
server.serve_forever()
