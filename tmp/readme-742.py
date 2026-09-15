import pathlib
p = pathlib.Path('README.md')
t = p.read_text()
assert t.count('# 726 Python tests') == 1
t = t.replace('# 726 Python tests', '# 742 Python tests', 1)
p.write_text(t)
print('readme')
