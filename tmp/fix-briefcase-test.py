import pathlib
p = pathlib.Path('tests/test_briefcase_ui.js')
t = p.read_text()
old_start = t.index('  // 6. The save action sends a request to compose, never a payload to store (static check).')
old_end = t.index('  // 7. The reading position is disclosed in the answer accounting and never as a finding.')
new = ("  // 6. The save action sends a request to compose, never a payload to store (static check).\n" +
       "  assert.ok(PANELS.indexOf(\"saveToBriefcase(WGref, 'alert_brief', { lat: where.latitude, lon: where.longitude, day: chosenDay }, body)\") >= 0,\n" +
       "            'saving asks the server to compose the alert brief for a point and a day');\n" +
       "  assert.ok(PANELS.indexOf(\"saveToBriefcase(WGref, 'advisory_brief', request, body)\") >= 0,\n" +
       "            'saving an advisory brief sends the request that composed it');\n" +
       "  assert.equal(PANELS.split(\"'/api/briefs/save'\").length - 1, 1, 'the page asks the server to compose a brief in exactly one place');\n" +
       "  assert.ok(PANELS.indexOf('Object.assign({ kind: kind }, params || {})') >= 0,\n" +
       "            'the request carries a kind and the composition parameters, never a brief body');\n\n")
t = t[:old_start] + new + t[old_end:]
p.write_text(t)
print('patched test')