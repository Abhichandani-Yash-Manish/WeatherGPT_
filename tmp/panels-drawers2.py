import pathlib
p = pathlib.Path('web/panels.js')
t = p.read_text()
snippet = pathlib.Path('tmp/drawers-snippet.js').read_text()
anchor = '  WG.panels.assistant = async function () { /* the conversation is owned by app.js */ };'
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, snippet + anchor, 1)
p.write_text(t)
print('inserted', len(snippet.splitlines()), 'lines')