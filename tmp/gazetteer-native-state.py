import pathlib
p = pathlib.Path('weathergpt_data/gazetteer.py')
t = p.read_text()
old = "            rows=[r for r in rows if same(r['admin1'],wanted_state)]"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "            against_state=[r for r in rows if same(r['admin1'],wanted_state)]\n            if not against_state and state and not str(state).isascii():\n                # A native-script state name cannot be compared with the catalogue's Latin\n                # admin1 field. Measured live on 15 September 2026: the Devanagari question\n                # found the place and the state filter then emptied the list. The name alone\n                # resolves and the state is disclosed as unused rather than silently dropped.\n                against_state = rows\n                state_basis = ('the state was given in another script and was not used to filter: '\n                               'the name alone resolved')\n            rows = against_state", 1)
p.write_text(t)
print('patched')