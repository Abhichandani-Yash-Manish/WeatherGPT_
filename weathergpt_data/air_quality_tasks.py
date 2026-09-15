"""Air-quality answers: modelled pollutants and the source's own index, never a health call.

The concentrations are CAMS modelled output at a coarse grid cell, not a monitor
measurement. An air-quality index is the source's own index, not a health assessment, a
risk score or an official air-quality warning, and no health advice is produced. The
current hour the provider reports is kept apart from the requested hourly window.
"""
from datetime import timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from .adapters import AIR_QUALITY, AIR_QUALITY_MODEL
from .answers import distance_km
from .geography import identity
from .transport import SourceError, parsed, stamp

IST = ZoneInfo('Asia/Kolkata')
MAX_HOURS = 48
LABELS = {'pm2_5': 'PM2.5 concentration', 'pm10': 'PM10 concentration',
          'nitrogen_dioxide': 'Nitrogen dioxide concentration', 'ozone': 'Ozone concentration',
          'carbon_monoxide': 'Carbon monoxide concentration', 'sulphur_dioxide': 'Sulphur dioxide concentration',
          'us_aqi': 'US AQI (source index)', 'european_aqi': 'European AQI (source index)'}


def render(result):
    facts = result.get('facts') or []
    if not facts:
        return 'No verified air-quality data could be retrieved. ' + ' '.join(result.get('notes', [])[:3])
    place = facts[0]['place']
    lines = []
    current = [fact for fact in facts if fact['parameter'].endswith('_current')]
    if current:
        lines.append(place + ' · provider current hour ' + current[0]['start'][:16].replace('T', ' ') + ' IST')
        lines.append('; '.join(LABELS.get(fact['parameter'][:-len('_current')], fact['parameter']) + ' ' +
                               str(fact['value']) + ' ' + fact['unit'] for fact in current) + '.')
    groups = {}
    for fact in facts:
        if fact['parameter'].endswith('_current'):
            continue
        groups.setdefault(fact['parameter'], []).append(fact)
    for parameter, rows in groups.items():
        values = [Decimal(fact['value']) for fact in rows]
        lines.append(place + ' · ' + LABELS.get(parameter, parameter) + ': ' + str(min(values)) + '–' +
                     str(max(values)) + ' ' + rows[0]['unit'] + ' across ' + str(len(rows)) + ' hourly values.')
    lines.append('Exact hours, values and evidence IDs are in the tables below.')
    return '\n'.join(lines)


def execute_air_quality(engine, result, plan, task, resolved, coordinates):
    foundation = engine.workspace.foundation()
    variables = [name for name in (task.get('parameters') or []) if name in AIR_QUALITY] or list(AIR_QUALITY)
    now = engine.workspace.clock().astimezone(timezone.utc)
    if not plan.get('start_local') or not plan.get('end_local'):
        result.update(status='needs_clarification', answer='Which day or window should the air quality cover?',
                      follow_up='A day or an ordered time window'); return result
    start, end = parsed(plan['start_local']).astimezone(timezone.utc), parsed(plan['end_local']).astimezone(timezone.utc)
    if end <= start or end - start > timedelta(hours=MAX_HOURS):
        raise SourceError('Air-quality detail supports up to %d hours per task; please narrow the window' % MAX_HOURS)
    days = max(1, min(7, (end.date() - now.date()).days + 1))
    points = engine.resolve_points(result, plan, resolved, coordinates)
    if points is None:
        return result
    result.update(charts=[], calculations=[], air_quality=True)
    missing = []
    for place in points:
        try:
            data = foundation.air_quality(place['coordinates']['latitude'], place['coordinates']['longitude'],
                                          days=days, variables=variables)
        except (ValueError, OSError) as exc:
            missing.append(place['label'] + ': ' + str(exc)); continue
        meta = data['provenance']; coverage = data['coverage']; citation = 'c-' + meta['sha256']
        result['citations'].append({
            'id': citation, 'source_id': data['source_id'], 'provider': 'Open-Meteo',
            'product': AIR_QUALITY_MODEL + ' air quality',
            'url': meta['url'], 'response_sha256': meta['sha256'], 'retrieved_at_utc': meta['retrieved_at_utc'],
            'requested_point': place['coordinates'], 'returned_grid': coverage['returned_grid'],
            'grid_distance_km': round(distance_km(place['coordinates'], coverage['returned_grid']), 3),
            'model_run_time': None})
        if place.get('citation'):
            result['citations'].append(place['citation'])
        expiry = min(parsed(meta['retrieved_at_utc']) + timedelta(hours=1), start)
        if result['expires_at_utc'] is None or expiry < parsed(result['expires_at_utc']):
            result['expires_at_utc'] = stamp(expiry)
        result['trace']['tools'].append({'name': 'air_quality', 'variables': variables,
                                         'source_sha256': meta['sha256']})
        emitted = 0
        for record in data['records']:
            if record['parameter'] not in variables:
                continue
            instant = parsed(record['valid_time_utc'])
            if record['aggregation'] == 'current_instant':
                parameter, opened, closed = record['parameter'] + '_current', instant, instant
            else:
                if not (start <= instant < end):
                    continue
                parameter, opened, closed = record['parameter'], instant, instant
            if record['value'] is None:
                missing.append(parameter + ' missing at ' + record['valid_time_utc']); continue
            result['facts'].append({
                'id': 'f' + str(len(result['facts']) + 1), 'parameter': parameter,
                'label': LABELS.get(record['parameter'], record['parameter']), 'value': str(record['value']),
                'unit': record['unit'], 'place': place['label'],
                'entity_id': place.get('selection_id') or identity(place['coordinates']),
                'start': opened.astimezone(IST).isoformat(), 'end': closed.astimezone(IST).isoformat(),
                'source_id': data['source_id'], 'evidence_kind': 'air_quality_model',
                'evidence_version': meta['sha256'], 'citation_ids': [citation],
                'source_locators': [record['source_locator']], 'method': record['aggregation']})
            emitted += 1
        result['notes'].append(AIR_QUALITY_MODEL + ' modelled air quality at the returned grid cell' +
                               (' and the provider current hour.' if emitted else '.'))
    result['notes'] += missing
    result['notes'].append('An air-quality index is the source\'s own index; the spread of a value is not a health '
                           'assessment, a risk score or an official air-quality warning, and no health advice is produced.')
    result['notes'].append('No ground monitor is connected, so a modelled cell is not a reading from a nearby station.')
    result['status'] = 'answered' if result['facts'] and not missing else 'partial' if result['facts'] else 'unavailable'
    result['answer'] = render(result)
    return result
