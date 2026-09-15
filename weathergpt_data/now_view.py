"""The right-now reading: what is observed, what is published, and what is forecast next.

Three connected products, kept apart on purpose:

  observed   what a station in the METAR or AWS layer reported, with its own instant, age and
             distance. A station describes itself, not a district, and not the future.
  in force   what the official district warning product publishes for today, with the bulletin
             identity it was read from. A quiet day in one product is not an all-clear.
  next hours model output for the grid cell, hour by hour, each value with its window and source.

Radar and satellite imagery, sub-hourly refresh between source hours, and any push or
notification are not connected, and the reading says so where they would otherwise be implied.
"""
from datetime import timedelta
from zoneinfo import ZoneInfo

from .transport import SourceError, parsed, stamp, utcnow

IST = ZoneInfo('Asia/Kolkata')
SCHEMA = 'now-v1'
NEXT_HOURS = 6
NOT_CONNECTED = ('radar and satellite imagery', 'sub-hourly refresh between source hours',
                 'any push or notification: this workspace answers when it is asked')
NOT_ESTABLISHED = [
    'A station report is one station at one instant: it is not a district average, not a field reading and not a forecast.',
    'A quiet day in the official district product is not an all-clear, and it says nothing about hazards that product does not carry.',
    'Model hours are grid-cell output, not observations, and no skill or impact is claimed for them.',
    'The CAP relay and the sea-area, coastal, radar and satellite products are not part of this reading.',
]


def _day_rows(view):
    return ((view or {}).get('data') or {}).get('days') or []


def day_state(warning_view, now=None):
    """The published day that contains this instant, or the first row the product lists."""
    rows = _day_rows(warning_view)
    if not rows:
        return None
    moment = now or utcnow()
    chosen = None
    for row in rows:
        try:
            if parsed(row['starts_utc']) <= moment < parsed(row['ends_utc']):
                chosen = row
                break
        except (KeyError, TypeError, ValueError):
            continue
    if chosen is None:
        chosen = next((row for row in rows if row.get('is_today')), rows[0])
    data = (warning_view or {}).get('data') or {}
    source_ids = [item.get('source_id') for item in (warning_view or {}).get('sources') or [] if isinstance(item, dict)]
    quiet = bool(chosen.get('quiet'))
    colour = str(chosen.get('colour') or '').lower()
    hazards = [str(item) for item in (chosen.get('hazards') or [])]
    status_line = ('No warning in this product for this district-day (' + (colour or 'colour not supplied') + ').'
                   if quiet else ('Official district warning: ' + (colour or 'colour not supplied') +
                                  ((' - ' + ', '.join(hazards)) if hazards else '')))
    return {'district': data.get('district'), 'state': data.get('state'), 'day': chosen.get('day'),
            'day_label': chosen.get('label'), 'starts_utc': chosen.get('starts_utc'), 'ends_utc': chosen.get('ends_utc'),
            'colour': colour or None, 'colour_code': chosen.get('colour_code'), 'hazards': hazards, 'quiet': quiet,
            'status_line': status_line, 'wording': chosen.get('source_text'),
            'issued_at_utc': data.get('issued_at_utc'), 'source_id': source_ids[0] if source_ids else None,
            'source_locator': data.get('source_locator')}


