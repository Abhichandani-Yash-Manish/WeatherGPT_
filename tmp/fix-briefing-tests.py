import pathlib
p = pathlib.Path('tests/test_briefing_run.py')
t = p.read_text()

old = "        self.assertNotIn('all-clear', text.lower().replace('not an all-clear', ''))"
assert t.count(old) == 1
new = ("        import re\n"
       "        for match in re.finditer('all-clear', text.lower()):\n"
       "            self.assertIn(text.lower()[max(0, match.start() - 10):match.start()], ('s not an ', ' not an ', ' is not an ', 'not an '),\n"
       "                          'an all-clear is only ever named as something this is not')")
t = t.replace(old, new, 1)

start = t.index("    def test_the_change_reading_compares_against_the_previous_record(self):")
end = t.index("    def test_a_part_read_in_only_one_run_is_not_comparable_not_a_change(self):")
block = '''    def test_the_change_reading_compares_against_the_previous_record(self):
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.cap_state', return_value=relay_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            first = compose(object(), [PLACE], now=NOW)
            same = compose(object(), [PLACE], now=NOW, previous=first)
            quiet = json.loads(json.dumps(first))
            quiet['places'][0]['official_day'] = {'quiet': True, 'colour': 'green', 'status_line': 'No warning in this product'}
            changed = compose(object(), [PLACE], now=NOW, previous=quiet)
        self.assertEqual(same['change_since_previous']['reading'], 'same')
        self.assertEqual(same['change_since_previous']['day_changes'][0]['summary'],
                         first['places'][0]['official_day']['status_line'])
        self.assertEqual(changed['change_since_previous']['reading'], 'changed')
        self.assertEqual(changed['change_since_previous']['day_changes'][0]['from']['state'], 'quiet')
        self.assertEqual(changed['change_since_previous']['day_changes'][0]['to']['state'], 'yellow')
        self.assertEqual(changed['change_since_previous']['previous_briefing_id'], first['briefing_id'])

'''
t = t[:start] + block + t[end:]
p.write_text(t)
print('patched')
