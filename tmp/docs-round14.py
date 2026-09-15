import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
old = '# 785 Python tests'
assert t.count(old) == 1
t = t.replace(old, '# 798 Python tests', 1)
doc_anchor = '- [Comparing two forecast sources](docs/57-model-comparison.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [The right-now reading](docs/58-right-now-reading.md) - live station observations in the conversation, and one reading composing the observed, the published day and the model hours next, with radar, sub-hourly refresh and push named as not connected." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['right_now_batch'] = {
    'report': 'docs/58-right-now-reading.md',
    'evidence_directory': 'research/implementation/right-now-20260915',
    'operational_ready': False,
    'scope': "PS feature 1's right-now gap: live station observations (METAR and AWS) are connected to the conversation through the same governed adapter as the page, and a right-now reading composes three products - what a station observed with its own instant, age and distance, what the official district product publishes for today with its bulletin identity, and the model hours next quoted as returned - with radar and satellite imagery, sub-hourly refresh and push stated as not connected. A /api/now read model and a Right now panel on the Today surface use the same composer.",
    'automated_tests': 798,
    'javascript_component_checks': 70,
    'measured': {'now_view': {'status': 'ok', 'stations': 2, 'model_hours': 6, 'published_day': 1, 'sources': ['S63', 'S62']},
                 'chat_right_now': {'question': "What's it like right now in Ahmedabad?", 'status': 'answered',
                                    'facts': 5, 'provider': 'deterministic_rules/rule-planner-v1'},
                 'chat_station_code': {'question': 'What is being observed at VOBL right now?', 'status': 'answered',
                                       'facts': 2, 'planned_as': 'aviation metar'},
                 'station_ages_minutes': {'aws': 380, 'metar': 50},
                 'not_connected': ['radar and satellite imagery', 'sub-hourly refresh between source hours',
                                   'any push or notification']},
    'limitations': ['No radar or satellite imagery, no sub-hourly refresh and no push.',
                    'No accuracy claim: the reading reports what the connected products returned at that instant.',
                    'One point and one instant were measured; a station layer can be stale between source hours.',
                    'No mobile, screen-reader or cross-browser acceptance of the panel.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/58-right-now-reading.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R29 is recorded'):
        glines.insert(index + 1, "- **R30 is recorded in [docs/58](58-right-now-reading.md).** PS feature 1's right-now gap is closed as far as the connected sources allow: live METAR and AWS observations now answer in the conversation (they previously said 'not connected to this conversation path yet'), and a single reading composes what a station reported (with its own instant, age and distance), what the official district product publishes for today, and the model hours next. A four-letter station code in a right-now question is read as an airport report rather than a settlement search. `/api/now` and the Today panel use the same composer; radar and satellite imagery, sub-hourly refresh and push are stated as not connected. **R30 moves PS feature 1 towards covered but does not close it**: the imagery and refresh parts remain unconnected, no accuracy or skill is claimed, and one point and one instant were measured.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/58' in r.read_text(), '| batch', 'right_now_batch' in h.read_text(), '| R30', inserted)