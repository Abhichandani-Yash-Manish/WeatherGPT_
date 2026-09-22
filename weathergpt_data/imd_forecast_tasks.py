"""IMD's own multi-model forecast at a point (Mausamgram), and what it is not.

Every forecast this workspace served until now came from a global model through Open-Meteo. That
was not a choice about quality; it was what the fifteen credential-gated `api.imd.gov.in` products
left available. Mausamgram is IMD's own public multi-model output, it needs no key, and the source
registry had carried it as reachable-but-unconnected since 16 September while nothing used it.

What it is: a blend the publisher runs, three-hourly to 120 hours, on a 0.125 degree grid, carrying
temperature and a bias-corrected temperature, accumulated precipitation, humidity, cloud, solar
irradiance, and wind at 10, 80, 100 and 120 metres.

What it is not, and the answer says so:

- **not an observation.** It is model output, like every other forecast here.
- **not an IMD warning or bulletin.** The official warning path is the district warning product and
  the published bulletins; a number from this source never becomes either.
- **not independent of the global models.** A multi-model blend and a global model can share
  lineage, so agreement between them is not confirmation - the same rule the forecast crosscheck
  has always stated.
- **not stamped by the publisher in time.** The payload carries no time axis, so each sample's
  valid time is derived from the requested initialisation plus its step.
"""
from datetime import timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from .adapters import MAUSAMGRAM, MAUSAMGRAM_MODEL
from .answers import distance_km, serving_horizon
from .geography import identity
from .transport import SourceError, parsed, stamp

IST = ZoneInfo('Asia/Kolkata')
MAX_HOURS = 120
LABELS = {'temperature_2m': 'Temperature', 'temperature_2m_bias_corrected': 'Temperature (bias-corrected)',
          'precipitation': 'Precipitation', 'relative_humidity_2m': 'Relative humidity',
          'wind_speed_10m': 'Wind speed at 10 m', 'wind_direction_10m': 'Wind direction at 10 m',
          'wind_gusts_10m': 'Wind gusts at 10 m', 'cloud_cover': 'Cloud cover',
          'shortwave_radiation': 'Solar irradiance', 'wind_speed_80m': 'Wind speed at 80 m',
          'wind_speed_100m': 'Wind speed at 100 m', 'wind_speed_120m': 'Wind speed at 120 m',
          'wind_direction_80m': 'Wind direction at 80 m', 'wind_direction_100m': 'Wind direction at 100 m',
          'wind_direction_120m': 'Wind direction at 120 m'}
# What the planner may ask for, mapped to the publisher's own field names.
REQUESTED = {'temperature_2m': ['temp', 'temp_bc'], 'precipitation': ['apcp'],
             'relative_humidity_2m': ['rh'], 'wind_speed_10m': ['wspd', 'gust'],
             'wind_direction_10m': ['wdir'], 'cloud_cover': ['tcdc'], 'shortwave_radiation': ['ghi'],
             'wind_speed_80m': ['wspd80m'], 'wind_speed_100m': ['wspd100m'], 'wind_speed_120m': ['wspd120m']}


def render(result):
    facts = result.get('facts') or []
    if not facts:
        return 'No IMD Mausamgram forecast could be retrieved. ' + ' '.join((result.get('notes') or [])[:3])
    place = facts[0]['place']
    lines = [] if result.get('lead') else [place + ' · IMD Mausamgram multi-model forecast']
    groups = {}
    for fact in facts:
        groups.setdefault(fact['parameter'], []).append(fact)
    for parameter, rows in groups.items():
        values = [Decimal(row['value']) for row in rows]
        label = LABELS.get(parameter, parameter)
        if parameter == 'precipitation':
            lines.append(label + ': ' + str(sum(values)) + ' ' + rows[0]['unit'] + ' total across ' +
                         str(len(rows)) + ' three-hourly steps.')
        else:
            lines.append(label + ': ' + str(min(values)) + '–' + str(max(values)) + ' ' + rows[0]['unit'] +
                         ' across ' + str(len(rows)) + ' three-hourly steps.')
    lines.append('IMD multi-model output, not an observation and not an official IMD warning or bulletin.')
    lines.append('Exact steps, values and evidence IDs are in the tables below.')
    return '\n'.join(lines)


