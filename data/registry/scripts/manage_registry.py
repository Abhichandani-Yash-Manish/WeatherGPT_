#!/usr/bin/env python3
"""Generate review views; verify registry references and frozen asset hashes offline."""
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'data/registry'


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Read-only verification, including generated views')
    parser.add_argument('--refresh-assets', action='store_true', help='Explicitly create/update the asset hash inventory after reviewing additions')
    args = parser.parse_args()
    if args.check and args.refresh_assets:
        parser.error('--check cannot refresh assets')
    registry = json.loads((HERE / 'sources.json').read_text())
    products = registry['products']
    ids = [s['id'] for s in products]
    assert len(ids) == len(set(ids)), 'Duplicate source IDs'
    questions = set(re.findall(r'Q\d{2}', (ROOT / 'research/discovery/question-evidence-map.md').read_text()))
    required = {'product', 'record_kind', 'evidence_level', 'processing_state', 'production_readiness',
                'priority', 'access_class', 'target_record_family', 'spatial_scope', 'temporal_scope',
                'fields_and_units', 'first_processing_task', 'usage_terms', 'user_review', 'owner',
                'evidence_files', 'supports_questions', 'upstream_source_ids'}
    levels = {'lead', 'access_blocked', 'catalogue_or_page_inspected', 'sample_inspected'}
    states = {'sample_missing', 'source_missing', 'sample_ready_for_processing', 'deferred', 'processed_snapshot'}
    asset_sources = {}
    for source in products:
        assert required <= source.keys(), (source['id'], 'Missing required fields')
        assert source['evidence_level'] in levels, source['id']
        assert source['processing_state'] in states, source['id']
        assert source['priority'] in {'first', 'next', 'later', 'optional'}, source['id']
        assert set(source['supports_questions']) <= questions, source['id']
        assert set(source['upstream_source_ids']) <= set(ids), source['id']
        assert source['id'] not in source['upstream_source_ids'], source['id']
        if source['processing_state'] in {'sample_ready_for_processing', 'processed_snapshot'}:
            assert source['evidence_level'] == 'sample_inspected' and source['evidence_files'], source['id']
        if source['processing_state'] == 'processed_snapshot':
            output = source['processing_outputs']
            build_manifest = json.loads((ROOT / output['manifest']).read_text())
            assert source['id'] in {item['source_id'] for item in build_manifest['inputs']}, source['id']
            for name, digest in build_manifest['outputs'].items():
                file = (ROOT / output['directory'] / name).resolve()
                assert file.is_relative_to(ROOT) and file.is_file(), str(file)
                assert hashlib.sha256(file.read_bytes()).hexdigest() == digest, str(file)
        for name in source['evidence_files']:
            path = (ROOT / name).resolve()
            assert path.is_relative_to(ROOT), (source['id'], 'Evidence must be project-local')
            assert path.is_file(), (source['id'], name, 'Missing evidence')
            asset_sources.setdefault(name, set()).add(source['id'])
    # Catch lineage cycles as the register grows.
    by_id = {s['id']: s for s in products}
    def walk(sid, trail):
        assert sid not in trail, ('Lineage cycle', sid)
        for parent in by_id[sid]['upstream_source_ids']:
            walk(parent, trail | {sid})
    for sid in ids:
        walk(sid, set())
    for name in ['data/registry/imports.json', registry['legacy_snapshot'], 'research/discovery/question-evidence-map.md']:
        assert (ROOT / name).is_file(), name
        asset_sources.setdefault(name, set())
    assets = []
    for name, sids in sorted(asset_sources.items()):
        payload = (ROOT / name).read_bytes()
        assets.append({'path': name, 'source_ids': sorted(sids), 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
    manifest = HERE / 'assets.json'
    if args.refresh_assets:
        manifest.write_text(encoded({'created_at_utc': datetime.now(timezone.utc).isoformat(),
                                     'scope': 'Referenced local evidence and supplied imports; hashes establish file integrity, not source authenticity.',
                                     'files': assets}))
    assert manifest.exists(), 'Create the initial asset inventory with --refresh-assets'
    assert json.loads(manifest.read_text())['files'] == assets, 'Asset inventory drift: inspect changes before --refresh-assets'
    for item in json.loads((HERE / 'imports.json').read_text())['files']:
        payload = (ROOT / item['path']).read_bytes()
        assert len(payload) == item['bytes'] and hashlib.sha256(payload).hexdigest() == item['sha256'], item['path']

    columns = ['id', 'product', 'record_kind', 'category', 'priority', 'evidence_level', 'processing_state',
               'access_class', 'target_record_family', 'spatial_scope', 'temporal_scope', 'fields_and_units',
               'first_processing_task', 'known_limitations', 'supports_questions', 'upstream_source_ids',
               'access_url', 'documentation_url', 'usage_terms', 'last_evidence_date', 'production_readiness',
               'selection', 'user_review', 'owner', 'evidence_files']
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    for source in products:
        writer.writerow({key: ' ; '.join(source.get(key, [])) if isinstance(source.get(key), list)
                         else source.get(key) for key in columns})
    details = ['# WeatherGPT source cards', '', 'Generated from `sources.json`; edit the JSON and regenerate. Original discovery: 11 September 2026. Selected routes rechecked on 12 September IST; see individual access checks. Other access statuses remain historical.', '']
    for source in products:
        details += [f"## {source['id']} — {source['product']}", '',
                    f"**Evidence:** {source['evidence_level']} · **Processing:** {source['processing_state']} · **Priority:** {source['priority']}", '',
                    f"**Where:** {source['access_url'] or 'Source not selected'}", '',
                    f"**Geography:** {source['spatial_scope']}", '',
                    f"**Time:** {source['temporal_scope']}", '',
                    f"**Fields/units:** {source['fields_and_units']}", '',
                    f"**First task:** {source['first_processing_task']}", '',
                    '**Unresolved:** ' + ' '.join(dict.fromkeys(source['known_limitations'] + source['open_questions'])), '',
                    f"**Terms:** {source['usage_terms']}", '',
                    f"**Questions:** {', '.join(source['supports_questions']) or 'Optional supporting reference'}", '',
                    '**Evidence files:**', '']
        details += [f'- [{Path(name).name}](../../{name.replace(" ", "%20")})' for name in source['evidence_files']] or ['- No local sample.']
        details += ['', f"**Review:** {source['user_review']} · **Production:** {source['production_readiness']}", '']
    views = {'sources.csv': buffer.getvalue(), 'source-cards.md': '\n'.join(details)}
    for name, content in views.items():
        path = HERE / name
        if args.check:
            assert path.exists() and path.read_text() == content, f'Stale generated view: {name}'
        else:
            path.write_text(content)
    print(encoded({'result': 'PASS', 'source_entries': len(products), 'evidence_assets': len(assets),
                   'evidence_bytes': sum(a['bytes'] for a in assets),
                   'evidence_levels': dict(Counter(s['evidence_level'] for s in products)),
                   'processing_states': dict(Counter(s['processing_state'] for s in products)),
                   'checks': ['unique IDs', 'question references', 'lineage references and cycles',
                              'local evidence paths', 'asset hashes', 'import hashes', 'generated views']}))


if __name__ == '__main__':
    main()
