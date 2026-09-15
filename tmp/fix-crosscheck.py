import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
old = "        if operation == 'crosscheck':\n            tasks[-1]['changed_fields'] = ['operation']\n"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, '', 1)
p.write_text(t)
print('removed')