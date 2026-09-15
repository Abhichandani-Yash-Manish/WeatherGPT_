import pathlib
p = pathlib.Path('weathergpt_data/preflight.py')
t = p.read_text()
old = """            'note': ('A preflight reports states, not permissions: a limited state means part of the workspace is thinner, '"
                     'not that the workspace may not be used.')}"""
assert t.count(old) == 1, t.count(old)
new = """            'note': ('A preflight reports states, not permissions: a limited state means part of the workspace is thinner, '
                     'not that the workspace may not be used.')}"""
t = t.replace(old, new, 1)
p.write_text(t)
print('fixed')
