import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()

pairs = [('# 742 Python tests', '# 754 Python tests'),
         ('#  2 of 68 component checks', '#  2 of 70 component checks'),
         ('node tests/test_briefcase_ui.js                     #  8', 'node tests/test_briefcase_ui.js                     # 10')]
for old, new in pairs:
    assert t.count(old) == 1, (old, t.count(old))
    t = t.replace(old, new, 1)

anchor = '- **Desktop web only.**'
bullet = ('- **A briefing you can have waiting.** A runner reads the connected products for named places and writes a dated'
          ' briefing: the official district warning day per place, the CAP relay reported separately, the forecast window as'
          ' retrieved, what could not be read, and what changed since the previous run — measured against that run record. The'
          ' interval is a foreground loop inside the command, not a service: nothing is delivered or pushed. See'
          ' [docs/51](docs/51-scheduled-briefing.md).' + chr(10))
assert t.count(anchor) == 1
t = t.replace(anchor, bullet + anchor, 1)

doc_anchor = '- [Personas and the briefcase](docs/50-personas-and-the-briefcase.md)'
assert t.count(doc_anchor) == 1
entry = ('- [A briefing you write on a schedule](docs/51-scheduled-briefing.md) - a dated briefing over named places with the'
         ' change since the previous run measured against that run own record, a foreground interval that says what it is not, and'
         ' the WS7 exit check now met with its limits recorded.' + chr(10))
t = t.replace(doc_anchor, entry + doc_anchor, 1)
r.write_text(t)

h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['scheduled_briefing_batch'] = {
    'report': 'docs/51-scheduled-briefing.md',
    'evidence_directory': 'research/implementation/briefing-20260915',
    'operational_ready': False,
    'scope': ('WS7 part 2 and its exit check: a dated briefing over named places composed from the connected products (official'
              ' district warning day per place, CAP relay reported separately, forecast window as retrieved, what could not be read),'
              ' written as Markdown with a full record and a series index by scripts/briefing.py, with a foreground interval'
              ' (--every/--runs) and a change reading computed against the previous run record; the page reads the newest run in the'
              ' workspace series directory through /api/briefing/latest.'),
    'automated_tests': 754,
    'javascript_component_checks': 70,
    'measured': {
        'scheduled_series': {'runs': 2, 'interval_seconds': 20, 'places': ['Ahmedabad, Gujarat', 'Kochi, Kerala'],
                             'latencies_seconds': [3.393, 29.886], 'change_readings': ['no_previous_run', 'same'],
                             'directory': 'research/implementation/briefing-20260915/series' },
        'workspace_series': {'directory': 'data/runtime/briefings', 'runs': 1, 'latency_seconds': 1.301},
        'page': 'the Briefcase surface rendered the run instant, identity, places, day, interval, latency, paths, text and limits',
    },
    'limitations': [
        'A foreground interval, not a service: no daemon, no push, no delivery, no notification channel.',
        'Two runs on one afternoon on one machine is not a reliability measurement, and the cold 29.886 s read is one observation, not a percentile.',
        'No forecast skill, accuracy, impact or operational clearance is claimed for anything in a briefing.',
        'CAP relay geographic applicability to a place is still not computed.',
    ],
}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))

p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/51-scheduled-briefing.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))

g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
entry31 = ('- **R23 is recorded in [docs/51](51-scheduled-briefing.md).** WS7 is complete against its exit check: three reading'
           ' positions reachable from the page, a brief kept, reopened and exported, and a scheduled run recorded. The runner writes'
           ' a dated briefing over named places, and the change since the previous run is computed from that run record; the interval'
           ' is a foreground loop that says what it is not, and nothing is delivered or pushed. **R23 closes no gap-register item and'
           ' changes no PS-feature status**: WS8 and WS9 remain open, and the coverage matrix still lists the features that are not'
           ' covered. 754 Python tests and 70 component checks passed at that checkpoint.')
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R22 is recorded'):
        glines.insert(index + 1, entry31)
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/51' in r.read_text(), '| batch', 'scheduled_briefing_batch' in h.read_text(), '| R23', inserted)