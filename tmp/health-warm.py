import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
t = p.read_text()
old = "        return {'schema_version':'source-health-v1','available':True,"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, old + "\n                'warm':getattr(self,'warm_state',None),", 1)
p.write_text(t)
print('health carries the warm state')