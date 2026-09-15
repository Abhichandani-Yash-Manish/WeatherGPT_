#!/usr/bin/env python3
"""Write a modelled air-quality reading for a point.

    python3 scripts/air_quality.py --place "Delhi, Delhi" --days 2
    python3 scripts/air_quality.py --lat 23.02 --lon 72.57 --variable pm2_5 --variable us_aqi

The values are CAMS modelled air quality at a coarse grid cell. An air-quality index is
the source's own index, not a health assessment, a risk score or an official warning, and
no health advice is produced. No ground monitor is connected.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.adapters import AIR_QUALITY, AIR_QUALITY_MODEL  # noqa: E402
from weathergpt_data.foundation import Foundation  # noqa: E402
from weathergpt_data.transport import SourceError  # noqa: E402


def resolve(place):
    from weathergpt_data.gazetteer import Gazetteer, preferred_match
    name, _, state = str(place).partition(',')
    matches = Gazetteer().search(name.strip(), state.strip())
    if not matches:
        raise SourceError('No indexed place matches: ' + str(place))
    chosen, why = preferred_match(matches)
    if chosen is None:
        raise SourceError('More than one place matches ' + str(place) + ' (' + why +
                          '). Add the state or district, or pass --lat and --lon.')
    return chosen


def markdown(result, variables, label):
    coverage = result['coverage']
    current = coverage.get('current') or {}
    instant = next((record['valid_time_utc'] for record in result['records']
                    if record['aggregation'] == 'current_instant'), None)
    lines = ['# Air quality — ' + str(label),
             '',
             'Source: **' + AIR_QUALITY_MODEL + '** · domain: ' + str(coverage.get('domain')) +
             ' · grid: ' + json.dumps(coverage.get('returned_grid')) + ' · time basis: ' + str(coverage.get('time_basis')),
             'Retrieved (UTC): ' + result['provenance']['retrieved_at_utc'],
             '']
    if current:
        lines.append('## Current reading' + (' — ' + str(instant) if instant else ''))
        for name in variables:
            value = current.get(name)
            lines.append('- ' + name + ': ' + ('unknown' if value is None else str(value) + ' ' + AIR_QUALITY[name][0]))
        lines.append('')
    lines.append('## Hourly window')
    for name in variables:
        values = [Decimal(str(record['value'])) for record in result['records']
                  if record['parameter'] == name and record['aggregation'] != 'current_instant'
                  and record['value'] is not None]
        unit = AIR_QUALITY[name][0]
        if values:
            lines.append('- ' + name + ': ' + str(min(values)) + ' to ' + str(max(values)) + ' ' + unit +
                         ' across ' + str(len(values)) + ' hourly values')
        else:
            lines.append('- ' + name + ': no value returned for the requested window')
    lines.append('')
    lines.append('## Limits')
    lines += ['- ' + note for note in result['limitations']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--place')
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lon', type=float)
    parser.add_argument('--variable', action='append', choices=sorted(AIR_QUALITY),
                        help='repeatable; defaults to every supported variable')
    parser.add_argument('--days', type=int, default=3)
    parser.add_argument('--output', type=Path)
    arguments = parser.parse_args()

    if arguments.place:
        chosen = resolve(arguments.place)
        latitude, longitude = chosen['coordinates']['latitude'], chosen['coordinates']['longitude']
        label = chosen.get('label') or arguments.place
    elif arguments.lat is not None and arguments.lon is not None:
        latitude, longitude, label = arguments.lat, arguments.lon, '%.4f, %.4f' % (arguments.lat, arguments.lon)
    else:
        raise SystemExit('Name a place with --place, or give both --lat and --lon.')

    variables = arguments.variable or sorted(AIR_QUALITY)
    result = Foundation().air_quality(latitude, longitude, days=arguments.days, variables=variables)
    now = datetime.now(timezone.utc)
    stamp = now.strftime('%Y-%m-%dT%H%M%SZ')
    output = arguments.output or ROOT / 'research' / 'implementation' / ('air-quality-' + now.strftime('%Y%m%d'))
    output.mkdir(parents=True, exist_ok=True)
    stem = 'air-quality-' + stamp
    (output / (stem + '.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (output / (stem + '.md')).write_text(markdown(result, variables, label), encoding='utf-8')

    print('air quality -> ' + str(output / (stem + '.md')))
    print('  status %s  grid %s  current %s' % (
        result['status'], json.dumps(result['coverage']['returned_grid']),
        json.dumps({name: result['coverage']['current'].get(name) for name in variables}, ensure_ascii=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