def next_hours(forecast_view, hours=NEXT_HOURS, now=None):
    """The next source hours as returned, one row per hour, with the values the product holds."""
    data = (forecast_view or {}).get('data') or {}
    parameters = data.get('parameters') or {}
    moment = now or utcnow()
    series = {}
    for name, entry in parameters.items():
        rows = []
        for point in (entry or {}).get('points') or []:
            try:
                at = parsed(point['t'])
            except (KeyError, TypeError, ValueError):
                continue
            if at < moment.astimezone(at.tzinfo) - timedelta(hours=1):
                continue
            rows.append((at, point.get('v')))
        rows.sort(key=lambda item: item[0])
        series[name] = rows[:hours]
    times = sorted({at for rows in series.values() for at, _ in rows})[:hours]
    wanted = ('temperature_2m', 'precipitation_probability', 'precipitation', 'wind_speed_10m')
    made = []
    for at in times:
        row = {'at': stamp(at)}
        for name in wanted:
            value = next((value for moment_at, value in series.get(name, []) if moment_at == at), None)
            if value is not None:
                row[name] = value
        made.append(row)
    source_ids = [item.get('source_id') for item in (forecast_view or {}).get('sources') or [] if isinstance(item, dict)]
    return {'status': 'ok' if made else 'unavailable', 'rows': made,
            'starts': made[0]['at'] if made else None, 'ends': made[-1]['at'] if made else None,
            'source_id': source_ids[0] if source_ids else None,
            'model': next((str((entry or {}).get('model')) for entry in parameters.values() if (entry or {}).get('model')), None),
            'unit': {name: (parameters.get(name) or {}).get('unit') for name in wanted if parameters.get(name)}}


def observed_stations(bundle, limit=2):
    rows = []
    for kind, stations in ((bundle or {}).get('data') or {}).get('networks', {}).items():
        for station in stations or []:
            rows.append(dict(station, network=kind))
    # A station's own age matters more than a kilometre: an AWS row from March sat 29 km away
    # and led the answer, while the fresh METAR 40 km away was mentioned second. Fresh stations
    # (three hours or less) lead; the distance order decides within each group.
    def freshness(row):
        age = row.get('age_minutes')
        return 0 if (age is not None and age <= 180) else 1
    rows.sort(key=lambda row: (freshness(row), row.get('distance_km') if row.get('distance_km') is not None else 1e9))
    return rows[:limit], len(rows)


def compose(foundation, latitude, longitude, hours=NEXT_HOURS, now=None, refresh=False, label=None):
    """The reading itself: three products, each with its own status, source and limits."""
    from . import product_api
    moment = now or utcnow()
    reading = {'schema_version': SCHEMA, 'generated_at_utc': stamp(moment),
               'point': {'latitude': latitude, 'longitude': longitude, 'label': label},
               'observed': {'status': 'unavailable', 'stations': [], 'rows_in_radius': 0, 'sources': []},
               'in_force': {'status': 'unavailable'}, 'next_hours': {'status': 'unavailable', 'rows': []},
               'sources': [], 'source_entries': [], 'not_connected': list(NOT_CONNECTED), 'not_established': list(NOT_ESTABLISHED),
               'limitations': []}
    try:
        bundle = product_api.observations_bundle(foundation, latitude, longitude, limit=3)
        stations, total = observed_stations(bundle)
        reading['observed'] = {'status': 'ok' if stations else 'unavailable', 'stations': stations,
                               'rows_in_radius': total,
                               'sources': [item.get('source_id') for item in bundle.get('sources') or [] if isinstance(item, dict)],
                               'coverage': bundle.get('coverage'), 'limitations': bundle.get('limitations')}
        reading['limitations'] += [note for note in bundle.get('limitations') or [] if note not in reading['limitations']]
        reading['source_entries'] += [item for item in bundle.get('sources') or [] if isinstance(item, dict)]
    except (SourceError, ValueError, OSError) as failure:
        reading['observed']['why'] = str(failure)[:200]
    try:
        warning = product_api.warnings_place(foundation, latitude, longitude, refresh=refresh)
        day = day_state(warning, now=moment)
        reading['in_force'] = dict(day or {}, status='ok' if day else 'unavailable')
        reading['sources'] += [item for item in [reading['in_force'].get('source_id')] if item]
        reading['limitations'] += [note for note in warning.get('limitations') or [] if note not in reading['limitations']]
        reading['source_entries'] += [item for item in warning.get('sources') or [] if isinstance(item, dict)]
    except (SourceError, ValueError, OSError) as failure:
        reading['in_force'] = {'status': 'unavailable', 'why': str(failure)[:200]}
    try:
        forecast = product_api.forecast(foundation, latitude, longitude, days=1, refresh=refresh)
        hours_view = next_hours(forecast, hours=hours, now=moment)
        reading['next_hours'] = dict(hours_view, status='ok' if hours_view.get('rows') else 'unavailable')
        reading['sources'] += [item for item in [hours_view.get('source_id')] if item]
        reading['source_entries'] += [item for item in forecast.get('sources') or [] if isinstance(item, dict)]
    except (SourceError, ValueError, OSError) as failure:
        reading['next_hours'] = {'status': 'unavailable', 'why': str(failure)[:200], 'rows': []}
    for part in ('observed', 'in_force', 'next_hours'):
        reading['sources'] += [item for item in reading[part].get('sources') or [] if item not in reading['sources']]
    reading['sources'] = list(dict.fromkeys(reading['sources']))
    # One entry per source: the same product can appear in more than one part of the reading,
    # and a reader should not be shown the same source twice.
    unique, seen = [], set()
    for item in reading['source_entries']:
        key = item.get('source_id')
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    reading['source_entries'] = unique
    reading['sources'] = [item.get('source_id') for item in unique] or reading['sources']
    reading['status'] = 'ok' if any(reading[part].get('status') == 'ok' for part in ('observed', 'in_force', 'next_hours')) else 'unavailable'
    reading['summary'] = summary(reading)
    return reading


