"""Offline, immutable inventory of saved source footprints. Does not create an LGD crosswalk."""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.geography import Geography, identity
from weathergpt_data.coverage import Coverage
from weathergpt_data.transport import parsed
from weathergpt_data.adapters import hourly, FORECAST, MARINE
from weathergpt_data.foundation import Foundation


def build(output, root=ROOT):
    root = Path(root).resolve(); output = Path(output).resolve()
    if output.exists(): raise FileExistsError('Output exists; choose a new immutable build directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.geography-', dir=output.parent))
    inputs = {}; geo = ledger = None
    baseline = root/'data/processed/foundation/20260911T194849Z'
    frozen = json.loads((baseline/'checkpoint-manifest.json').read_text())
    assessed = datetime.now(timezone.utc).isoformat()

    def read(path, expected=None, decode=True):
        body = path.read_bytes(); sha = hashlib.sha256(body).hexdigest()
        rel = str(path.relative_to(root))
        expected = expected or frozen['files'].get(rel)
        if expected is None or sha != expected: raise ValueError('Missing/mismatched evidence hash: ' + rel)
        inputs[rel] = sha
        return json.loads(body) if decode else body

    def saved(name): return read(baseline/(name+'.json'))
    def raw(meta): return read(root/'data/runtime'/meta['blob'], meta['sha256'], 'json' in meta['content_type'])
    def evidence(meta, artifact, locator):
        return {'source_id': meta['source_id'], 'url': meta['url'], 'sha256': meta['sha256'],
                'retrieved_at_utc': meta['retrieved_at_utc'], 'artifact': artifact, 'locator': locator}
    def add(meta, artifact, kind, code, label, locator, **kw):
        return geo.add(namespace=meta['source_id'], kind=kind, source_code=str(code),
                       label=label, locator=locator, version=meta['sha256'],
                       evidence=evidence(meta, artifact, locator), **kw)
    def coverage(meta, eid, product, variable, expected=1, validated=1, quarantined=0,
                 window_start=None, window_end=None, temporal='unresolved', notes=()):
        return ledger.record(product=product, entity_id=eid, variable=variable,
                             source_id=meta['source_id'], version=identity([meta['sha256'], 'geography-v1', assessed]),
                             window_start=window_start, window_end=window_end,
                             expected=expected, fetched=expected, validated=validated,
                             missing=expected-validated-quarantined, quarantined=quarantined,
                             evidence=meta, assessed_at=assessed, temporal=temporal,
                             spatial='source_identity', notes=notes)
    try:
        geo = Geography(stage/'geography.sqlite'); ledger = Coverage(stage/'coverage.sqlite')
        directory = saved('advisory-directory'); state_ids = {}
        meta = directory['states']['provenance']
        raw(meta)
        for i, state in enumerate(directory['states']['records']):
            state_ids[state['id']] = add(meta, 'advisory-directory.json', 'state', state['id'], state['label'],
                                          '$.states.records[%s]' % i)
        for i, group in enumerate(directory['results']):
            meta = group['provenance']; raw(meta)
            for j, district in enumerate(group['records']):
                locator = '$.results[%s].records[%s]' % (i, j)
                eid = add(meta, 'advisory-directory.json', 'district', group['state']+'/'+district['id'],
                          district['label'], locator, attributes={'source_state': group['state'], 'lgd_mapping': 'unresolved'})
                geo.relate(eid, state_ids[group['state']], 'listed_under', evidence(meta, 'advisory-directory.json', locator))
                coverage(meta, eid, 'advisory_directory', 'listed_entry',
                         notes=['Directory membership only. Bulletin availability, validity and current administrative identity unverified.'])
        warning = saved('national-warning-snapshot'); meta = warning['provenance']; features = raw(meta)
        if features.get('crs', {}).get('properties', {}).get('name') != 'urn:ogc:def:crs:EPSG::4326':
            raise ValueError('Unexpected warning source CRS')
        quarantines = {q['feature_index']: q['reason'] for q in warning['coverage']['quarantined']}
        accepted = {r['source_locator'] for r in warning['records']}
        if len(features['features']) != len(accepted) + len(quarantines): raise ValueError('Warning count mismatch')
        for i, feature in enumerate(features['features']):
            props = feature['properties']; locator = '$.features[%s]' % i
            if i not in quarantines and locator not in accepted: raise ValueError('Unaccounted warning feature')
            eid = add(meta, 'national-warning-snapshot.json', 'district', props['Obj_id'],
                      str(props.get('District') or '(missing source label)'), locator,
                      geometry=feature.get('geometry'), crs='EPSG:4326',
                      status='quarantined' if i in quarantines else 'source_record',
                      attributes={'quarantine_reason': quarantines.get(i), 'boundary_edition': 'unknown',
                                  'native_feature_id': feature.get('id'), 'lgd_mapping': 'unresolved'})
            coverage(meta, eid, 'official_warning_snapshot', 'source_feature',
                     validated=0 if i in quarantines else 1, quarantined=int(i in quarantines),
                     notes=['Counts source features, not current administrative districts or active alerts.',
                            'Day validity and CAP lifecycle unresolved. No alert eligibility.'])
        stations = saved('aviation-stationinfo'); meta = stations['provenance']; raw(meta)
        for station in stations['records']:
            add(meta, 'aviation-stationinfo.json', 'airport', station['station_id'], station['name'],
                station['source_locator'], aliases=[{'name': station['station_id'], 'language': 'und'}],
                geometry={'type': 'Point', 'coordinates': [station['longitude'], station['latitude']]},
                crs='EPSG:4326', attributes={'reported_wmo_id': station['wmo_id'],
                                           'district_representativeness': 'unverified'})
        places = saved('place-ahmedabad'); meta = places['provenance']; raw(meta)
        for i, place in enumerate(places['records']):
            add(meta, 'place-ahmedabad.json', 'place', place['id'], place['name'], '$.records[%s]' % i,
                geometry={'type': 'Point', 'coordinates': [place['longitude'], place['latitude']]},
                crs='EPSG:4326', attributes={'provider_fields': place, 'lgd_mapping': 'unresolved'})
        numeric_replays = []
        names = sorted([p.stem for p in baseline.glob('forecast-*.json')] +
                       [p.stem for p in baseline.glob('marine-*.json') if p.stem in
                        {'marine-arabian-sea', 'marine-bay-of-bengal', 'marine-andaman-sea'}] + ['river-ahmedabad'])
        for name in names:
            sample = saved(name); meta = sample['provenance']; data = raw(meta)
            query = parse_qs(urlparse(meta['url']).query)
            days = int(query['forecast_days'][0]); start = parsed(meta['retrieved_at_utc']).astimezone(timezone.utc).date()
            end = start + timedelta(days=days-1); requested = sample['coverage']['requested_point']
            if name.startswith('river-'):
                replay = Foundation.daily(data, meta, requested, {'river_discharge': ('m³/s', 0)},
                                          'river_discharge', 'GloFAS delivery', (start, end)); step = 1
            else:
                fields = FORECAST if name.startswith('forecast-') else MARINE
                replay = hourly(data, meta, fields, sample['family'], sample['records'][0]['model'], requested, (start, end)); step = 24
            grid = replay['coverage']['returned_grid']
            eid = add(meta, name+'.json', 'model_point', identity([meta['source_id'], query, grid]), name,
                      '$.coverage.returned_grid', geometry={'type': 'Point', 'coordinates': [grid['longitude'], grid['latitude']]},
                      crs='EPSG:4326', attributes={'requested_point': requested, 'returned_point': grid,
                                                 'request_settings': query, 'native_grid_id': None,
                                                 'spatial_support': 'provider_returned_sample_point', 'run_id': None})
            for variable in sorted({r['parameter'] for r in replay['records']}):
                rows = [r for r in replay['records'] if r['parameter'] == variable]
                coverage(meta, eid, sample['family'], variable, expected=days*step,
                         validated=sum(r['value'] is not None for r in rows),
                         window_start=start.isoformat()+'T00:00:00+00:00',
                         window_end=(end+timedelta(days=1)).isoformat()+'T00:00:00+00:00', temporal='validated',
                         notes=['Replayed against original request date; not a live fetch.',
                                'Interval is sample timestamps; precipitation retains preceding-hour support in normalized records.',
                                'Provider point is not a stable grid identity or a district average.'])
            numeric_replays.append({'sample': name, 'records': replay['count'], 'result': 'pass'})
        kinds = dict(geo.db.execute('SELECT kind,count(*) FROM entities GROUP BY kind'))
        sources = dict(geo.db.execute('SELECT namespace,count(*) FROM entities GROUP BY namespace'))
        coverage_counts = dict(ledger.db.execute('SELECT product,count(*) FROM coverage GROUP BY product'))
        ids = [r[0] for r in ledger.db.execute('SELECT coverage_id FROM coverage')]
        eligible = sum(ledger.assess(cid, assessed)['eligible'] for cid in ids)
        if eligible: raise ValueError('Reference inventory must not promote operational eligibility')
        examples = {'ahmedabad': geo.resolve('Ahmedabad'), 'airport_vaah': geo.resolve('VAAH', kind='airport'),
                    'warning_point_ahmedabad': geo.areas_at(23.02579, 72.58727, 'S15', warning['provenance']['sha256']),
                    'warning_coverage_example': ledger.assess(next(r[0] for r in ledger.db.execute("SELECT coverage_id FROM coverage WHERE source_id='S15'")), assessed)}
        for db in [geo.db, ledger.db]:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('SQLite integrity failure')
        summary = {'schema_version': 'source-geography-v1', 'assessed_at_utc': assessed,
                   'scope': 'Saved source footprint inventory; not an authoritative nationwide administrative catalogue.',
                   'entities_by_type': kinds, 'entities_by_source': sources, 'coverage_assessments_by_product': coverage_counts,
                   'source_warning_features': len(features['features']), 'warning_quarantines': len(quarantines),
                   'gujarat_advisory_directory_entries': next(r['count'] for r in directory['results'] if r['state'] == 'Gujarat'),
                   'reviewed_crosswalks': 0, 'current_lgd_inventory_imported': False,
                   'eligible_assessments': eligible, 'numeric_replays': numeric_replays,
                   'open_dependencies': ['Dated authoritative administrative export and changes', 'Reviewed source-to-administration crosswalks',
                                         'Boundary provenance and spatial representativeness', 'Coverage expectations for every PS capability',
                                         'Current official warnings, lifecycle and source freshness', 'Scheduler and serving integration']}
        for name, value in [('summary.json', summary), ('examples.json', examples)]:
            (stage/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
        geo.close(); geo = None; ledger.close(); ledger = None
        for rel, sha in inputs.items():
            if hashlib.sha256((root/rel).read_bytes()).hexdigest() != sha: raise ValueError('Input changed during build')
        implementation = ['weathergpt_data/geography.py', 'weathergpt_data/coverage.py',
                          'weathergpt_data/adapters.py', 'weathergpt_data/foundation.py', 'scripts/build_geography_catalogue.py']
        manifest = {'inputs': inputs, 'implementation': {p: hashlib.sha256((root/p).read_bytes()).hexdigest() for p in implementation},
                    'outputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir()},
                    'operational_ready': False}
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        # Atomic directory creation refuses an existing nonempty build; no mutable current pointer.
        if output.exists(): raise FileExistsError('Output was created concurrently')
        os.rename(stage, output)
        return summary
    except Exception:
        if geo: geo.close()
        if ledger: ledger.close()
        shutil.rmtree(stage)
        raise


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    print(json.dumps(build(p.parse_args().output), indent=2))
