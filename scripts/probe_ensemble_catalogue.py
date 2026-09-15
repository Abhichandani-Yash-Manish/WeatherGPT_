#!/usr/bin/env python3
"""Measure the Open-Meteo ensemble surface before the adapter is built on it.

    python3 scripts/probe_ensemble_catalogue.py [--output DIR]

The ensemble endpoint requires a model id and rejects an unknown one, so the model ids
and member counts here are what the service returned, not what its documentation lists.
For each governed model the probe records the base variables, the perturbed-member
count per variable, the units, the returned grid, the time axis length and how many
member values are null. It also probes one stored mean/spread model id to record the
alternate route without using it. Read-only; no key.

Evidence for docs/62; not a forecast and not a skill measurement.
"""
import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://ensemble-api.open-meteo.com/v1/ensemble'
POINT = (23.02579, 72.58727)
VARIABLES = ('temperature_2m', 'precipitation', 'wind_speed_10m')
MODELS = ('gfs025', 'ecmwf_ifs025', 'icon_seamless')
MEAN_MODELS = ('dwd_icon_eps_ensemble_mean_seamless',)


def request(params):
    url = ENDPOINT + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read()), url


def classify(body, variables):
    hourly = body.get('hourly') or {}
    units = body.get('hourly_units') or {}
    report = {}
    for variable in variables:
        if variable not in hourly:
            report[variable] = {'state': 'absent'}
            continue
        members = sorted(name for name in hourly if name.startswith(variable + '_member'))
        values = [hourly[name] for name in members]
        nulls = sum(1 for column in values for value in column if value is None)
        report[variable] = {'state': 'returned', 'unit': units.get(variable),
                            'member_count': len(members), 'time_steps': len(hourly.get('time') or []),
                            'member_null_values': nulls}
    return report


def probe(model, **extra):
    params = {'latitude': POINT[0], 'longitude': POINT[1], 'timezone': 'UTC', 'timeformat': 'unixtime',
              'models': model, **extra}
    try:
        body, url = request(params)
    except Exception as error:  # noqa: BLE001 - the probe reports what it saw
        return {'model': model, 'error': '%s: %s' % (type(error).__name__, str(error)[:200])}
    hourly = body.get('hourly') or {}
    times = hourly.get('time') or []
    return {'model': model, 'url': url, 'utc_offset_seconds': body.get('utc_offset_seconds'),
            'timezone': body.get('timezone'), 'grid': {'latitude': body.get('latitude'),
            'longitude': body.get('longitude')}, 'first_time': times[:1], 'last_time': times[-1:],
            'fields': classify(body, VARIABLES)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output')
    arguments = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    output = Path(arguments.output) if arguments.output else ROOT / 'research' / 'implementation' / ('ensemble-spread-' + stamp)
    output.mkdir(parents=True, exist_ok=True)

    report = {'schema_version': 'ensemble-catalogue-probe-v1',
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'endpoint': ENDPOINT, 'point': {'latitude': POINT[0], 'longitude': POINT[1]},
              'variables': list(VARIABLES),
              'models': [probe(model, hourly=','.join(VARIABLES), forecast_days=1) for model in MODELS],
              'mean_route': [probe(model, hourly='temperature_2m,temperature_2m_spread', forecast_days=1)
                             for model in MEAN_MODELS],
              'invalid_model_control': probe('definitely_not_a_model', hourly='temperature_2m', forecast_days=1)}
    path = output / 'ensemble-probe.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('ensemble probe -> ' + str(path.relative_to(ROOT)))
    for row in report['models']:
        if row.get('error'):
            print('  %-16s ERROR %s' % (row['model'], row['error']))
            continue
        parts = ['%s=%s(%s)' % (name, value.get('member_count'), value.get('unit'))
                 for name, value in row['fields'].items() if value.get('state') == 'returned']
        print('  %-16s grid %s  %s' % (row['model'], row['grid'], ', '.join(parts)))
    control = report['invalid_model_control']
    print('  invalid model control: ' + ('rejected' if control.get('error') else 'ACCEPTED (bad)'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