def execute_imd_forecast(engine, result, plan, task, resolved, coordinates):
    foundation = engine.workspace.foundation()
    asked = [name for name in (task.get('parameters') or []) if name in REQUESTED]
    fields = []
    for name in (asked or list(REQUESTED)):
        for field in REQUESTED[name]:
            if field not in fields:
                fields.append(field)
    now = engine.workspace.clock().astimezone(timezone.utc)
    if not plan.get('start_local') or not plan.get('end_local'):
        result.update(status='needs_clarification', answer='Which day or window should the IMD forecast cover?',
                      follow_up='A day or an ordered time window')
        return result
    start, end = parsed(plan['start_local']).astimezone(timezone.utc), parsed(plan['end_local']).astimezone(timezone.utc)
    if end <= start:
        raise SourceError('Use an ordered time window')
    if end - start > timedelta(hours=MAX_HOURS):
        asked_end = end
        end = start + timedelta(hours=MAX_HOURS)
        plan['end_local'] = end.astimezone(IST).isoformat()
        result.setdefault('notes', []).append(
            'Asked through ' + asked_end.astimezone(IST).strftime('%d %b %Y %H:%M') + ' IST, but this product runs ' +
            str(MAX_HOURS) + ' hours from its initialisation. What follows covers the part inside that and says '
            'nothing about the rest of the period asked about.')
    points = engine.resolve_points(result, plan, resolved, coordinates)
    if points is None:
        return result
    missing = []
    for place in points:
        try:
            data = foundation.mausamgram(place['coordinates']['latitude'], place['coordinates']['longitude'],
                                         variables=fields)
        except (SourceError, ValueError, OSError) as exc:
            missing.append(place['label'] + ': ' + str(exc))
            continue
        meta = data['provenance']
        coverage = data['coverage']
        citation = 'c-' + meta['sha256']
        cell = coverage.get('returned_grid')
        result['citations'].append({
            'id': citation, 'source_id': data['source_id'], 'provider': 'India Meteorological Department',
            'product': MAUSAMGRAM_MODEL, 'url': meta['url'], 'response_sha256': meta['sha256'],
            'retrieved_at_utc': meta['retrieved_at_utc'], 'requested_point': place['coordinates'],
            'returned_grid': cell,
            'grid_distance_km': round(distance_km(place['coordinates'], cell), 3) if cell else None,
            'model_run_time': coverage.get('initialisation_utc')})
        if place.get('citation'):
            result['citations'].append(place['citation'])
        result['trace']['tools'].append({'name': 'imd_mausamgram', 'fields': coverage.get('fields_returned'),
                                         'initialisation_utc': coverage.get('initialisation_utc'),
                                         'source_sha256': meta['sha256']})
        ahead = start if start > now else None
        expiry = serving_horizon(parsed(meta['retrieved_at_utc']), ahead)
        if result['expires_at_utc'] is None or expiry < parsed(result['expires_at_utc']):
            result['expires_at_utc'] = stamp(expiry)
        emitted = 0
        for record in data['records']:
            instant = parsed(record['valid_time_utc'])
            if not (start <= instant < end):
                continue
            if record['value'] is None:
                continue
            result['facts'].append({
                'id': 'f' + str(len(result['facts']) + 1), 'parameter': record['parameter'],
                'label': LABELS.get(record['parameter'], record['parameter']),
                'value': str(record['value']), 'unit': record['unit'], 'place': place['label'],
                'entity_id': place.get('selection_id') or identity(place['coordinates']),
                'start': instant.astimezone(IST).isoformat(),
                'end': (parsed(record['interval_end_utc']) if record.get('interval_end_utc') else instant).astimezone(IST).isoformat(),
                'source_id': data['source_id'], 'evidence_kind': 'imd_multi_model_forecast',
                'evidence_version': meta['sha256'], 'citation_ids': [citation],
                'source_locators': [record['source_locator']], 'method': record['aggregation']})
            emitted += 1
        if not emitted:
            missing.append(place['label'] + ': the requested window falls outside this run')
        elif cell:
            result['notes'].append(
                'Served from the IMD Mausamgram cell at ' + str(cell['latitude']) + ', ' + str(cell['longitude']) +
                ', ' + str(round(distance_km(place['coordinates'], cell), 1)) + ' km from the requested point: the '
                'publisher answers only on its own 0.125 degree grid.')
        result['notes'].append(
            'Initialisation ' + str(coverage.get('initialisation_utc')) + '; the valid time of each step is derived '
            'from that initialisation and the three-hour step, because the payload carries no time axis.')
    result['notes'] += missing
    for limitation in [
            'IMD Mausamgram is a multi-model blend published by IMD. It is model output, not an observation, '
            'and it is not an official IMD warning, nowcast or bulletin.',
            'A multi-model blend and a global model can share lineage, so agreement between this and the other '
            'forecast sources here is not independent confirmation.']:
        if limitation not in result['notes']:
            result['notes'].append(limitation)
    result['status'] = 'answered' if result['facts'] else 'unavailable'
    if result['facts'] and missing:
        result['status'] = 'partial'
    result['answer'] = render(result)
    return result
