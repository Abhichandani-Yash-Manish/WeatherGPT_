#!/usr/bin/env python3
"""Measure the two sources a forecast verification needs, before the adapter is built.

    python3 scripts/probe_verification_sources.py [--output DIR]

The forecast side is the Open-Meteo Previous Runs API, which returns a variable at fixed
lead-time offsets (``_previous_dayN``). The reference side is ERA5 hourly reanalysis,
already registered as S22. The probe records the lead-time columns, their units, a date
range beyond the 92-day past window, the accepted model ids, and two negative controls
(a daily aggregation on the previous-runs endpoint, and a lead time beyond day 7). It
also records an ERA5 hourly window. Read-only; no key.

Evidence for docs/80; reanalysis is not an observation and this is not a skill score.
"""
import argparse
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORECAST_ENDPOINT = 'https://previous-runs-api.open-meteo.com/v1/forecast'
REFERENCE_ENDPOINT = 'https://archive-api.open-meteo.com/v1/archive'
POINT = (23.02579, 72.58727)
VARIABLES = ('temperature_2m', 'precipitation')
LEADS = (1, 2, 3, 5, 7)
MODELS = ('gfs_seamless', 'ecmwf_ifs025', 'best_match')
# A completed window with a five-day reanalysis delay already past.
WINDOW = ('2026-08-01', '2026-08-07')


def request(url, params):
    full = url + '?' + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(full, timeout=60) as response:
            return json.loads(response.read()), full, None
    except Exception as error:  # noqa: BLE001 - the probe records what it saw
        reason = ''
        if hasattr(error, 'read'):
            try:
                reason = error.read().decode('utf-8', 'replace')[:200]
            except Exception:
                reason = ''
        return None, full, '%s: %s %s' % (type(error).__name__, str(error)[:120], reason)


def base():
    return {'latitude': POINT[0], 'longitude': POINT[1], 'timezone': 'UTC', 'timeformat': 'unixtime'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output')
    arguments = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%d')
    output = Path(arguments.output) if arguments.output else ROOT / 'research' / 'implementation' / ('forecast-verification-' + stamp)
    output.mkdir(parents=True, exist_ok=True)

    report = {'schema_version': 'verification-source-probe-v1',
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'forecast_endpoint': FORECAST_ENDPOINT, 'reference_endpoint': REFERENCE_ENDPOINT,
              'point': {'latitude': POINT[0], 'longitude': POINT[1]},
              'variables': list(VARIABLES), 'leads': list(LEADS), 'window': list(WINDOW)}

    columns = [variable + '_previous_day%d' % lead for variable in VARIABLES for lead in LEADS]
    body, url, error = request(FORECAST_ENDPOINT, {**base(), 'hourly': ','.join(VARIABLES + tuple(columns)),
                                                   'start_date': WINDOW[0], 'end_date': WINDOW[1],
                                                   'models': 'gfs_seamless'})
    report['forecast'] = {'url': url, 'error': error}
    if body:
        hourly = body.get('hourly') or {}
        units = body.get('hourly_units') or {}
        times = hourly.get('time') or []
        report['forecast'].update({
            'utc_offset_seconds': body.get('utc_offset_seconds'), 'grid': {'latitude': body.get('latitude'),
            'longitude': body.get('longitude')}, 'hours': len(times),
            'first_time_utc': datetime.fromtimestamp(times[0], timezone.utc).isoformat() if times else None,
            'units': {name: units.get(name) for name in VARIABLES},
            'lead_columns': {name: (name in hourly) for name in columns},
            'non_null': {name: sum(value is not None for value in (hourly.get(name) or [])) for name in columns}})
    daily_body, daily_url, daily_error = request(FORECAST_ENDPOINT, {**base(), 'models': 'gfs_seamless',
        'daily': 'temperature_2m_max_previous_day1', 'past_days': 5})
    report['daily_rejected'] = {'url': daily_url, 'error': daily_error}
    # The service accepts a lead beyond day 7 and answers it with null rather than an error, so
    # the adapter must cap the lead set itself and treat an all-null lead as unmeasured.
    lead8_body, lead8_url, lead8_error = request(FORECAST_ENDPOINT, {**base(), 'models': 'gfs_seamless',
        'hourly': 'temperature_2m_previous_day7,temperature_2m_previous_day8', 'past_days': 3})
    lead8_hourly = (lead8_body or {}).get('hourly') or {}
    report['lead_beyond_7'] = {'url': lead8_url, 'error': lead8_error,
        'day7_non_null': sum(value is not None for value in (lead8_hourly.get('temperature_2m_previous_day7') or [])),
        'day8_non_null': sum(value is not None for value in (lead8_hourly.get('temperature_2m_previous_day8') or [])),
        'note': 'The service accepts a lead beyond day 7 and returns nulls, not an error.'}
    report['models'] = {}
    for model in MODELS:
        probe_body, probe_url, probe_error = request(FORECAST_ENDPOINT, {**base(), 'models': model,
            'hourly': 'temperature_2m_previous_day1', 'past_days': 2})
        report['models'][model] = {'url': probe_url, 'error': probe_error,
            'hours': len(((probe_body or {}).get('hourly') or {}).get('time') or []) if probe_body else None}
    reference_body, reference_url, reference_error = request(REFERENCE_ENDPOINT, {**base(),
        'hourly': ','.join(VARIABLES), 'models': 'era5', 'start_date': WINDOW[0], 'end_date': WINDOW[1]})
    report['reference'] = {'url': reference_url, 'error': reference_error}
    if reference_body:
        hourly = reference_body.get('hourly') or {}
        report['reference'].update({'hours': len(hourly.get('time') or []),
                                    'units': {name: (reference_body.get('hourly_units') or {}).get(name) for name in VARIABLES},
                                    'non_null': {name: sum(value is not None for value in (hourly.get(name) or [])) for name in VARIABLES}})
    path = output / 'verification-source-probe.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('verification source probe -> ' + str(path.relative_to(ROOT)))
    forecast = report['forecast']
    if forecast.get('error'):
        print('  forecast ERROR ' + forecast['error'])
    else:
        print('  forecast hours %s grid %s units %s' % (forecast['hours'], forecast['grid'], forecast['units']))
        missing = [name for name, present in forecast['lead_columns'].items() if not present]
        print('  lead columns present: %s' % ('all' if not missing else 'missing ' + ', '.join(missing)))
    print('  daily on previous-runs: %s' % ('rejected' if report['daily_rejected']['error'] else 'ACCEPTED (bad)'))
    beyond = report['lead_beyond_7']
    print('  lead day 7 non-null %s; lead day 8 accepted but non-null %s (the adapter caps the lead set)'
          % (beyond['day7_non_null'], beyond['day8_non_null']))
    print('  models: ' + ', '.join('%s=%s' % (name, 'ok' if not row['error'] else 'error') for name, row in report['models'].items()))
    print('  reference: %s' % (report['reference'].get('error') or 'hours %s' % report['reference']['hours']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
