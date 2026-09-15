"""Ensemble spread answers: the member distribution of one model, never a score.

The spread, the range and the percentiles are properties of the members the model
returned, computed by the adapter and disclosed with the answer. They are not a
probability, a confidence, a risk or a skill measure, and a member count is not a
probability of the event. Modelled grid values are not local measurements.
"""
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

from .adapters import ENSEMBLE, ensemble_model_for
from .answers import distance_km
from .geography import identity
from .transport import SourceError, parsed, stamp

IST = ZoneInfo('Asia/Kolkata')
MAX_HOURS = 48
ALIASES = {'rainfall': 'precipitation', 'rain': 'precipitation', 'precipitation': 'precipitation',
           'temperature': 'temperature_2m', 'temperature_2m': 'temperature_2m',
           'wind': 'wind_speed_10m', 'wind_speed': 'wind_speed_10m', 'wind_speed_10m': 'wind_speed_10m'}
STATISTICS = ('mean', 'spread', 'p10', 'p90')


def requested_variables(parameters):
    mapped = list(dict.fromkeys(ALIASES.get(name, name) for name in (parameters or [])))
    supported = [name for name in mapped if name in ENSEMBLE]
    return supported or list(ENSEMBLE)


def execute_ensemble(engine, result, plan, task, resolved, coordinates):
    foundation = engine.workspace.foundation()
    model = ensemble_model_for(task.get('request_quote', ''))
    variables = requested_variables(task.get('parameters'))
    now = engine.workspace.clock().astimezone(timezone.utc)
    if not plan.get('start_local') or not plan.get('end_local'):
        result.update(status='needs_clarification', answer='Which day or window should the ensemble cover?',
                      follow_up='A day or an ordered time window'); return result
    start, end = parsed(plan['start_local']).astimezone(timezone.utc), parsed(plan['end_local']).astimezone(timezone.utc)
    if end <= start or end - start > timedelta(hours=MAX_HOURS):
        raise SourceError('Ensemble detail supports up to %d hours per task; please narrow the window' % MAX_HOURS)
    days = max(1, min(7, (end.date() - now.date()).days + 1))
    points = engine.resolve_points(result, plan, resolved, coordinates)
    if points is None:
        return result
    result.update(charts=[], calculations=[], ensemble=True)
    missing = []
    for place in points:
        try:
            data = foundation.ensemble(place['coordinates']['latitude'], place['coordinates']['longitude'],
                                       days=days, model=model, variables=variables)
        except (ValueError, OSError) as exc:
            missing.append(place['label'] + ': ' + str(exc)); continue
        meta = data['provenance']; coverage = data['coverage']; citation = 'c-' + meta['sha256']
        result['citations'].append({
            'id': citation, 'source_id': data['source_id'], 'provider': 'Open-Meteo',
            'product': model + ' ensemble member forecast',
            'url': meta['url'], 'response_sha256': meta['sha256'], 'retrieved_at_utc': meta['retrieved_at_utc'],
            'requested_point': place['coordinates'], 'returned_grid': coverage['returned_grid'],
            'grid_distance_km': round(distance_km(place['coordinates'], coverage['returned_grid']), 3),
            'model_run_time': None})
        if place.get('citation'):
            result['citations'].append(place['citation'])
        expiry = min(parsed(meta['retrieved_at_utc']) + timedelta(hours=1), start)
        if result['expires_at_utc'] is None or expiry < parsed(result['expires_at_utc']):
            result['expires_at_utc'] = stamp(expiry)
        result['trace']['tools'].append({'name': 'ensemble', 'model': model, 'variables': variables,
                                         'source_sha256': meta['sha256']})
        emitted = 0
        for variable in variables:
            for statistic in STATISTICS:
                rows = [record for record in data['records'] if record['parameter'] == variable + '_' + statistic
                        and start <= parsed(record['valid_time_utc']) < end]
                for record in rows:
                    value = record['value']
                    if value is None:
                        missing.append(record['parameter'] + ' missing at ' + record['valid_time_utc']); continue
                    period = record['aggregation'].startswith('preceding_hour_')
                    when = parsed(record['interval_end_utc'] if period else record['valid_time_utc']).astimezone(IST)
                    opened = parsed(record['interval_start_utc']).astimezone(IST) if period else when
                    result['facts'].append({
                        'id': 'f' + str(len(result['facts']) + 1), 'parameter': record['parameter'],
                        'label': record['parameter'], 'value': value, 'unit': record['unit'],
                        'place': place['label'], 'entity_id': place.get('selection_id') or identity(place['coordinates']),
                        'start': opened.isoformat(), 'end': when.isoformat(), 'source_id': data['source_id'],
                        'evidence_kind': 'model_ensemble', 'evidence_version': meta['sha256'],
                        'citation_ids': [citation], 'source_locators': [record['source_locator']],
                        'method': record['aggregation'], 'member_count': record.get('member_count')})
                    emitted += 1
        if emitted:
            result['charts'].append({'kind': 'ensemble_spread', 'title': place['label'] + ' · ' + model +
                                     ' ensemble', 'unit': '', 'points': [],
                                     'source_ids': [data['source_id']], 'missing_values': 'Unknown where fewer than two members'})
        result['notes'].append(model + ' returned ' + ', '.join(
            '%d %s members' % (count, name) for name, count in coverage['member_total'].items()) +
            '; the control run is excluded from the spread.')
    result['notes'] += missing
    result['notes'].append('Ensemble spread and percentiles describe the returned members; they are not a '
                           'probability, confidence, risk or skill measure, and a member count is not the chance of an event.')
    result['notes'].append('Modelled grid values are not local measurements; the model run identity is not exposed.')
    result['status'] = 'answered' if result['facts'] and not missing else 'partial' if result['facts'] else 'unavailable'
    from .point_tasks import render_point_facts
    result['answer'] = render_point_facts(result)
    return result
