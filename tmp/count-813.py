import json, pathlib
p = pathlib.Path('README.md')
t = p.read_text()
assert t.count('# 809 Python tests') == 1
p.write_text(t.replace('# 809 Python tests', '# 813 Python tests', 1))
h = pathlib.Path('data/registry/hardening-progress.json')
d = json.loads(h.read_text())
assert d['paraphrase_robustness_batch']['automated_tests'] == 809
d['paraphrase_robustness_batch']['automated_tests'] = 813
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
print('updated')