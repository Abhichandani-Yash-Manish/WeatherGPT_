import pathlib
p = pathlib.Path('web/views.js')
t = p.read_text()
snippet = pathlib.Path('tmp/views-warm-snippet.js').read_text()
anchor = 'function renderHealth(health) {'
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, snippet + chr(10) + anchor, 1)
old = "  if (!health.available) { box.append(el('p', health.note || 'No collection history.', 'block-note')); return; }"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, old + chr(10) + '  renderWarmState(health, box);', 1)
p.write_text(t)
print('warm state rendered')