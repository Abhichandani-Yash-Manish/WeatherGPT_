import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
g54 = root / 'docs/54-holdout-generalisation.md'
t54 = g54.read_text()
anchor = "## The rule that follows"
assert t54.count(anchor) == 1, t54.count(anchor)
g54.write_text(t54.replace(anchor, "\n## What followed, and what it costs this set\n\nDocs/55 repairs the two root causes this record named. Reading the misses to write this record, and then\nchanging the engine because of them, means `fresh_holdout` is **development data from here on**: its 0.615 is\nthe generalisation number of the engine *before* those repairs, and it must not be quoted as the number for\nthe current engine. The next generalisation number needs a holdout authored after the repairs.\n" + anchor, 1))
r = root / 'README.md'
t = r.read_text()
old_tests = '# 774 Python tests'
assert t.count(old_tests) == 1
t = t.replace(old_tests, '# 782 Python tests', 1)
doc_anchor = '- [A sealed holdout, run once](docs/54-holdout-generalisation.md)'
assert t.count(doc_anchor) == 1
entry = '- [Two gaps the sealed holdout exposed](docs/55-place-typos-and-coasts.md) - a misspelt state that emptied a candidate list, and a coast searched for as a settlement: both repaired, pinned by tests over the real index, and recorded as having turned the sealed set into development data.'
t = t.replace(doc_anchor, entry + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['coastal_and_typo_batch'] = {
    'report': 'docs/55-place-typos-and-coasts.md',
    'evidence_directory': 'research/implementation/coastal-and-typo-repairs-20260915',
    'operational_ready': False,
    'scope': "The two root causes the sealed holdout exposed, repaired: a misspelt state name no longer empties a candidate list the place itself matched (bounded, disclosed, never swapped for a different state), and a coast or sea is read as a region rather than searched for as a settlement (marked in the planner, skipped by the resolver, and answered by the warning tool with a request for a district or a port). 'off' is a place preposition and an article between the preposition and the name is read. Eight tests over the real gazetteer and rule planner, plus four live journeys.",
    'automated_tests': 782,
    'javascript_component_checks': 70,
    'measured': {'typo_state': {'question': 'Will it rain in Ahmedbad, Gujrat tomorrow?', 'status': 'needs_selection',
                                'choices': 1, 'reading': 'Ahmedabad, Ahmadabad, State of Gujarat',
                                'before': 'refused with could not find a settlement' },
                 'coast': {'question': 'Are there warnings for the Kerala coast?', 'status': 'needs_clarification',
                           'choices': 0, 'before': '20 villages called Kerla in Rajasthan' },
                 'compound': {'tasks': 2, 'statuses': ['needs_clarification', 'needs_clarification']},
                 'port': {'question': 'What are the waves off Kochi for tomorrow?', 'status': 'needs_selection', 'choices': 5}},
    'limitations': ['A single approximate match still requires confirmation by design.',
                    'A coast question still asks for a district or a port: the sea-area bulletins remain unconnected.',
                    'fresh_holdout is now development data, so its 0.615 describes the engine before these repairs.',
                    'No usability, native-language, mobile or cross-browser acceptance was measured.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/55-place-typos-and-coasts.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R26 is recorded'):
        glines.insert(index + 1, "- **R27 is recorded in [docs/55](55-place-typos-and-coasts.md).** Both root causes behind the sealed holdout's misses are repaired: a misspelt state name resolves against the indexed names with the reading disclosed and is never swapped for a different state, and a coast or sea is a region that the resolver leaves to the tools, so the warning tool asks for a district or a port instead of attaching guidance to a village named like the region. 'off Kochi' and 'in the Ahmedabad district' are read. Four live journeys are recorded, and the same record states that `fresh_holdout` is now development data: its 0.615 describes the engine before these repairs. **R27 closes no gap-register item**; no usability, native-language or mobile acceptance was measured.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/55' in r.read_text(), '| batch', 'coastal_and_typo_batch' in h.read_text(), '| R27', inserted, '| 54 updated', 'development data from here on' in g54.read_text())