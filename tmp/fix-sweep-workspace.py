import pathlib
p = pathlib.Path('scripts/ingest_state_agromet.py')
t = p.read_text()
old = """    class _Service:
        raw_root = ROOT / 'data' / 'runtime' / 'ingestion' / 'raw'"""
assert t.count(old) == 1, t.count(old)
new = """    class _Service:
        raw_root = ROOT / 'data' / 'runtime' / 'ingestion' / 'raw'
        ingestion_database = ROOT / 'data' / 'runtime' / 'ingestion' / 'ingestion.sqlite'"""
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')