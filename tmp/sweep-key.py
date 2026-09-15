import pathlib
p = pathlib.Path('scripts/ingest_state_agromet.py')
t = p.read_text()
old = "        prior = outcomes.get(record['state']) or {}"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "        key = record['state'] + '/' + record.get('centre', '')  # a state can have several centres" + chr(10) + "        prior = outcomes.get(key) or {}", 1)
old2 = "        outcomes[record['state']] = dict(record, history=history)"
assert t.count(old2) == 1, t.count(old2)
t = t.replace(old2, "        outcomes[key] = dict(record, history=history)", 1)
p.write_text(t)
print('patched key')