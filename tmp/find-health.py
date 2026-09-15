import pathlib
p = pathlib.Path('web/app.js')
t = p.read_text()
anchor = None
for candidate in ('function renderHealth(', 'function paintHealth('):
    if candidate in t:
        anchor = candidate
        break
assert anchor, 'health renderer not found'
print('renderer:', anchor)