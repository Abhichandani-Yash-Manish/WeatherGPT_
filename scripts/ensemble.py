#!/usr/bin/env python3
"""Write the member spread of one ensemble model for a point.

    python3 scripts/ensemble.py --place "Ahmedabad, Gujarat" --model gfs025 --days 2
    python3 scripts/ensemble.py --lat 23.02 --lon 72.57 --variable precipitation --threshold 1

The spread, the range and the percentiles are properties of the returned ensemble members,
computed here and disclosed. They are not a probability, a confidence, a risk or a skill
score, and a member exceedance count is a frequency over members that are not independent.
Modelled grid values are not local measurements.
"""
import argparse
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.adapters import ENSEMBLE, ENSEMBLE_MODELS  # noqa: E402
from weathergpt_data.foundation import Foundation  # noqa: E402
from weathergpt_data.transport import SourceError  # noqa: E402

STATISTICS = ('mean', 'spread', 'min', 'max', 'p10', 'p50', 'p90')


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


def series(result, variable):
    return {statistic: [record for record in result['records']
                        if record['parameter'] == variable + '_' + statistic] for statistic in STATISTICS}


def markdown(result, variables, label, threshold):
    coverage = result['coverage']
    lines = ['# Ensemble spread — ' + str(label),
             '',
             'Model: **' + coverage['model'] + '** · members: ' +
             ', '.join('%s %d' % (name, count) for name, count in coverage['member_total'].items()) +
             ' · grid: ' + json.dumps(coverage['returned_grid']) + ' · time basis: ' + coverage['time_basis'],
             'Retrieved (UTC): ' + result['provenance']['retrieved_at_utc'],
             '']
    for variable in variables:
        rows = series(result, variable)
        unit = (rows['mean'][0]['unit'] if rows['mean'] else '')
        means = [record['value'] for record in rows['mean'] if record['value'] is not None]
        spreads = [record['value'] for record in rows['spread'] if record['value'] is not None]
        lines.append('## ' + variable + ' (' + unit + ')')
        if means:
            lines.append('- Mean across hours: ' + min(means, key=Decimal) + ' to ' + max(means, key=Decimal) + ' ' + unit)
        if spreads:
            lines.append('- Member spread across hours: up to ' + max(spreads, key=Decimal) + ' ' + unit +
                         ' (population standard deviation)')
        sample = next((record for record in rows['p50'] if record['value'] is not None), None)
        if sample is not None:
            index = rows['p50'].index(sample)
            values = {statistic: rows[statistic][index]['value'] for statistic in STATISTICS}
            lines.append('- At ' + sample['valid_time_utc'] + ': mean ' + str(values['mean']) +
                         ', spread ' + str(values['spread']) + ', min ' + str(values['min']) +
                         ', max ' + str(values['max']) + ', p10 ' + str(values['p10']) +
                         ', p50 ' + str(values['p50']) + ', p90 ' + str(values['p90']) +
                         ' across ' + str(sample['member_count']) + ' members')
        if threshold is not None and variable == 'precipitation':
            fractions = [record for record in result['records'] if record['parameter'] == 'precipitation_exceedance']
            shown = [record for record in fractions if record['value'] is not None]
            if shown:
                best = max(shown, key=lambda record: str(record['value']))
                lines.append('- Members at or above ' + str(threshold) + ' mm: ' + str(best.get('exceedance_count')) +
                             ' of ' + str(best['member_count']) + ' at ' + best['valid_time_utc'] +
                             ' (a member frequency, not a probability)')
        lines.append('')
    lines.append('## Limits')
    lines += ['- ' + note for note in result['limitations']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--place')
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lon', type=float)
    parser.add_argument('--model', default='gfs025', choices=list(ENSEMBLE_MODELS))
    parser.add_argument('--variable', action='append', choices=sorted(ENSEMBLE),
                        help='repeatable; defaults to every supported variable')
    parser.add_argument('--days', type=int, default=2)
    parser.add_argument('--threshold', type=float, default=None,
                        help='precipitation threshold in mm for a member exceedance count')
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

    variables = arguments.variable or sorted(ENSEMBLE)
    result = Foundation().ensemble(latitude, longitude, days=arguments.days, model=arguments.model,
                                   variables=variables, threshold=arguments.threshold)
    now = datetime.now(timezone.utc)
    stamp = now.strftime('%Y-%m-%dT%H%M%SZ')
    output = arguments.output or ROOT / 'research' / 'implementation' / ('ensemble-spread-' + now.strftime('%Y%m%d'))
    output.mkdir(parents=True, exist_ok=True)
    stem = arguments.model + '-' + stamp
    (output / (stem + '.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (output / (stem + '.md')).write_text(markdown(result, variables, label, arguments.threshold), encoding='utf-8')

    print('ensemble -> ' + str(output / (stem + '.md')))
    print('  status %s  model %s  members %s  grid %s' % (
        result['status'], result['coverage']['model'], result['coverage']['member_total'],
        json.dumps(result['coverage']['returned_grid'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
