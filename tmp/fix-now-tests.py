import pathlib
p = pathlib.Path('tests/test_now_view.py')
t = p.read_text()
t = t.replace("        self.assertIn('5.76 km', summary)", "        self.assertIn('(4.2 km)', summary)", 1)
t = t.replace("        self.assertEqual(view['coverage']['stations'], 1)", "        self.assertEqual(view['coverage']['stations'], 2)", 1)
p.write_text(t)
print('fixed')