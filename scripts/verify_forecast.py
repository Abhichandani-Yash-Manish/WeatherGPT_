#!/usr/bin/env python3
"""Measure archived model runs against ERA5 reanalysis for a completed window.

    python3 scripts/verify_forecast.py --lat 23.02579 --lon 72.58727 --days 14
    python3 scripts/verify_forecast.py --place "New Delhi" --model ecmwf_ifs025 --variable precipitation

The forecast is an archived model run at a fixed lead-time offset; the reference is ERA5
reanalysis, a modelled analysis and not a station observation. The statistics describe this
sample for this model, variable and window. They are not operational skill, a confidence or
a risk, and no model is ranked against another. An output file is written as JSON and as a
Markdown table.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.adapters import PREVIOUS_RUNS, PREVIOUS_RUNS_MODELS  # noqa: E402
from weathergpt_data.foundation import Foundation  # noqa: E402
from weathergpt_data.transport import SourceError  # noqa: E402

COLUMNS = ('lead_days', 'n', 'bias', 'mae', 'rmse', 'correlation')


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


def markdown(result, label):
    forecast = result['forecast']
    reference = result['reference']
    lines = ['# Forecast verification — ' + str(label),
             '',
             'Model: **' + str(forecast.get('model')) + '** · forecast source: ' + str(forecast.get('source_id')) +
             ' · reference: ' + str(reference.get('source_id')) + ' ERA5 hourly reanalysis',
             'Window: ' + str(result['window']['start']) + ' to ' + str(result['window']['end']) +
             ' (UTC) · grid: ' + json.dumps(forecast.get('grid')),
             'Retrieved (UTC): ' + str(forecast.get('retrieved_at_utc')) + ' (forecast), ' +
             str(reference.get('retrieved_at_utc')) + ' (reference)',
             '',
             'Every figure describes the matched sample for this model, variable and window. It is not operational '
             'skill, a confidence or a risk, and no model is ranked against another.',
             '']
    for variable, rows in sorted((result.get('variables') or {}).items()):
        lines.append('## ' + variable)
        lines.append('| Lead (days) | Matched hours | Bias | MAE | RMSE | Correlation |')
        lines.append('|---|---|---|---|---|---|')
        for row in rows:
            if row['status'] != 'measured':
                lines.append('| %s | %d | unmeasured: %s | | | |' % (row['lead_days'], row['n'], row.get('reason', '')))
                continue
            lines.append('| %s | %s | %s | %s | %s | %s |' % (
                row['lead_days'], row['n'], row['bias'], row['mae'], row['rmse'],
                'undefined' if row['correlation'] is None else row['correlation']))
        lines.append('')
    lines.append('## Limits')
    lines += ['- ' + note for note in result.get('limits', [])]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--place')
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lon', type=float)
    parser.add_argument('--model', default='gfs_seamless', choices=list(PREVIOUS_RUNS_MODELS))
    parser.add_argument('--variable', action='append', choices=sorted(PREVIOUS_RUNS))
    parser.add_argument('--leads', default='1,2,3,5,7', help='comma-separated lead times from 1 to 7')
    parser.add_argument('--start', help='first completed date (YYYY-MM-DD)')
    parser.add_argument('--end', help='last completed date (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=14, help='window length ending six days ago when --start/--end are absent')
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

    today = datetime.now(timezone.utc).date()
    end = arguments.end or (today - timedelta(days=6)).isoformat()
    start = arguments.start or (datetime.fromisoformat(end).date() - timedelta(days=arguments.days - 1)).isoformat()
    leads = [int(value) for value in arguments.leads.split(',') if value.strip()]
    variables = arguments.variable or sorted(PREVIOUS_RUNS)
    result = Foundation().verification(latitude, longitude, start, end, model=arguments.model,
                                       variables=variables, leads=leads)
    now = datetime.now(timezone.utc)
    stamp = now.strftime('%Y-%m-%dT%H%M%SZ')
    output = arguments.output or ROOT / 'research' / 'implementation' / ('forecast-verification-' + now.strftime('%Y%m%d'))
    output.mkdir(parents=True, exist_ok=True)
    stem = 'verification-' + arguments.model + '-' + stamp
    (output / (stem + '.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (output / (stem + '.md')).write_text(markdown(result, label), encoding='utf-8')

    print('verification -> ' + str(output / (stem + '.md')))
    print('  model %s  window %s..%s  grid %s' % (arguments.model, start, end, json.dumps(result['forecast'].get('grid'))))
    for variable, rows in sorted(result.get('variables', {}).items()):
        print('  %s: ' % variable + ', '.join(
            'day%s n=%s mae=%s' % (row['lead_days'], row['n'], row.get('mae', '-')) for row in rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
