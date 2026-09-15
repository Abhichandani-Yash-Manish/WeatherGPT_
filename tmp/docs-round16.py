import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
old = '# 813 Python tests'
assert t.count(old) == 1
t = t.replace(old, '# 826 Python tests', 1)
doc_anchor = '- [Paraphrase robustness](docs/59-paraphrase-robustness.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [State agromet coverage](docs/60-state-agromet-coverage.md) - a 22-centre sweep that took state coverage from one edition to five, the sixteen centres that answer 404, and the marker defect that would have accepted any PDF as a bulletin." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['state_agromet_coverage_batch'] = {
    'report': 'docs/60-state-agromet-coverage.md',
    'registry': 'data/registry/state-agromet-targets.json',
    'operational_ready': False,
    'scope': "State agromet corpus coverage: a 22-centre target registry built from the publisher's centre path pattern, a per-state ingest path with the district outcome vocabulary, a sweep that records every target's outcome per target, and the state name each document prints checked against the claimed state. Five states are now indexed (Gujarat, Rajasthan, Uttar Pradesh, Chhattisgarh, Karnataka) against one before; sixteen centres answer 404 at that path and one run hit the provider cooldown. The round also found and fixed a family-marker defect: _squash() collapsed Devanagari to the empty string, and on empty pattern matches every document, so an Indian-language marker would have accepted any PDF.",
    'automated_tests': 826,
    'javascript_component_checks': 70,
    'measured': {'targets_listed': 22, 'ingested': 5, 'not_served_404': 16, 'provider_cooldown': 1,
                 'states': {'Gujarat': {'issue_date': '2026-09-12', 'language': 'en', 'passages': 257},
                            'Rajasthan': {'issue_date': '2026-08-07', 'language': 'hi', 'passages': 42},
                            'Uttar Pradesh': {'issue_date': '2026-09-11', 'language': 'hi', 'passages': 173},
                            'Chhattisgarh': {'issue_date': '2026-08-07', 'language': 'hi', 'passages': 63},
                            'Karnataka': {'issue_date': None, 'issue_date_basis': 'printed_issue_not_stated',
                                          'language': 'hi', 'passages': 355}},
                 'corpus_before': {'state_editions': 1, 'passages': 257},
                 'corpus_after': {'state_editions': 5, 'passages': 890},
                 'defects_found': {'squash_empty_pattern': 'fixed; a Devanagari title squashed to the empty string and would have matched every document',
                                   'language_from_character_count': 'fixed; the edition language follows the script of the title that matched',
                                   'markers_all_required': 'fixed; the family now accepts any of its sampled titles'}},
    'limitations': ['Nationwide state coverage is not established: the centres that publish elsewhere are unknown.',
                    'A 404 at a guessed address is not evidence that a state has no bulletin.',
                    'A listed target is not a promise of an issue, and a reachable address is not a validated product.',
                    'No agronomist or native speaker has reviewed the Devanagari editions.',
                    'Karnataka states no printed issue date, so its currency is recorded as not stated.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/60-state-agromet-coverage.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R31 is recorded'):
        glines.insert(index + 1, "- **R32 is recorded in [docs/60](60-state-agromet-coverage.md).** State agromet coverage went from one edition (Gujarat) to five: a 22-centre target registry was swept with the district outcome vocabulary, and per-state ingest records each target's own outcome (five ingested with their printed issue dates, sixteen HTTP 404 at the centre path, one provider cooldown). The round found a serious family-marker defect: `_squash()` kept only `[a-z0-9]`, so a Devanagari title squashed to the empty string and would have matched every document; it is fixed to keep letters and digits in any script, and the edition language now follows the script of the title that matched (two relabels recorded with their evidence). **R32 closes the holdout's coverage absence for five states and closes no gap-register item**: nationwide state coverage is not established, a 404 at a guessed address is not evidence that a state has no bulletin, and no native speaker has reviewed the Devanagari editions. 826 Python tests passed at that checkpoint.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/60' in r.read_text(), '| batch', 'state_agromet_coverage_batch' in h.read_text(), '| R32', inserted)