import pathlib
p = pathlib.Path('weathergpt_data/gazetteer.py')
t = p.read_text()
old = 'def choose_by_probe(candidates, probe, limit=4):'
assert t.count(old) == 1, t.count(old)
t = t.replace(old, 'def choose_by_probe(candidates, probe, limit=8):', 1)
p.write_text(t)
print('limit raised to 8')