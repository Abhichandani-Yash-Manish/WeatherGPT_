"""Write the intake-repair evidence: what was measured, and what was decided from it."""
import json, pathlib, sqlite3

root = pathlib.Path('.')
out = root / 'research/reviews/intake-repair-20260915'
out.mkdir(parents=True, exist_ok=True)
manifest = json.loads((root / 'data/processed/bulletins/2026-09-15/manifest.json').read_text())
runs = manifest.get('runs') or []
families = []
for run in runs:
    report = run.get('report') or run
    families.append({'family': report.get('family') or run.get('family'),
                     'status': report.get('status'),
                     'candidates': len(report.get('candidates') or []),
                     'accepted': len(report.get('accepted') or []),
                     'rejected': len(report.get('rejected') or []),
                     'rejection_reasons': sorted({(item.get('stage') or '?') + ': ' + (item.get('error') or '')[:90]
                                                  for item in (report.get('rejected') or [])})})

db = sqlite3.connect('file:data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite?mode=ro', uri=True)
multi = db.execute("""SELECT family, coalesce(region,'(national)') FROM passages
                      GROUP BY family, 2 HAVING count(DISTINCT json_extract(payload,'$.issue_date')) > 1""").fetchall()
editions = db.execute('SELECT count(DISTINCT json_extract(payload,\'$.issue_date\')) FROM passages').fetchone()[0]
documents = db.execute('SELECT count(*) FROM documents').fetchone()[0]
passages = db.execute('SELECT count(*) FROM passages').fetchone()[0]

record = {
    'schema_version': 'intake-repair-evidence-v1',
    'recorded_at_utc': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).replace(microsecond=0).isoformat(),
    'run': {'day': manifest.get('day'), 'families': families,
            'manifest': 'data/processed/bulletins/2026-09-15/manifest.json'},
    'corpus_after_run': {'documents': documents, 'passages': passages, 'distinct_printed_issue_dates': editions},
    'products_and_regions_with_more_than_one_edition': multi,
    'live_two_edition_comparison_possible': bool(multi),
    'defects_found_and_repaired': [
        {'id': 'intake-aborts-on-an-unverifiable-publication',
         'measured': 'A four-family run exited 1 with SourceError: Immutable document publication already differs for document 732cdfa9c255f90f.',
         'repair': 'The intake records the target as rejected with stage publish and held true, and continues the run; the publication is still never rewritten.',
         'evidence': 'tests/test_document_ingest.py::PublicationIdentityTests::test_the_intake_holds_a_target_it_cannot_verify_and_keeps_going'},
        {'id': 'clock-and-annotation-fields-counted-as-identity',
         'measured': 'The stored payload for sha 732cdfa9 has age_days 0, currency printed_issue_matches_retrieval_date and no marker_basis; a fresh extraction of the same bytes has age_days 1, printed_issue_differs_from_retrieval_date and marker_basis no_marker_required.',
         'repair': 'Publication identity is the document identity fields plus every passage printed position and text; clock-derived and later-added annotations are not identity, so a re-fetch is idempotent and a changed passage is still refused.',
         'evidence': 'tests/test_document_ingest.py::PublicationIdentityTests::test_rerecording_the_same_document_on_a_later_clock_is_idempotent'},
        {'id': 'character-annotation-changed-the-passage-id',
         'measured': 'Six stored passages and six freshly extracted passages of sha 732cdfa9 had disjoint ids; the only differing field on the first passage was text_quality (text_layer_clean stored, control_characters_replaced fresh), which was part of the id input.',
         'repair': 'text_quality is no longer part of a passage id. Stored ids are unchanged (ids are recorded, not recomputed); publications made after this batch derive ids from content and position only.',
         'evidence': 'tests/test_document_ingest.py::PublicationIdentityTests::test_the_character_annotation_is_not_part_of_a_passage_identity'},
    ],
    'limits': [
        'One intake run on one day against four families; other families were not re-run.',
        'No product and region holds two editions after this run, so the live cross-edition comparison still cannot be exercised on real text.',
        'Issue dates and currency are as printed; this run changed no source term and no publisher relationship.',
    ],
}
(out / 'evidence.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
print('families:', [(f['family'], f['status'], f['accepted'], f['rejected']) for f in families])
print('multi-edition products:', multi, '| documents', documents, '| passages', passages, '| issue dates', editions)
