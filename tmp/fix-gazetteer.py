import pathlib
p = pathlib.Path('weathergpt_data/gazetteer.py')
t = p.read_text()
bad = "'state_match_basis':state_basis'other_alias_matches'"
assert t.count(bad) == 1, t.count(bad)
t = t.replace(bad, "'state_match_basis':state_basis,'other_alias_matches'", 1)
p.write_text(t)
print('fixed')