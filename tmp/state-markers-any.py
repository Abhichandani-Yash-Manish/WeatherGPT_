import pathlib
p = pathlib.Path('weathergpt_data/document_ingest.py')
t = p.read_text()
old = "        markers=['agromet advisory service bulletin', 'मौसम सलाहकार', 'संयुक्त क'],"
assert t.count(old) == 1, t.count(old)
new = "        markers=[],\n        markers_any=['agromet advisory service bulletin', 'मौसम सलाहकार', 'संयुक्त क'],"
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')