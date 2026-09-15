import json, pathlib, datetime

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

h_path = pathlib.Path('data/registry/hardening-progress.json')
h = json.loads(h_path.read_text())
h['answer_transparency_batch'] = {
    'report': 'docs/47-answer-transparency-and-edition-coverage.md',
    'evidence_directory': 'research/reviews/refinement-20260915',
    'doctor_command': 'python3 scripts/doctor.py',
    'operational_ready': False,
    'scope': ('Answer transparency (engine checkpoints, a token-gated progress route, a composer stage line and '
              'a stop control that names the stage), whole-document section readings, cross-edition difference '
              'disclosure, a keyboard-only journey with its repairs, and an environment doctor. No warning '
              'contract, numeric contract, source term or engine claim changed.'),
    'automated_tests': 654,
    'javascript_component_checks': 60,
    'javascript_suites': {'test_charts.js': 2, 'test_views.js': 18, 'test_bulletin_ui.js': 6,
                          'test_conversation_ui.js': 13, 'test_suite_ui.js': 18, 'test_voice_ui.js': 3},
    'measured': {
        'checkpoints_defined': 6,
        'stages_observed_live': ['started', 'resolving', 'retrieving'],
        'queue': {'capacity': 3, 'max_waiting_observed': 1, 'turns_overlapped': 2},
        'whole_document_live': {'family': 'state_agromet', 'region': 'Gujarat', 'printed_issue': '2026-09-12',
                                'sections_indexed': 15, 'passages_indexed': 257, 'passages_served': 8},
        'editions_indexed_per_product_and_region_live': 1,
        'live_two_edition_comparison_performed': False,
        'keyboard': {'district_paths': 756, 'tabbable_after_repair': 1, 'tab_stops_from_find_to_district': 7,
                     'palette_opened_by_keyboard': True, 'escape_closes_palette': True},
        'doctor': {'ok': 13, 'warn': 0, 'fail': 0},
        'benchmark': {'cases': 17, 'turns': 19, 'declared_tasks': 18, 'completed': 12, 'incomplete': 6,
                      'completion_rate': 0.667, 'abstained_turns': 3, 'critical_failures': 0,
                      'changed_from_previous_run': False},
    },
    'repairs_recorded': [
        'Command-K had two owners: the palette opened and the question box was focused at the same time. The palette owns it; the slash key focuses the question box.',
        'All 756 district paths were tab stops, so the map could trap a keyboard user. One roving tab stop now moves with the arrow keys and Enter opens the district under the cursor.',
        'The palette control was named by its glyph; it is named Command palette.',
        'Ledger controls read only Delete and Open; each now names the stored conversation it acts on.',
        'The stage poll did not send the workspace token, so the stage line stayed empty. Fixed, and the live run records the rendered line.',
    ],
    'limitations': [
        'No live two-edition comparison: the corpus holds one indexed edition per product and region (534 district regions, 12 families).',
        'Live stage sampling observed three of six checkpoints; turns completed in five to twenty seconds.',
        'The keyboard journey is one Chrome instance, not screen-reader, zoom, high-contrast or cross-browser acceptance.',
        'The doctor reports presence of dependencies, not operational readiness, and measures no skill.',
        'The declared benchmark did not move: 12 of 18 declared tasks completed, unchanged from docs/45.',
    ],
}
h['updated_at_utc'] = now
h_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

p_path = pathlib.Path('data/registry/product-progress.json')
p = json.loads(p_path.read_text())
p['as_of_utc'] = now
p['latest_batch'] = 'docs/47-answer-transparency-and-edition-coverage.md'
p_path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

readme = pathlib.Path('README.md')
text = readme.read_text()
text = text.replace('python3 -m pytest tests/ -q                          # 635 Python tests',
                    'python3 -m pytest tests/ -q                          # 654 Python tests')
text = text.replace("""node tests/test_charts.js                            #  2 of 57 component checks
node tests/test_views.js                             # 16
node tests/test_bulletin_ui.js                       #  6
node tests/test_conversation_ui.js                   # 13
node tests/test_suite_ui.js                          # 17
node tests/test_voice_ui.js                          #  3""",
                    """node tests/test_charts.js                            #  2 of 60 component checks
node tests/test_views.js                             # 18
node tests/test_bulletin_ui.js                       #  6
node tests/test_conversation_ui.js                   # 13
node tests/test_suite_ui.js                          # 18
node tests/test_voice_ui.js                          #  3
python3 scripts/doctor.py                            # environment, model and corpus presence""")
text = text.replace('- [The Instrument Desk](docs/46-frontend-instrument-desk.md)',
                    '- [Answer transparency and cross-edition coverage](docs/47-answer-transparency-and-edition-coverage.md) — engine stages and queue position reported as facts, whole-edition readings, cross-edition differences named and never ranked, and a keyboard journey with its repairs.\n- [The Instrument Desk](docs/46-frontend-instrument-desk.md)', 1)
text = text.replace('- [The Instrument Desk frontend overhaul](docs/46-frontend-instrument-desk.md) — 57 component checks',
                    '- [Answer transparency and cross-edition coverage](docs/47-answer-transparency-and-edition-coverage.md) — 654 tests, 60 component checks, live stage readings, and the honest note that no live two-edition comparison was possible.\n- [The Instrument Desk frontend overhaul](docs/46-frontend-instrument-desk.md) — 57 component checks', 1)
readme.write_text(text, encoding='utf-8')

gap = pathlib.Path('docs/31-full-solution-gap-register.md')
lines = gap.read_text().splitlines()
entry = ("- **R15 is recorded in [docs/47](47-answer-transparency-and-edition-coverage.md).** The engine now reports its own "
         "checkpoints through a token-gated progress route and the composer shows the stage, the seconds in it and the queue "
         "position as facts; a whole-edition question is answered from the newest edition's printed sections in printed order "
         "with the count served; a newer edition is compared with the one before it and any dropped section or materially "
         "different text is named with both issue dates and never ranked; a keyboard-only journey repaired a 756-stop map tab "
         "order, an unnamed palette control and unnamed ledger controls; and the doctor script reports the pieces the "
         "workspace needs. **R15 closes no gap-register item and promotes no finding**; the live corpus holds one edition per "
         "product and region, so the comparison itself is pinned by component checks and the live change question reports the "
         "single-edition state. The declared benchmark did not move (12 of 18 declared tasks). 654 tests and 60 component "
         "checks passed at that checkpoint.")
for index in range(len(lines) - 1, -1, -1):
    if lines[index].startswith('- **R14 is recorded'):
        lines.insert(index + 1, entry)
        break
gap.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('hardening batch keys:', len(h))
print('latest_batch:', p['latest_batch'])
print('README test count line:', '654 Python tests' in readme.read_text())
print('gap register R15 present:', 'R15 is recorded' in gap.read_text())
