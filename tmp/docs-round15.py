import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
old = '# 798 Python tests'
assert t.count(old) == 1
t = t.replace(old, '# 809 Python tests', 1)
doc_anchor = '- [The right-now reading](docs/58-right-now-reading.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [Paraphrase robustness](docs/59-paraphrase-robustness.md) - 38 deterministic variants over eleven declared shapes, the eight repairs that took the held rate from 25/34 to 38/38, and the honest note that this is a development set, not generalisation." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['paraphrase_robustness_batch'] = {
    'report': 'docs/59-paraphrase-robustness.md',
    'evidence_directory': 'research/implementation/paraphrase-robustness-20260915',
    'operational_ready': False,
    'scope': "Paraphrase robustness (finding A01): a deterministic measurement of eleven declared shapes across 38 wording variants, and the eight repairs it found - agromet bulletins in the document vocabulary, a station code read as a station request with an acronym guard, Hinglish past markers in the history vocabulary, tide as an unconnected domain, an order-independent crosscheck shape, Indic-script questions planned in their own language, a native-script state disclosed as unused rather than emptying the candidate list, and 'sea_area' accepted by the plan schema and validator.",
    'automated_tests': 809,
    'javascript_component_checks': 70,
    'measured': {'variants_before': 34, 'held_before': 25, 'rate_before': 0.735,
                 'variants_after': 38, 'held_after': 38, 'rate_after': 1.0,
                 'shapes': 11,
                 'live_journeys': {'devanagari_rain': 'answered', 'gujarati_rain': 'answered',
                                   'station_code': 'answered', 'agromet_bulletin': 'answered',
                                   'tide': 'unavailable (the honest gap)', 'crosscheck_hinglish': 'answered'},
                 'all_live_journeys_planned_by': 'deterministic_rules/rule-planner-v1'},
    'limitations': ['A development set written and tuned by the same hand: not a generalisation measurement.',
                    'A plan is not an answer, and no answer was checked against its source by a human.',
                    'No native speaker has reviewed the Indic-script output.',
                    'Variants are generated deterministically, not sampled from users.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/59-paraphrase-robustness.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R30 is recorded'):
        glines.insert(index + 1, "- **R31 is recorded in [docs/59](59-paraphrase-robustness.md).** Paraphrase robustness (A01) is now measured rather than asserted: `scripts/measure_paraphrases.py` runs 38 deterministic variants over eleven declared shapes, and the eight repairs it found took the held rate from 25/34 to 38/38. The repairs include agromet bulletins in the document vocabulary, a station code read as a station request (with an acronym guard), Hinglish past-tense markers for history, tide as an unconnected domain like its siblings, an order-independent crosscheck shape, Indic-script questions planned in their own language, a native-script state disclosed as unused instead of emptying the candidate list, and 'sea_area' accepted by the schema and validator. Six repaired wordings are recorded live, all planned by the rules floor. **R31 closes no gap-register item**: the set is a development set by construction, a plan is not an answer, and no native speaker has reviewed the Indic-script output. 809 Python tests passed at that checkpoint.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/59' in r.read_text(), '| batch', 'paraphrase_robustness_batch' in h.read_text(), '| R31', inserted)