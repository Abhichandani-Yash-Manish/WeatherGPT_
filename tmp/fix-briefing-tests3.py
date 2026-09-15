import pathlib
p = pathlib.Path('tests/test_briefing_run.py')
t = p.read_text()
old = """        for match in re.finditer('all-clear', text.lower()):
            self.assertIn(text.lower()[max(0, match.start() - 10):match.start()], ('s not an ', ' not an ', ' is not an ', 'not an '),
                          'an all-clear is only ever named as something this is not')"""
assert t.count(old) == 1
new = """        for match in re.finditer('all-clear', text.lower()):
            window = text.lower()[max(0, match.start() - 12):match.start()]
            self.assertIn('not', window, 'an all-clear is only ever named as something this is not')"""
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')
