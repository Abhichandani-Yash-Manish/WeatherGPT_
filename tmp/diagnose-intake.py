"""Diagnose the intake failure: which family, which sha, and what differs."""
import json, pathlib, sys, traceback
sys.path.insert(0, 'weathergpt_data')
sys.path.insert(0, '.')
from weathergpt_data.document_ingest import ingest
from weathergpt_data.transport import Store

ROOT = pathlib.Path('.').resolve()
store = Store(ROOT / 'data/runtime/documents')
runtime = ROOT / 'data/runtime/ingestion'
for family in ('national_bulletin', 'flash_flood_national', 'sea_area_bulletin', 'coastal_bulletin'):
    try:
        report = ingest(store, runtime, family)
        print('OK  ', family, report.get('status'), '| accepted', len(report.get('accepted') or []), '| rejected', len(report.get('rejected') or []))
    except Exception as error:  # noqa: BLE001
        print('FAIL', family, type(error).__name__, str(error)[:120])
        traceback.print_exc(limit=3)
        break
