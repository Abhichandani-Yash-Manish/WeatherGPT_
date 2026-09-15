import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()

old_cmd = "node tests/test_charts.js                            #  2 of 60 component checks"
assert t.count(old_cmd) == 1
t = t.replace(old_cmd, "node tests/test_charts.js                            #  2 of 68 component checks", 1)
old_voice = "node tests/test_voice_ui.js                          #  3"
assert t.count(old_voice) == 1
t = t.replace(old_voice, "node tests/test_voice_ui.js                          #  3\nnode tests/test_briefcase_ui.js                     #  8", 1)

anchor = "- **Desktop web only.**"
bullet = ("- **A reading position, and a briefcase for what you keep.** Farmer, district officer and traveller each open"
          " the page on their own surfaces and questions, and every answer names the position it was read under and states that"
          " it changes no value, unit, window, warning level or source. Briefs the workspace composed can be kept, reopened,"
          " exported as Markdown and deleted on this machine; nothing is delivered, pushed or scheduled. See"
          " [docs/50](docs/50-personas-and-the-briefcase.md)." + chr(10))
assert t.count(anchor) == 1
t = t.replace(anchor, bullet + anchor, 1)

doc_anchor = "- [Critical full-solution review](docs/21-full-solution-critical-review.md)"
entry = ("- [Personas and the briefcase](docs/50-personas-and-the-briefcase.md) - three registered reading positions that change"
         " emphasis and never evidence, disclosed in every answer, and a local briefcase that keeps, reopens, exports and deletes"
         " composed briefs. WS7's scheduled-briefing half is explicitly still open." + chr(10))
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, entry + doc_anchor, 1)
r.write_text(t)

h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['personas_briefcase_batch'] = {
    'report': 'docs/50-personas-and-the-briefcase.md',
    'evidence_directory': 'research/implementation/personas-briefcase-20260915',
    'operational_ready': False,
    'scope': ('WS7 part 1: three registered reading positions (farmer, district officer, traveller) that select surfaces, '
              'offered questions and listed limits while changing no value, unit, window, warning level, source identifier or '
              'evidence class, disclosed in every answer; plus a local briefcase that keeps, lists, reopens, exports as Markdown '
              'and deletes briefs the server composed, each with its sources and content hash.'),
    'automated_tests': 742,
    'javascript_component_checks': 68,
    'measured': {
        'personas': ['farmer', 'district_officer', 'traveller'],
        'same_question_same_facts_with_and_without_a_persona': True,
        'unknown_persona': 'refused before planning, never treated as the neutral reader',
        'kept_briefs_in_one_run': 2,
        'export': {'header': 'Content-Disposition: attachment; filename="advisory-brief-cotton-squaring-ahmedabad-236e9faa.md"',
                   'characters': 3131},
        'browser_download': {'file': 'browser/exported-brief.md', 'bytes': 3164},
        'page_positions': {'farmer': ['advisories', 'forecast', 'climate'],
                           'district_officer': ['warnings', 'map', 'observations', 'changes'],
                           'traveller': ['forecast', 'aviation', 'marine', 'observations']},
    },
    'limitations': [
        'No usability study and no effect of a position on answer quality: the check pins that it changes no evidence.',
        'Nothing is delivered, pushed, scheduled or shared; the export is a file on the reader machine.',
        'One desktop viewport, one browser, one session: no screen-reader, mobile, keyboard-only or cross-browser acceptance.',
        'WS7 is not finished: the scheduled briefing artefact and its recorded run remain open.',
    ],
}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))

p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/50-personas-and-the-briefcase.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))

g = root / 'docs/31-full-solution-gap-register.md'
lines = g.read_text().splitlines()
entry31 = ("- **R22 is recorded in [docs/50](50-personas-and-the-briefcase.md).** The first half of WS7 landed: farmer, district"
           " officer and traveller are registered reading positions, checked by the server before any work is done, disclosed in"
           " every answer, and pinned as emphasis-only - the same question returns the same facts with and without one. A local"
           " briefcase keeps, reopens, exports and deletes briefs the server composed, and the page's own export wrote a real"
           " Markdown file through the browser download path. **R22 closes no gap-register item and does not finish WS7**: the"
           " scheduled-briefing artefact is still open, nothing is delivered, and no usability or quality effect of a position is"
           " measured. 742 Python tests and 68 component checks passed at that checkpoint.")
inserted = False
for index in range(len(lines) - 1, -1, -1):
    if lines[index].startswith('- **R21 is recorded'):
        lines.insert(index + 1, entry31)
        inserted = True
        break
g.write_text(chr(10).join(lines) + chr(10))
print('README', 'docs/50' in r.read_text(), '| registry batch', 'personas_briefcase_batch' in h.read_text(), '| R22', inserted)
