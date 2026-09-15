import pathlib
p = pathlib.Path('weathergpt_data/gazetteer.py')
t = p.read_text()
old = "                scored=sorted(((difflib.SequenceMatcher(None,norm(candidate),norm(state)).ratio(),candidate)"
assert t.count(old) == 1, t.count(old)
new = ("                def bare(value):return norm(value).removeprefix('state of ').strip()" + chr(10) +
       "                scored=sorted(((difflib.SequenceMatcher(None,bare(candidate),bare(state)).ratio(),candidate)")
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')