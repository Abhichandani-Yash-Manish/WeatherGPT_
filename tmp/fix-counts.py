import json, pathlib
r = pathlib.Path('README.md')
t = r.read_text()
assert t.count('# 866 Python tests') == 1
r.write_text(t.replace('# 866 Python tests', '# 860 Python tests', 1))
h = pathlib.Path('data/registry/hardening-progress.json')
d = json.loads(h.read_text())
if d['chat_surface_batch']['automated_tests'] != 860:
    d['chat_surface_batch']['automated_tests'] = 860
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
print('counts set to the measured 860')