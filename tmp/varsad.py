import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
old = r"|barish|baarish|varsha|barsat|paani|"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, r"|barish|baarish|varsha|varsad|barsat|paani|", 1)
p.write_text(t)
print('patched')