import json, pathlib, datetime

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

h_path = pathlib.Path('data/registry/hardening-progress.json')
h = json.loads(h_path.read_text())
h['alert_brief_batch'] = {
    'report': 'docs/49-engine-architecture-and-gap-analysis.md',
    'evidence_directory': 'research/implementation/alert-brief-20260915',
    'operational_ready': False,
    'scope': ('The alert journey: one point and one published warning day become an artefact - the day status in the '
              'product own terms, the bulletin identity and retrieval instant, the CAP relay reported separately, what '
              'would change it, what is not established, how to check again, and a content hash. Exposed as a product '
              'view, a CLI that writes Markdown, and an action on the warnings surface.'),
    'automated_tests': 713,
    'javascript_component_checks': 61,
    'measured': {
        'live_brief': {'place': 'Ahmedabad, Gujarat', 'day': 1,
                       'status_line': 'Official district warning: yellow - Thunderstorm/lightning/squall',
                       'brief_identity_prefix': 'c68f1b47a7e4ec57', 'drawer_characters': 1910},
        'artefacts': ['brief-patna-day2.md (warning day)', 'brief-patna-day5.md (quiet day)',
                      'brief-arabian-sea-day1.md (outside every district)'],
        'cold_process_latency_seconds': 50,
        'delivery': 'none; nothing is pushed, emailed or published',
    },
    'limitations': [
        'No delivery, subscription or dissemination: the brief is a local artefact.',
        'The first brief in a cold process waits on the district warning layer fetch (about fifty seconds here).',
        'Flood and cyclone warnings, sea-area bulletins and personal field decisions are outside its evidence.',
        'The CAP relay remains separately reported and its origin unauthenticated.',
    ],
}
h['updated_at_utc'] = now
h_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')

p_path = pathlib.Path('data/registry/product-progress.json')
p = json.loads(p_path.read_text())
p['as_of_utc'] = now
p['latest_batch'] = 'docs/49-engine-architecture-and-gap-analysis.md'
p_path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')

readme = pathlib.Path('README.md')
text = readme.read_text()
text = text.replace('# 705 Python tests', '# 713 Python tests')
line = ('- **An alert brief you can keep.** One place and one published warning day become an artefact: the day status in '
        'the product own terms, the bulletin identity and retrieval instant, the CAP relay reported separately, what would '
        'change it, what is not established, and a content hash. Written with scripts/alert_brief.py. Nothing is delivered '
        'anywhere.' + chr(10))
if 'An alert brief you can keep' not in text:
    text = text.replace('- **Two products, one answer.**', line + '- **Two products, one answer.**', 1)
readme.write_text(text, encoding='utf-8')

gap = pathlib.Path('docs/31-full-solution-gap-register.md')
lines = gap.read_text().splitlines()
entry = ("- **R20 is recorded in [docs/49](49-engine-architecture-and-gap-analysis.md).** The warning journey now ends in an "
         "artefact: the alert-brief route, the alert_brief.py CLI and an action on the warnings surface produce a brief for one "
         "point and one published day carrying the day status, the bulletin identity and retrieval instant, the CAP relay reported "
         "separately, what would change it, what is not established and a content hash; three artefacts were recorded (a warning "
         "day, a quiet day, a point outside every district) and the cold-process latency of about fifty seconds is recorded rather "
         "than hidden. **R20 closes no gap-register item**; delivery, subscription and dissemination remain absent by design, and "
         "flood, cyclone and sea-area products are still unconnected. 713 tests and 61 component checks passed at that checkpoint.")
inserted = False
for index in range(len(lines) - 1, -1, -1):
    if lines[index].startswith('- **R19 is recorded'):
        lines.insert(index + 1, entry)
        inserted = True
        break
gap.write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
print('batches:', len(h), '| README updated:', '713 Python tests' in readme.read_text(),
      '| brief line:', 'An alert brief you can keep' in readme.read_text(), '| R20:', inserted)
