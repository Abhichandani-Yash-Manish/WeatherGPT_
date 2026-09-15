import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
doc_anchor = '- [Two gaps the sealed holdout exposed](docs/55-place-typos-and-coasts.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [A second sealed holdout](docs/56-second-holdout.md) - 6 of 11 declared tasks after the repairs, but every miss now an absence the product states rather than a wrong product or a mis-read place, plus the case-authoring lesson recorded from two vocabulary mistakes." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['second_holdout_batch'] = {
    'report': 'docs/56-second-holdout.md',
    'evidence_directory': 'research/reviews/acceptance-benchmark-20260915q',
    'operational_ready': False,
    'scope': "A second sealed holdout authored after the typo and coast repairs and run once, plus the four diagnoses of its misses (a state agromet edition not held, district temperature history not held, TAF not served for the station, one partial advisory, and an out-of-scope tsunami question answered as an explanation with no fabricated forecast), and the authoring lesson recorded from two vocabulary mistakes.",
    'automated_tests': 782,
    'javascript_component_checks': 70,
    'measured': {'cases': 10, 'turns': 11, 'declared_tasks': 11, 'completed': 6, 'incomplete': 4, 'missing': 1,
                 'completion_rate': 0.545, 'prohibited_claim_hits': 0, 'critical_failures': 0,
                 'statuses_outside_the_declared_vocabulary': 1,
                 'miss_kinds': {'absence_reported_by_the_product': 3, 'partial': 1, 'shape_mismatch_on_an_out_of_scope_question': 1,
                                'wrong_product_or_misread_place': 0},
                 'first_holdout_comparison': {'completed': '8 of 13', 'completion_rate': 0.615}},
    'limitations': ['Two ten-case sets are a probe of shapes, not a sample of users.',
                    'Completion is not correctness: no answer was checked against its source by a human this round.',
                    'A prohibited-claim hit is a regex match, not a semantic review.',
                    'Twice a case vocabulary was narrower than the product honest outcome space; that is recorded as an authoring lesson.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/56-second-holdout.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R27 is recorded'):
        glines.insert(index + 1, "- **R28 is recorded in [docs/56](56-second-holdout.md).** A second sealed set was authored after the repairs and run once: 6 of 11 declared tasks (0.545), 0 prohibited-claim hits, 0 critical failures. Its misses are three absences the product reports with reasons (a Maharashtra agromet edition not held, district temperature history not held, TAF not served), one partial advisory, and one out-of-scope tsunami question answered as an explanation with no fabricated forecast. Compared with the first sealed set, no miss came from a wrong product or a mis-read place. **R28 closes no gap-register item**: two ten-case sets are a probe of shapes, not a sample of users, and completion is not correctness.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/56' in r.read_text(), '| batch', 'second_holdout_batch' in h.read_text(), '| R28', inserted)