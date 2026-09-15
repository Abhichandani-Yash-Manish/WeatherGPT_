import pathlib
p = pathlib.Path('tests/test_briefing_run.py')
t = p.read_text()
old = """            briefing = compose(object(), [PLACE], now=NOW)
        text = markdown(briefing)
        self.assertIn('quiet in the product for 1', summary_line(briefing))"""
assert t.count(old) == 1
new = """            briefing = compose(object(), [PLACE], day=2, now=NOW)
        text = markdown(briefing)
        self.assertIn('official day read for 1', summary_line(briefing))
        self.assertIn('quiet in the product for 1', summary_line(briefing))
        self.assertEqual(briefing['places'][0]['official_day']['colour'], 'green')"""
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')
