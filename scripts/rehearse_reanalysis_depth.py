#!/usr/bin/env python3
"""Rehearse the daily reanalysis path against the live archive through the governed store.

    python3 scripts/rehearse_reanalysis_depth.py [--output DIR]

Unlike the catalogue probe, which asks the raw endpoint, this runs the real adapter:
the governed Store fetches S22, checks the payload, and returns the validated envelope
with its provenance. It records one ERA5 run over a mixed variable set, one ERA5-Land
run over the surface variables that model carries, and the variables ERA5-Land does
not carry. The output is evidence for the docs, not a forecast or a skill claim.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from weathergpt_data.adapters import reanalysis_supported  # noqa: E402
from weathergpt_data.foundation import Foundation  # noqa: E402
from weathergpt_data.transport import Store  # noqa: E402

POINT = {'latitude': 23.02579, 'longitude': 72.58727}
START, END = '2024-07-01', '2024-07-02'
ERA5_LAND_ABSENT = ('precipitation_sum', 'rain_sum', 'wind_speed_10m_max', 'shortwave_radiation_sum')


def summarise(envelope):
    by_parameter = {}
    for record in envelope['records']:
        entry = by_parameter.setdefault(record['parameter'], {'unit': record['unit'], 'count': 0, 'non_null': 0, 'first': None})
        entry['count'] += 1
        if record['value'] is not None:
            entry['non_null'] += 1
            if entry['first'] is None:
                entry['first'] = record['value']
    return {'status': envelope['status'], 'quality': envelope['quality'], 'count': envelope['count'],
            'returned_grid': envelope['coverage']['returned_grid'], 'parameters': by_parameter,
            'url': envelope['provenance']['url'], 'response_sha256': envelope['provenance']['sha256'],
            'retrieved_at_utc': envelope['provenance']['retrieved_at_utc'], 'limitations': envelope['limitations']}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output')
    arguments = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = Path(arguments.output) if arguments.output else ROOT / 'research' / 'implementation' / 'reanalysis-depth-20260915'
    output.mkdir(parents=True, exist_ok=True)

    foundation = Foundation(Store(ROOT / 'data/runtime'))
    era5 = foundation.history_local(POINT['latitude'], POINT['longitude'], START, END, refresh=True, models='era5')
    land = foundation.history_local(POINT['latitude'], POINT['longitude'], START, END, refresh=True, models='era5_land')

    report = {'schema_version': 'reanalysis-depth-rehearsal-v1',
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'point': POINT, 'window': [START, END],
              'era5': summarise(era5), 'era5_land': summarise(land),
              'era5_land_supported': sorted(reanalysis_supported('era5_land')),
              'era5_land_not_supported': sorted(reanalysis_supported('era5') - reanalysis_supported('era5_land'))}
    path = output / 'live-rehearsal.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('live rehearsal -> ' + str(path.relative_to(ROOT)))
    for name in ('era5', 'era5_land'):
        row = report[name]
        carried = [key for key, value in row['parameters'].items() if value['non_null']]
        empty = [key for key, value in row['parameters'].items() if not value['non_null']]
        print('  %-10s status %-8s records %3d  carried %2d  empty %2d  grid %s' % (
            name, row['status'], row['count'], len(carried), len(empty), row['returned_grid']))
        if empty:
            print('       empty: ' + ', '.join(sorted(empty)))
    print('  era5_land omits: ' + ', '.join(report['era5_land_not_supported']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
