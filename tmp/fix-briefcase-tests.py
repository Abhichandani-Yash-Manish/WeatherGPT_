import pathlib, re
t = pathlib.Path('tests/test_personas_briefcase.py')
tt = t.read_text()

old_start = tt.index("def markdown_payload():")
old_end = tt.index("class PersonaTests")
new_block = '''def day_row(number):
    return {'day': number, 'label': '1%d Sep 2026' % number, 'date_local': '2026-09-1%d' % number,
            'colour': 'yellow', 'colour_code': 3, 'hazards': ['Thunderstorm/lightning/squall'], 'quiet': False,
            'source_text': 'Thunderstorm with lightning at isolated places.',
            'starts_utc': '2026-09-1%dT18:30:00+00:00' % number,
            'ends_utc': '2026-09-1%dT18:30:00+00:00' % (number + 1)}


def warnings_view():
    return {'schema_version': 'product-view-v1', 'view': 'warnings.place', 'status': 'ok',
            'generated_at_utc': '2026-09-15T04:11:36+00:00',
            'data': {'district': 'PATNA', 'state': 'BIHAR', 'issued_at_utc': '2026-09-15T00:00:00+00:00',
                     'day_boundary_basis': 'Day n is the nth IST calendar day counted from the bulletin date.',
                     'temporal_applicability': 'derived', 'source_locator': '$.features[605]',
                     'days': [day_row(1), day_row(2)]},
            'sources': [{'source_id': 'S63', 'product': 'IMD district warning product',
                         'layer': 'imd:district_warnings_india', 'retrieved_at_utc': '2026-09-15T04:11:36+00:00'}],
            'limitations': ['Day windows are derived from the bulletin date.'],
            'not_established': ['This is district-level warning guidance, not a flood warning and not an all-clear.']}


def markdown_payload():
    """A brief the compose function itself built, so the export renders a real payload."""
    return compose(warnings_view(),
                   {'data': {'messages': 9, 'eligible_by_lifecycle': 0, 'latest_sent': '2026-09-09T12:54:34+05:30'},
                    'sources': [{'source_id': 'S06'}]}, 1)


'''
tt = tt[:old_start] + new_block + tt[old_end:]

tt = tt.replace("from weathergpt_data.briefcase import",
                "from weathergpt_data.alert_brief import compose\nfrom weathergpt_data.briefcase import", 1)

old_export = '''        self.assertIn('Content hash:** sha256 ' + 'c' * 16, text)
        self.assertIn('# Alert brief', text)'''
assert tt.count(old_export) == 1
tt = tt.replace(old_export, '''        self.assertIn('Content hash:** sha256 ' + payload['brief_id'][:16], text)
        self.assertIn('# Alert brief', text)
        self.assertIn('Thunderstorm with lightning at isolated places.', text)''', 1)
tt = tt.replace("        self.assertTrue(text.startswith('<!--'))\n        self.assertIn('Nothing was delivered or published', text)",
                "        payload = markdown_payload()\n        entry = self.store.save('alert_brief', payload, now=NOW)\n        text = markdown(entry)\n        self.assertTrue(text.startswith('<!--'))\n        self.assertIn('Nothing was delivered or published', text)", 1)
old_lines = """        entry = self.store.save('alert_brief', markdown_payload(), now=NOW)
        text = markdown(entry)
        self.assertTrue(text.startswith('<!--'))"""
if tt.count(old_lines):
    tt = tt.replace(old_lines, "", 1)
t.write_text(tt)
print('patched')
