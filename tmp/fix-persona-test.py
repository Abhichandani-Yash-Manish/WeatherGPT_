import pathlib
t = pathlib.Path('tests/test_personas_briefcase.py')
tt = t.read_text()
old = """    def test_every_persona_carries_the_registered_keys(self):
        for item in catalogue()['personas']:
            self.assertEqual(tuple(item.keys()), KEYS)"""
assert tt.count(old) == 1
new = """    def test_every_persona_carries_the_registered_keys(self):
        for item in catalogue()['personas']:
            self.assertEqual(set(item), set(KEYS) | {'note'})
            self.assertEqual(item['note'], PERSONA_NOTE)"""
tt = tt.replace(old, new, 1)
t.write_text(tt)
print('patched')
