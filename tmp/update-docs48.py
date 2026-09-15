import json, pathlib, datetime

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

h_path = pathlib.Path('data/registry/hardening-progress.json')
h = json.loads(h_path.read_text())
h['intake_publication_identity_batch'] = {
    'report': 'docs/48-intake-publication-identity.md',
    'evidence_directory': 'research/reviews/intake-repair-20260915',
    'run_manifest': 'data/processed/bulletins/2026-09-15/manifest.json',
    'operational_ready': False,
    'scope': ('Document-intake robustness and publication identity: an unverifiable publication is held per '
              'target instead of aborting the sweep, publication identity is content and address rather than '
              'clock-derived annotations, and text_quality leaves the passage id. No source term, issue date, '
              'currency or retrieval instant changed.'),
    'automated_tests': 659,
    'measured': {
        'families_re_run': ['national_bulletin', 'flash_flood_national', 'sea_area_bulletin', 'coastal_bulletin'],
        'run_exit_code': 0,
        'documents_before': 582, 'documents_after': 584,
        'passages_before': 6700, 'passages_after': 6739,
        'products_and_regions_with_more_than_one_edition': 0,
        'live_two_edition_comparison_possible': False,
        'held_targets': {'sea_area_bulletin': 1, 'coastal_bulletin': 2},
        'disjoint_passage_ids_for_one_document': {'sha256_prefix': '732cdfa9c255f90f', 'stored': 6, 'extracted': 6, 'overlap': 0,
                                                  'only_differing_field': 'text_quality'},
    },
    'repairs_recorded': [
        'An unverifiable publication aborted the four-family intake with SourceError; it is now recorded as a held target and the run continues.',
        'Publication identity compared clock-derived fields (age_days, currency, printed_issue_is_retrieval_date) and later-added annotations (marker_basis), so a re-fetch of unchanged bytes looked like a different document.',
        'text_quality was part of the passage id input, so the same bytes could extract to a different passage identity.',
        'The integrity refusal now names the document, the region and the reason.',
    ],
    'limitations': [
        'No product and region holds two editions, so the cross-edition comparison is still exercised only by component checks.',
        'One intake run on one day against four families; the other families were not re-run.',
        'Stored ids and stored annotations are unchanged; only publications made after this batch derive ids without text_quality.',
    ],
}
h['updated_at_utc'] = now
h_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

p_path = pathlib.Path('data/registry/product-progress.json')
p = json.loads(p_path.read_text())
p['as_of_utc'] = now
p['latest_batch'] = 'docs/48-intake-publication-identity.md'
p_path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

readme = pathlib.Path('README.md')
text = readme.read_text()
text = text.replace('# 654 Python tests', '# 659 Python tests')
text = text.replace('- [Answer transparency and cross-edition coverage](docs/47-answer-transparency-and-edition-coverage.md) — 654 tests,',
                    '- [The intake holds what it cannot verify](docs/48-intake-publication-identity.md) — a re-fetch is not a new edition, the sweep no longer aborts on one held target, and no product holds two editions yet.\n- [Answer transparency and cross-edition coverage](docs/47-answer-transparency-and-edition-coverage.md) — 654 tests,')
text = text.replace('- [Answer transparency and cross-edition coverage](docs/47-answer-transparency-and-edition-coverage.md) — engine stages and queue position reported as facts',
                    '- [The intake holds what it cannot verify](docs/48-intake-publication-identity.md) — publication identity is content and address, a held target no longer aborts the sweep, and the live corpus still holds one edition per product.\n- [Answer transparency and cross-edition coverage](docs/47-answer-transparency-and-edition-coverage.md) — engine stages and queue position reported as facts', 1)
readme.write_text(text, encoding='utf-8')

gap = pathlib.Path('docs/31-full-solution-gap-register.md')
lines = gap.read_text().splitlines()
entry = ("- **R16 is recorded in [docs/48](48-intake-publication-identity.md).** Re-running the document intake to look for a "
         "second edition found that one unverifiable publication aborted the whole sweep, that publication identity was "
         "compared through clock-derived and later-added annotations, and that a character annotation was part of the passage "
         "id. All three are repaired: the intake holds the target and continues, identity is content and address, and the same "
         "bytes extract to the same passage id. **R16 closes no gap-register item and promotes no finding**; the publisher "
         "still serves one edition per product and region, so the live cross-edition comparison remains unexercised and the "
         "corpus grew only from 582 to 584 documents. 659 tests passed at that checkpoint.")
for index in range(len(lines) - 1, -1, -1):
    if lines[index].startswith('- **R15 is recorded'):
        lines.insert(index + 1, entry)
        break
gap.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('batches:', len(h), '| latest_batch:', p['latest_batch'])
print('README count updated:', '659 Python tests' in readme.read_text())
print('R16 present:', 'R16 is recorded' in gap.read_text())
