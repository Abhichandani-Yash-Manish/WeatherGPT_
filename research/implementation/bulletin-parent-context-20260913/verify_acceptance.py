"""Verify task outcomes, source bytes and independently located parent text."""
import io
import json
import re
import statistics
import sys
import urllib.request
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.bulletin_index import BulletinIndex, EXTRACTION_VERSION, clean
from weathergpt_data.bulletin_context import parent_context
from weathergpt_data.transport import digest, parsed
import pdfplumber

out = Path(__file__).parent
folder = out / sys.argv[1]
rows = json.loads((folder / 'summary.json').read_text())
packets = {r['file'].removesuffix('.json'): json.loads((folder / r['file']).read_text()) for r in rows}
assert len(packets) == 15 and all('error' not in p for p in packets.values())
def crop(p): return [x for x in p.get('passages', []) if x['evidence_kind'] == 'published_advisory_passage']
def context(p): return [x for x in p.get('passages', []) if x['evidence_kind'] == 'published_bulletin_context']
for key in ['1-1', '1-2', '1-3']:
    p = packets[key]
    assert p['status'] == 'partial' and len(crop(p)) == 3 and len(context(p)) == 6
    assert all(x['district'] == 'Dibrugarh' and x['crop_key'] == 'rice' and not x['stage'] for x in crop(p))
    assert 'Postpone sowing' in p['answer'] and 'guidance needs reconciliation' in p['answer']
    assessment = p['retrieval_coverage'][0]['parent_context']
    assert assessment['status'] == 'partial' and len(assessment['qualification_flags']) == 1
    assert not assessment['dissemination_eligible']
assert packets['1-2']['retrieval_coverage'][0]['selection'] == 'all'
assert packets['1-2']['trace']['planning']['model_calls'] == 0
assert packets['1-3']['passages'] == packets['1-2']['passages']
for key, district, expected_crop in [('2-1', 'Coimbatore', 'banana'), ('3-1', 'Kamrup', 'rice'), ('3-2', 'Kamrup', 'maize')]:
    assert packets[key]['status'] == 'answered'
    assert all(x['district'] == district and x['crop_key'] == expected_crop for x in crop(packets[key]))
    assert context(packets[key])
assert all(x['stage'] == 'Sowing' for x in crop(packets['3-2']))
p = packets['4-1']
assert {x['crop_key'] for x in crop(p)} == {'cotton', 'groundnut'}
assert p['task_coverage']['completed'] == 2
p = packets['5-1']
assert p['status'] == 'partial' and len(p['task_results']) == 2 and not p['facts']
forecast = next(t for t in p['task_results'] if t['request']['kind'] == 'forecast')
assert forecast['status'] == 'needs_clarification' and 'village or town' in forecast['answer']
assert not forecast['passage_ids'] and all(x['task_id'] != forecast['id'] for x in p['passages'])
for key in ['6-1', '6-2']:
    assert packets[key]['status'] == 'needs_clarification'
for key in ['6-3', '6-4', '7-1', '8-1', '9-1']:
    assert packets[key]['status'] == 'unavailable' and not packets[key].get('passages')
for key in ['6-2', '6-3', '6-4']:
    p = packets[key]
    assert p['plan']['places'][0]['name'] == 'Nagpur'
    assert p['plan']['tasks'][0]['kind'] == 'agriculture'
    assert p['plan']['tasks'][0]['start_local'] == packets['6-1']['plan']['tasks'][0]['start_local']
assert packets['6-4']['plan']['tasks'][0]['document_request']['growth_stage'] == 'flowering'

point = json.loads((out / 'live-point/1-1.json').read_text())
assert len(point['facts']) == 3 and point['status'] == 'partial'
assert [p['kind'] for p in point['plan']['places']] == ['district', 'settlement']
forecast = next(t for t in point['task_results'] if t['request']['kind'] == 'forecast')
assert forecast['status'] == 'answered' and not forecast['passage_ids']
assert all(p['task_id'] != forecast['id'] for p in point['passages'])
packets['explicit-city-mixed'] = point
rows += json.loads((out / 'live-point/summary.json').read_text())

