import json, pathlib, datetime

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

h_path = pathlib.Path('data/registry/hardening-progress.json')
h = json.loads(h_path.read_text())
h['advisory_brief_batch'] = {
    'report': 'docs/49-engine-architecture-and-gap-analysis.md',
    'evidence_directory': 'research/implementation/advisory-brief-20260915',
    'operational_ready': False,
    'scope': ('Agriculture depth: a composed advisory brief for one district, crop and stage - published passages quoted '
              'with source, page, printed issue date and locator, the source conditions quoted as conditions, the forecast '
              'kept apart as context with its samples and source, decision support naming what it does not know, and no '
              'prescription, diagnosis or dose decision.'),
    'automated_tests': 726,
    'javascript_component_checks': 61,
    'measured': {
        'district_edition_used': {'family': 'district_agromet', 'region': 'Ahmedabad', 'printed_issue': '2026-09-11',
                                  'passages_quoted': 1, 'source_id': 'S57'},
        'crops_left_out_of_a_cotton_brief': ['chilli', 'gram', 'groundnut', 'rice'],
        'forecast_context': {'source_id': 'S62', 'parameters': 8, 'samples_per_parameter': 24,
                             'note': 'first and last values of the retrieved series; no summary computed'},
        'artefacts': ['brief-ahmedabad-cotton-day1.md', 'brief-ahmedabad-cotton-decision-support.md',
                      'brief-kohima-rice-not-held.md'],
        'name_resolution_disclosed': 'Ahmadabad was read as Ahmedabad, the spelling the edition uses',
    },
    'limitations': [
        'No agronomist has reviewed the composition; the source conditions are quoted, not checked against a field.',
        'The forecast remains a grid-cell model value, not an observation of the field.',
        'Nothing is delivered or scheduled: the artefact is written locally on request.',
        'A district without an indexed edition falls back to the state edition, named as such; a missing state edition is reported.',
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
text = text.replace('# 713 Python tests', '# 726 Python tests')
line = ('- **An advisory brief for a crop.** One district, one crop and one stage become an artefact: published advice '
        'quoted with its page and printed issue date, the source conditions quoted as conditions, the forecast kept apart '
        'as context, what a decision still needs when asked, and no prescription, diagnosis or dose decision. Another '
        'crop is never served for the one asked about. Written with scripts/advisory_brief.py.' + chr(10))
if 'An advisory brief for a crop' not in text:
    text = text.replace('- **An alert brief you can keep.**', line + '- **An alert brief you can keep.**', 1)
readme.write_text(text, encoding='utf-8')

gap = pathlib.Path('docs/31-full-solution-gap-register.md')
lines = gap.read_text().splitlines()
entry = ("- **R21 is recorded in [docs/49](49-engine-architecture-and-gap-analysis.md).** Agriculture gained a composed advisory "
         "brief: published agromet passages quoted with source, page, printed issue date and locator; the source conditions quoted as "
         "conditions; the forecast kept apart as context with its samples and source; decision support naming what it does not know; "
         "and no prescription, diagnosis or dose decision. The requested district is resolved against the names the editions actually "
         "use and the resolution is disclosed; a crop the edition does not name is disclosed rather than substituted, and a district "
         "without an edition falls back to its state edition. **R21 closes no gap-register item**; no agronomist has reviewed the "
         "composition, nothing is delivered or scheduled, and WS7-WS9 remain open. 726 tests and 61 component checks passed at that "
         "checkpoint.")
inserted = False
for index in range(len(lines) - 1, -1, -1):
    if lines[index].startswith('- **R20 is recorded'):
        lines.insert(index + 1, entry)
        inserted = True
        break
gap.write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
print('batches:', len(h), '| README:', '726 Python tests' in readme.read_text(), '| line:', 'An advisory brief for a crop' in readme.read_text(), '| R21:', inserted)
