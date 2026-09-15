#!/usr/bin/env python3
"""Measure which daily reanalysis variables each Open-Meteo archive model returns.

    python3 scripts/probe_reanalysis_catalogue.py

The archive API answers a variable a model does not carry with null rather than an
error, so "the field came back" is not the same as "the model supports it". This probe
asks every candidate variable of every governed model over one completed window and
records, per variable and model, whether the field is absent, entirely null, or carries
real values. The result is written next to the run as evidence and is what the adapter
catalogue is built from; it is not a substitute for reading the returned payload.

Read-only. One request per model plus the two long-record checks. No key is used.
"""
import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://archive-api.open-meteo.com/v1/archive'
POINT = (23.02579, 72.58727)
# One completed window where every governed model has data, so an all-null column means
# the model does not carry the variable rather than the variable not existing that day.
WINDOW = ('2025-07-01', '2025-07-03')
MODELS = ('era5', 'era5_land', 'era5_seamless')

CANDIDATES = (
    'precipitation_sum', 'rain_sum', 'precipitation_hours',
    'temperature_2m_mean', 'temperature_2m_max', 'temperature_2m_min',
    'apparent_temperature_mean',
    'relative_humidity_2m_mean', 'relative_humidity_2m_max', 'relative_humidity_2m_min',
    'dewpoint_2m_mean', 'surface_pressure_mean', 'cloud_cover_mean',
    'wind_speed_10m_max', 'wind_gusts_10m_max', 'wind_direction_10m_dominant',
    'shortwave_radiation_sum', 'et0_fao_evapotranspiration',
    'soil_moisture_0_to_7cm_mean', 'soil_temperature_0_to_7cm_mean',
)


def request(params):
    url = ENDPOINT + '?' + '&'.join('%s=%s' % (key, value) for key, value in params.items())
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.loads(response.read()), url


def fields(day):
    return {'latitude': POINT[0], 'longitude': POINT[1], 'start_date': day, 'end_date': day,
            'daily': ','.join(CANDIDATES), 'timezone': 'Asia/Kolkata'}


def classify(body):
    daily = body.get('daily') or {}
    units = body.get('daily_units') or {}
    report = {}
    for name in CANDIDATES:
        if name not in daily:
            report[name] = {'state': 'absent'}
            continue
        values = daily.get(name) or []
        present = [value for value in values if value is not None]
        report[name] = {'state': 'returned' if present else 'all_null', 'unit': units.get(name),
                        'values': len(values), 'non_null': len(present)}
    return report


def probe_model(model):
    params = fields(WINDOW[0])
    params.update(end_date=WINDOW[1], models=model, daily=','.join(CANDIDATES))
    try:
        body, url = request(params)
    except Exception as error:  # noqa: BLE001 - the probe reports what it saw
        return {'model': model, 'request': url, 'error': '%s: %s' % (type(error).__name__, str(error)[:200])}
    return {'model': model, 'request': url, 'timezone': body.get('timezone'),
            'window': WINDOW, 'fields': classify(body)}


def probe_record(model, day):
    params = {'latitude': POINT[0], 'longitude': POINT[1], 'start_date': day, 'end_date': day,
              'daily': 'temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean,'
                       'soil_moisture_0_to_7cm_mean', 'models': model, 'timezone': 'Asia/Kolkata'}
    try:
        body, url = request(params)
    except Exception as error:  # noqa: BLE001
        return {'model': model, 'date': day, 'error': '%s: %s' % (type(error).__name__, str(error)[:200])}
    daily = body.get('daily') or {}
    return {'model': model, 'date': day, 'request': url,
            'non_null': {name: sum(value is not None for value in (daily.get(name) or []))
                         for name in ('temperature_2m_mean', 'precipitation_sum',
                                      'relative_humidity_2m_mean', 'soil_moisture_0_to_7cm_mean')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', help='directory for the probe record')
    arguments = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = Path(arguments.output) if arguments.output else ROOT / 'research' / 'implementation' / ('reanalysis-depth-' + stamp[:8])
    output.mkdir(parents=True, exist_ok=True)

    report = {'schema_version': 'reanalysis-catalogue-probe-v1',
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'endpoint': ENDPOINT, 'point': {'latitude': POINT[0], 'longitude': POINT[1]},
              'candidates': list(CANDIDATES),
              'models': {model: probe_model(model) for model in MODELS},
              'long_record': [probe_record('era5', '1960-07-01'),
                              probe_record('era5_land', '1950-07-01')]}
    path = output / 'catalogue-probe.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('catalogue probe -> ' + str(path.relative_to(ROOT)))
    for model in MODELS:
        row = report['models'][model]
        if row.get('error'):
            print('  %-14s ERROR %s' % (model, row['error']))
            continue
        returned = [name for name in CANDIDATES if row['fields'][name]['state'] == 'returned']
        all_null = [name for name in CANDIDATES if row['fields'][name]['state'] == 'all_null']
        absent = [name for name in CANDIDATES if row['fields'][name]['state'] == 'absent']
        print('  %-14s returned %2d  all_null %2d  absent %2d' % (model, len(returned), len(all_null), len(absent)))
        if all_null:
            print('       all_null: ' + ', '.join(all_null))
        if absent:
            print('       absent:   ' + ', '.join(absent))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
