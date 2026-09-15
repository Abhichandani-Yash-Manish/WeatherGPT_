import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
old_tests = '# 754 Python tests'
assert t.count(old_tests) == 1
t = t.replace(old_tests, '# 764 Python tests', 1)
old_lang = '- **Language output is measured per direction, not fluent.** Twenty languages'
assert t.count(old_lang) == 1, t.count(old_lang)
start = t.index(old_lang)
end = t.index(chr(10), start)
t = t[:start] + "- **Language output is measured per direction, not fluent.** Nineteen of twenty-three registered languages pass a measured `write` gate (including Hindi and Gujarati); ten of those also pass measured speech and hearing, the rest are readable but speech for them is beta-gated by the provider. Four fail the write gate and are refused rather than offered with a warning, each with its recorded reason. Rendering puts a deterministic gate between the evidence and the reader: values are withheld and substituted, safety-critical clauses are held, and the gate now also refuses a rendering that mixes Indian scripts or that is not written in the requested script at all - a Tamil rendering carrying Telugu characters was shipped before that check existed. A failed gate keeps the source-language answer and says which failure it was. Quoted published passages are evidence and are never rewritten: of 6,739 indexed passages only 107 contain Devanagari, all of them bilingual letterheads, so document coverage in the language sense is not established. No native speaker has reviewed any output." + t[end:]
doc_anchor = '- [A briefing you write on a schedule](docs/51-scheduled-briefing.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [Language and voice, re-measured](docs/52-language-and-voice-measurement.md) - a stricter gate that refuses mixed scripts, the ledger re-measured at 19 of 23 write and 10 of 23 speak and hear, six journeys including a Hindi clarification rendered through the gate, real audio for Hindi and Gujarati, and the measured document-language gap." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['language_voice_batch'] = {
    'report': 'docs/52-language-and-voice-measurement.md',
    'evidence_directory': 'research/implementation/language-voice-20260915',
    'operational_ready': False,
    'scope': "WS8: the language and voice path re-measured after the engine work, two gate defects repaired (a rendering that mixes Indian scripts, and a script verdict that was computed and never used), a refused script rendering reported as such rather than as an unreachable service, an agromet advisory with a crop routed to agriculture rather than to the warning product, the language ledger re-measured, six journeys recorded, real audio measured for Hindi and Gujarati, and the document-language gap measured.",
    'automated_tests': 764,
    'javascript_component_checks': 70,
    'measured': {'ledger': {'file': 'data/registry/language-support.json', 'registered': 23, 'write_verified': 19, 'write_failed': 4,
                            'speak_verified': 10, 'hear_verified': 10,
                            'write_failures': {'ta': 'a protected value was duplicated by the rendering',
                                               'sd': 'the rendering was not written in this script',
                                               'sat': 'a protected value did not survive the rendering',
                                               'mni': 'the rendering was not written in this script'}},
                 'journeys': {'turns': 6, 'adherence': {'values_did_not_survive': 3, 'written_by_template': 1,
                                                       'rendered_with_protected_values': 2, 'rendered_in_another_script': 1}},
                 'speech': {'hi': {'audio_bytes': 188204, 'detected': 'hi-IN', 'number_as_digits': False},
                            'gu': {'audio_bytes': 225836, 'detected': 'gu-IN', 'unit_present': False}},
                 'documents': {'passages': 6739, 'devanagari': 107, 'other_indic': 5,
                               'note': 'the non-Latin passages are bilingual letterheads, some with degraded extraction; no substantive non-English prose is indexed'}},
    'limitations': ['No fluency, accuracy or native acceptability: no native speaker has reviewed any rendering, transcript or audio.',
                    'Recognition probability is the recogniser own number, was absent for one probe, and is never answer or forecast confidence.',
                    'No mobile, noisy-input, barge-in, screen-reader or cross-browser voice acceptance.',
                    'Document coverage in the language sense is not established: the corpus is English and quoted passages are never rewritten.'],
}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/52-language-and-voice-measurement.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R23 is recorded'):
        glines.insert(index + 1, "- **R24 is recorded in [docs/52](52-language-and-voice-measurement.md).** WS8 was re-measured and two gate defects were repaired: a rendering that mixed Indian scripts could pass the script check (a Tamil answer carrying Telugu characters), and the script verdict was computed and never used, so a rendering not written in the requested language could still report ok. A refused script rendering now names itself instead of being reported as an unreachable service. The ledger was re-measured under the stricter gate: 19 of 23 languages pass write, 10 pass speak and hear, and four fail with their own recorded reasons. Six journeys and real audio for Hindi and Gujarati are recorded, and the document-language gap is a number: 107 of 6,739 passages carry Devanagari, all bilingual letterheads. **R24 closes no gap-register item**: no native speaker has reviewed anything, mobile and noisy-input acceptance are unmeasured, and document coverage in the language sense is not established. 764 Python tests and 70 component checks passed at that checkpoint.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/52' in r.read_text(), '| batch', 'language_voice_batch' in h.read_text(), '| R24', inserted)