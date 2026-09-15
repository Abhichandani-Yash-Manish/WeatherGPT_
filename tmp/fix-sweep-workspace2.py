import pathlib
p = pathlib.Path('scripts/ingest_state_agromet.py')
t = p.read_text()
old = """    def clock(self):
        return datetime.now(timezone.utc)"""
assert t.count(old) == 1, t.count(old)
new = """    opener = None

    def clock(self):
        return datetime.now(timezone.utc)"""
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')