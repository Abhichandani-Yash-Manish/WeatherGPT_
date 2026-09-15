import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
old = '# 782 Python tests'
assert t.count(old) == 1
t = t.replace(old, '# 785 Python tests', 1)
doc_anchor = '- [A second sealed holdout](docs/56-second-holdout.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [Comparing two forecast sources](docs/57-model-comparison.md) - the crosscheck operation now runs on the rules-first floor, with both sources, their difference, the shared-lineage caveat, and no skill, average or confidence score." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['model_comparison_batch'] = {
    'report': 'docs/57-model-comparison.md',
    'evidence_directory': 'research/implementation/model-comparison-20260915',
    'operational_ready': False,
    'scope': "PS feature 3's missing piece, taken as far as the connected sources allow: the rules planner now recognises a request to compare forecast sources or check another model, so the crosscheck operation runs on the rules-first floor instead of only through a model. A crosscheck with no measure named is still refused by the rules. Three checks added.",
    'automated_tests': 785,
    'javascript_component_checks': 70,
    'measured': {'crosscheck_turn': {'question': 'Compare the models for rainfall in Ahmedabad tomorrow morning.',
                                     'status': 'answered', 'provider': 'deterministic_rules/rule-planner-v1',
                                     'facts': 4, 'calculations': 2, 'comparison_present': True},
                 'plain_turn': {'question': 'Will it rain in Ahmedabad tomorrow morning?', 'status': 'answered',
                                'facts': 1, 'calculations': 0},
                 'caveat': 'the best-match product may include GFS upstream, so agreement is not independent confirmation'},
    'limitations': ['No skill, calibration or accuracy claim, and no statement that either source is better.',
                    'No ensemble spread: the connected products are deterministic runs.',
                    'WRF remains without an accessible source.',
                    'One place and one window measured on one morning.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/57-model-comparison.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R28 is recorded'):
        glines.insert(index + 1, "- **R29 is recorded in [docs/57](57-model-comparison.md).** PS feature 3's missing piece - a model-vs-model comparison exposed in the answer - now runs on the rules-first floor: the rules planner recognises a request to compare forecast sources or check another model, produces `forecast/crosscheck`, and the answer carries both sources, their difference and the caveat that the best-match product may share GFS upstream. A crosscheck that names no measure is still left to a model rather than guessed. Measured live on the rules path (four facts, two calculations, comparison present) and pinned by three checks. **R29 moves no PS feature to covered**: no skill or calibration is claimed, ensemble spread is not computed, WRF remains without an accessible source, and one place and one window were measured.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/57' in r.read_text(), '| batch', 'model_comparison_batch' in h.read_text(), '| R29', inserted)