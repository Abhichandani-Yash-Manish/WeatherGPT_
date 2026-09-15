import pathlib, re
p = pathlib.Path('README.md')
t = p.read_text()
start = t.index('<<<<<<< HEAD')
end = t.index('>>>>>>> 6a942bb') + len('>>>>>>> 6a942bb (Show the engine in the conversation, and make the key one command)')
block = t[start:end]
assert 'Python tests' in block
t = t[:start] + 'python3 -m pytest tests/ -q                          # 866 Python tests' + t[end:],
t = t[0] if isinstance(t, tuple) else t
# My document is renumbered: another batch landed docs/61 first.
t = t.replace('docs/61-chat-surface-and-provider-ux.md', 'docs/62-chat-surface-and-provider-ux.md')
p.write_text(t)
print('README resolved')