index = BulletinIndex(ROOT / 'data/runtime/ingestion/bulletins' / EXTRACTION_VERSION / 'index.sqlite')
docs, sections, pdf_hashes = {}, {}, {}
counts = {'crop_passage_instances': 0, 'parent_section_instances': 0, 'numeric_facts': 0, 'independent_parent_locator_checks': 0}
blobs = {p.stem: p for p in (ROOT / 'data/runtime/ingestion').rglob('*.bin')}
for p in packets.values():
    citations = {c['id']: c for c in p['citations'] if c.get('id')}
    for item in p.get('passages', []):
        citation = citations[item['citation_ids'][0]]
        sha = citation['response_sha256']
        assert sha == item['document_sha256'] and item['text'] in p['answer']
        assert item['citation_ids'][0].startswith(item['task_id'] + '-')
        if sha not in docs:
            docs[sha] = index.document(sha)
            sections[sha] = parent_context(docs[sha])[0]
            with urllib.request.urlopen('http://127.0.0.1:8765' + citation['local_document_path']) as response:
                body = response.read()
                assert digest(body) == sha and 'application/pdf' in response.headers['Content-Type']
                pdf_hashes[sha] = response.status
        doc = docs[sha]
        assert (item['district'], item['state'], item['issue_date']) == (doc['district'], doc['state'], doc['issue_date'])
        is_context = item['evidence_kind'] == 'published_bulletin_context'
        source = next(c for c in (sections[sha] if is_context else doc['chunks']) if c['id'] == item['id'])
        assert all(item[k] == v for k, v in source.items())
        counts['parent_section_instances' if is_context else 'crop_passage_instances'] += 1
        if is_context and item.get('locators'):
            # Separate from the line/heading parser: read only the stored rectangles.
            with pdfplumber.open(doc['provenance']['raw_file']) as pdf:
                text = clean(' '.join(pdf.pages[l['page'] - 1].crop(l['bbox']).extract_text() or '' for l in item['locators']))
            assert text == item['text'], item['section']
            counts['independent_parent_locator_checks'] += 1
    for coverage in p.get('retrieval_coverage', []):
        owned = {x['id'] for x in p.get('passages', []) if x['task_id'] == coverage['task_id']}
        for flag in coverage.get('parent_context', {}).get('qualification_flags', []):
            assert set(flag['passage_ids']) <= owned
    for fact in p['facts']:
        assert all(c in citations for c in fact['citation_ids'])
        assert all(citations[c]['response_sha256'] == fact['evidence_version'] and citations[c]['source_id'] == fact['source_id'] for c in fact['citation_ids'])
        body = blobs[fact['evidence_version']].read_bytes()
        assert digest(body) == fact['evidence_version']
        raw = json.loads(body)
        match = re.fullmatch(r'\$\.hourly\.(\w+)\[(\d+)\]', fact['source_locators'][0])
        assert match
        parameter, i = match[1], int(match[2])
        assert fact['parameter'] == parameter and raw['hourly_units'][parameter] == fact['unit']
        assert Decimal(str(raw['hourly'][parameter][i])) == Decimal(fact['value'])
        assert parsed(fact['end']).timestamp() == raw['hourly']['time'][i]
        assert parsed(fact['start']).timestamp() == raw['hourly']['time'][i] - 3600
        counts['numeric_facts'] += 1

result = {'http_turns': len(packets), 'statuses': {s: sum(p['status'] == s for p in packets.values()) for s in sorted({p['status'] for p in packets.values()})},
          **counts, 'pdf_http_hashes': pdf_hashes,
          'latency_seconds': {'median': statistics.median(r['seconds'] for r in rows), 'max': max(r['seconds'] for r in rows)},
          'scope': 'Local Ollama HTTP journeys, source-byte replay and parent rectangle checks. No operational, national, language or agronomic acceptance.'}
(out / 'acceptance.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
