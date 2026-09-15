import pathlib
p = pathlib.Path('web/index.html')
t = p.read_text()
old = 'placeholder="Will it rain in Ahmedabad tomorrow morning?"'
assert t.count(old) == 1, t.count(old)
t = t.replace(old, 'placeholder="What is it like right now in Ahmedabad?"', 1)
p.write_text(t)
print('composer placeholder refreshed')