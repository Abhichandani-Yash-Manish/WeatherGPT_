import pathlib
p = pathlib.Path('web/panels.js')
t = p.read_text()
snippet = pathlib.Path('tmp/views-provider-snippet.js').read_text()
anchor = "    sourceCard.append(el('p', 'A registered source is not a serving approval, and a tested adapter is not operational readiness.', 'field-note'));"
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, anchor + chr(10) + snippet, 1)
p.write_text(t)
print('settings provider card added')