def summary(reading):
    """One paragraph a reader can quote, with each part's own status and source."""
    lines = []
    stations = (reading.get('observed') or {}).get('stations') or []
    if stations:
        lead = stations[0]
        lead_age = lead.get('age_minutes')
        lines.append('Freshest station report here: ' + str(lead.get('name') or lead.get('station_code')) +
                     (', ' + str(round(float(lead['distance_km']), 2)) + ' km away' if lead.get('distance_km') is not None else '') +
                     ', reported ' + str(lead.get('observed_at_utc')) +
                     (', ' + str(lead_age) + ' minutes before retrieval' if lead_age is not None else '') + '.')
        def minutes(station):
            value = station.get('age_minutes')
            return value if value is not None else 10 ** 9
        nearest = min(stations, key=lambda station: station.get('distance_km') if station.get('distance_km') is not None else 1e9)
        if nearest is not lead:
            lines.append('The nearest station (' + str(nearest.get('name') or nearest.get('station_code')) +
                         (' at ' + str(round(float(nearest['distance_km']), 2)) + ' km' if nearest.get('distance_km') is not None else '') +
                         ') reported ' + str(minutes(nearest)) + ' minutes before retrieval, so the fresher report leads.')
        if minutes(lead) > 180:
            lines.append('No station within range reported in the last three hours: the freshest report available is ' +
                         str(minutes(lead)) + ' minutes old, and it is shown as that, not as now.')
    else:
        lines.append('No station in the connected layers reported within 150 km, which is an absence of station evidence here, not a statement that nothing is happening.')
    day = reading.get('in_force') or {}
    if day.get('status') == 'ok':
        lines.append('Official district product for ' + str(day.get('district') or 'this point') + ': ' + str(day.get('status_line')) +
                     ' (issued ' + str(day.get('issued_at_utc')) + ').')
    else:
        lines.append('The official district product could not be read for this point: ' + str(day.get('why') or 'no day matched') + '.')
    hours = (reading.get('next_hours') or {}).get('rows') or []
    if hours:
        lines.append('Model hours next, ' + str((reading['next_hours'] or {}).get('starts')) + ' to ' +
                     str((reading['next_hours'] or {}).get('ends')) + ': ' + '; '.join(
                         str(row['at']) + ((' ' + str(row['temperature_2m']) + ' °C') if row.get('temperature_2m') is not None else '') +
                         (', rain chance ' + str(row['precipitation_probability']) + '%' if row.get('precipitation_probability') is not None else '')
                         for row in hours) + '.')
    lines.append('Not connected here: ' + '; '.join(NOT_CONNECTED) + '.')
    return ' '.join(lines)
