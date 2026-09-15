import json, pathlib
for path, old, new in [('README.md', '# 764 Python tests', '# 766 Python tests')]:
    p = pathlib.Path(path)
    t = p.read_text()
    assert t.count(old) == 1, (path, t.count(old))
    p.write_text(t.replace(old, new, 1))
h = pathlib.Path('data/registry/hardening-progress.json')
d = json.loads(h.read_text())
assert d['language_voice_batch']['automated_tests'] == 764
d['language_voice_batch']['automated_tests'] = 766
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
print('updated')