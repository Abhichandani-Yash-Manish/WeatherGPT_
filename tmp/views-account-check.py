import pathlib
p = pathlib.Path('tests/test_views.js')
t = p.read_text()
snippet = pathlib.Path('tmp/views-account-snippet.js').read_text()
anchor = 'console.log(' + chr(39) + 'PASS: two products in one turn are compared in plain terms and never ranked' + chr(39) + ');'
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, snippet + chr(10) + anchor, 1)
p.write_text(t)
print('check inserted into test_views.js')