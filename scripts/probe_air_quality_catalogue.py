#!/usr/bin/env python3
"""Measure the Open-Meteo air-quality surface before the adapter is built on it.

    python3 scripts/probe_air_quality_catalogue.py [--output DIR]

The catalogue, the units, the domain, the hourly axis and the current block are recorded
from what the service returned, and three negative controls pin what it rejects: a daily
aggregation, a forecast beyond seven days, and an unknown variable. Read-only; no key.

Evidence for docs/69; not a health assessment and not a monitor measurement.
"""
import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://air-quality-api.open-meteo.com/v1/air-quality'
POINT = (23.02579, 72.58727)
CATALOGUE = ('pm2_5', 'pm10', 'nitrogen_dioxide', 'ozone', 'carbon_monoxide',
             'sulphur_dioxide', 'us_aqi', 'european_aqi')
EXCLUDED = ('carbon_dioxide', 'ammonia', 'grass_pollen', 'uv_index')


def request(params):
    url = ENDPOINT + '?' + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return json.loads(response.read()), url, None
    except Exception as error:  # noqa: BLE001 - the probe records what it saw
        reason = ''
        if hasattr(error, 'read'):
            try:
                reason = error.read().decode('utf-8', 'replace')[:200]
            except Exception:
                reason = ''
        return None, url, '%s: %s %s' % (type(error).__name__, str(error)[:120], reason)


def base():
    return {'latitude': POINT[0], 'longitude': POINT[1], 'timezone': 'UTC', 'timeformat': 'unixtime'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output')
    arguments = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    output = Path(arguments.output) if arguments.output else ROOT / 'research' / 'implementation' / ('air-quality-' + stamp)
    output.mkdir(parents=True, exist_ok=True)

    report = {'schema_version': 'air-quality-catalogue-probe-v1',
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'endpoint': ENDPOINT, 'point': {'latitude': POINT[0], 'longitude': POINT[1]},
              'catalogue': list(CATALOGUE), 'excluded': list(EXCLUDED)}

    body, url, error = request({**base(), 'hourly': ','.join(CATALOGUE + EXCLUDED),
                                'current': 'pm2_5,pm10,us_aqi', 'forecast_days': 1})
    report['hourly'] = {'url': url, 'error': error}
    if body:
        hourly = body.get('hourly') or {}
        report['hourly'].update({
            'utc_offset_seconds': body.get('utc_offset_seconds'), 'timezone': body.get('timezone'),
            'grid': {'latitude': body.get('latitude'), 'longitude': body.get('longitude')},
            'time_steps': len(hourly.get('time') or []),
            'first_time': (hourly.get('time') or [None])[0],
            'units': {name: value for name, value in (body.get('hourly_units') or {}).items() if name != 'time'},
            'returned': [name for name in CATALOGUE + EXCLUDED if name in hourly],
            'current': body.get('current'), 'current_units': body.get('current_units')})
    for label, params in (('daily_rejected', {'daily': 'pm2_5_max'}),
                          ('forecast_days_7', {'hourly': 'pm2_5', 'forecast_days': 7}),
                          ('forecast_days_10_rejected', {'hourly': 'pm2_5', 'forecast_days': 10}),
                          ('unknown_variable_rejected', {'hourly': 'not_a_pollutant'})):
        probe_body, probe_url, probe_error = request({**base(), **params})
        report[label] = {'url': probe_url, 'error': probe_error,
                         'time_steps': len(((probe_body or {}).get('hourly') or {}).get('time') or []) if probe_body else None}
    path = output / 'air-quality-probe.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('air-quality probe -> ' + str(path.relative_to(ROOT)))
    hourly = report['hourly']
    if hourly.get('error'):
        print('  hourly ERROR ' + hourly['error'])
    else:
        print('  grid %s  steps %s  returned %s' % (hourly['grid'], hourly['time_steps'], hourly['returned']))
        print('  units ' + json.dumps(hourly['units'], ensure_ascii=False))
        print('  current ' + json.dumps(hourly['current'], ensure_ascii=False))
    for label in ('daily_rejected', 'forecast_days_7', 'forecast_days_10_rejected', 'unknown_variable_rejected'):
        print('  %-26s %s' % (label, 'rejected' if report[label]['error'] else 'accepted (steps %s)' % report[label]['time_steps']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
