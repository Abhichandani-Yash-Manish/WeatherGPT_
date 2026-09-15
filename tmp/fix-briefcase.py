import pathlib
p = pathlib.Path('weathergpt_data/briefcase.py')
text = p.read_text()
old = ("        rendered = ('## The stored payload could not be re-rendered by this version', '',\n"
       "                    'The entry is kept as it was stored. This version of the renderer does not recognise it, so the payload is '\n"
       "                    'quoted rather than paraphrased:', '', '    ' +\n"
       "                    json.dumps(entry['payload'], ensure_ascii=False, indent=2, default=str).replace(chr(10), chr(10) + '    '))")
assert text.count(old) == 1, text.count(old)
new = ("        rendered = chr(10).join(['## The stored payload could not be re-rendered by this version', '',\n"
       "                               'The entry is kept as it was stored. This version of the renderer does not recognise it, so the payload is '\n"
       "                               'quoted rather than paraphrased:', '',\n"
       "                               '    ' + json.dumps(entry['payload'], ensure_ascii=False, indent=2, default=str\n"
       "                                                 ).replace(chr(10), chr(10) + '    ')])")
text = text.replace(old, new, 1)
p.write_text(text)

t = pathlib.Path('tests/test_personas_briefcase.py')
tt = t.read_text()
old_test = ("        self.assertNotIn('value', json.dumps(block))\n"
            "        self.assertNotIn('source_id', json.dumps(block))")
assert tt.count(old_test) == 1
new_test = ("        self.assertEqual(set(block), set(KEYS) | {'note', 'applied'})\n"
            "        self.assertIn('changes no value', block['note'])")
tt = tt.replace(old_test, new_test, 1)
t.write_text(tt)
print('patched')
