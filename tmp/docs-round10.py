import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
anchor = '- **Desktop web only.**'
assert t.count(anchor) == 1
t = t.replace(anchor, "- **A sealed holdout, run once.** The declared benchmark's numbers describe the cases they were tuned on: its earlier holdout had been read during development. A fresh set of ten unseen cases was authored, sealed in the registry with a rule against tuning on it, and run once — 8 of 13 declared tasks, 0 prohibited claims, 0 crashes. The difference between that and 17/17 is the honest estimate of shape coverage. See [docs/54](docs/54-holdout-generalisation.md)." + chr(10) + anchor, 1)
doc_anchor = '- [Operations: one command, a preflight and measured latency](docs/53-operations.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [A sealed holdout, run once](docs/54-holdout-generalisation.md) - ten unseen cases, 8 of 13 declared tasks, 0 prohibited claims, the five misses with their causes, and why the tuned sets overstate coverage." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['sealed_holdout_batch'] = {
    'report': 'docs/54-holdout-generalisation.md',
    'evidence_directory': 'research/reviews/acceptance-benchmark-20260915p',
    'operational_ready': False,
    'scope': 'A sealed holdout of ten unseen cases authored after the engine rounds and run once, with no engine change afterwards.',
    'automated_tests': 774,
    'javascript_component_checks': 70,
    'measured': {'cases': 10, 'turns': 12, 'declared_tasks': 13, 'completed': 8, 'incomplete': 3, 'missing': 2,
                 'completion_rate': 0.615, 'prohibited_claim_hits': 0, 'critical_failures': 0,
                 'statuses_outside_the_declared_vocabulary': 2,
                 'tuned_comparison': {'development': '17/17', 'holdout': '4/4'}},
    'limitations': ['Ten cases written in one sitting are a probe of shapes, not a sample of users.',
                    'Two root causes account for three of the five misses; the cases are not independent samples.',
                    'A prohibited-claim hit is a regex match, not a semantic review.',
                    'The misses were read to write the record: any round that fixes them makes this set development data.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/54-holdout-generalisation.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R25 is recorded'):
        glines.insert(index + 1, "- **R26 is recorded in [docs/54](54-holdout-generalisation.md).** A fresh holdout of ten unseen cases was authored, sealed in the registry with a rule against tuning on it, and run once: 8 of 13 declared tasks completed (0.615), 0 prohibited-claim hits, 0 critical failures. The five misses reduce to two root causes (two misspellings in one place name were not resolved; a coast is not a settlement and the compound question stopped at a place selection) plus one whole-edition read that returned partial and one case whose declared status vocabulary was authored too narrowly. **R26 closes no gap-register item and lowers no existing claim**: it records what generalisation looks like today, states that the misses were read to write the record, and states that any round fixing them makes this set development data again.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/54' in r.read_text(), '| batch', 'sealed_holdout_batch' in h.read_text(), '| R26', inserted)