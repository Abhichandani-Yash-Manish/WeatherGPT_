"""Live station observations in the conversation, and the right-now reading around them.

The observations surface has read the METAR and AWS layers for months; the conversation path
answered \"live observation retrieval is not connected yet\". This connects it through the same
governed adapter and the same provenance, with the station's own time, age and distance attached
to every value.

A station report describes one station's instruments at one instant. It is not a district average,
not a forecast, and not evidence that a warning applies or does not apply. The composed right-now
reading keeps three products apart - what a station observed, what the official district product
publishes for today, and what the model holds for the next hours - and it says where radar and
satellite imagery, sub-hourly refresh and push are not connected.
"""
from .transport import SourceError, stamp, utcnow

# The fields a station report is rendered for, in the order a reader wants them. A field the
# station did not report is left out rather than defaulted.
FIELDS = (('temperature_c', 'temperature_c', 'Observed station temperature'),
          ('windsp', 'wind_speed_kt', 'Observed station wind speed'),
          ('winddir', 'wind_direction', 'Observed station wind direction'),
          ('mslp', 'mslp', 'Observed station pressure'),
          ('humidity', 'relative_humidity_2m', 'Observed station humidity'))
MAX_STATIONS = 2
NEXT_HOURS = 6
NOT_CONNECTED = ('radar and satellite imagery', 'sub-hourly refresh between source hours',
                 'any push or notification: this workspace answers when it is asked')


def _point(plan, resolved, coordinates, gazetteer=None, notes=None):
    """The requested point: the resolved place, an explicit pin, or the index itself.

    Observation-only plans never reach the point resolver, so the tool grounds the place it was
    given rather than asking the reader to repeat a name the question carried.
    """
    if isinstance(coordinates, dict) and coordinates.get('latitude') is not None:
        return coordinates, 'the supplied pin'
    for place in plan.get('places') or []:
        entry = (resolved or {}).get(place.get('name'))
        if isinstance(entry, dict) and isinstance(entry.get('coordinates'), dict):
            return entry['coordinates'], entry.get('label') or place.get('name')
    if gazetteer is None:
        return None, None
    from .gazetteer import preferred_match
    for place in plan.get('places') or []:
        matches = gazetteer.search(place.get('name') or '', place.get('state') or '', place.get('district') or '')
        chosen, why = preferred_match(matches)
        if chosen and chosen.get('coordinates'):
            if notes is not None:
                notes.append('Place read as ' + str(chosen.get('label') or chosen.get('name')) + ' — ' + str(why) + '.')
            return chosen['coordinates'], chosen.get('label') or place.get('name')
    return None, None


def _station_facts(result, station, label, source_id, evidence_version, citation_id):
    """One fact per reported field, with the station's own instant and distance attached."""
    observed = station.get('observed_at_utc') or station.get('observed_at')
    if not observed:
        return []
    made = []
    for field, parameter, label_text in FIELDS:
        for entry in station.get('parameters') or []:
            if entry.get('field') != field or entry.get('value') in (None, ''):
                continue
            made.append({'id': 'f' + str(len(result['facts']) + len(made) + 1), 'parameter': parameter,
                         'label': label_text, 'value': str(entry.get('value')), 'unit': entry.get('unit'),
                         'place': label, 'entity_id': 'station:' + str(station.get('station_code') or station.get('name')),
                         'observed_at': observed, 'start': observed, 'end': observed, 'sample_at': observed,
                         'source_id': source_id, 'evidence_kind': 'observation', 'evidence_version': evidence_version,
                         'citation_ids': [citation_id] if citation_id else [], 'source_locators': [],
                         'method': 'reported_station_observation'})
    return made


def execute_observation(engine, result, plan, task, resolved=None, coordinates=None):
    """Read the live station layers for the requested point and report what they say."""
    from . import product_api
    point, label = _point(plan, resolved, coordinates, gazetteer=getattr(engine, 'gazetteer', None),
                          notes=result['notes'])
    if point is None:
        result.update(status='needs_clarification',
                      answer='Which place should I read a live station report for? Give a town or city, or a pin.',
                      follow_up='Place name and state, or an explicit pin')
        return result
    latitude, longitude = float(point['latitude']), float(point['longitude'])
    foundation = engine.workspace.foundation()
    bundle = product_api.observations_bundle(foundation, latitude, longitude, limit=3)
    source_ids = [item.get('source_id') for item in bundle.get('sources') or [] if isinstance(item, dict)]
    source_id = source_ids[0] if source_ids else 'S63'
    evidence_version = ''
    for item in bundle.get('sources') or []:
        if isinstance(item, dict) and item.get('source_id') == source_id:
            evidence_version = str(item.get('retrieved_at_utc') or item.get('validator') or '')
    stations = []
    for kind, rows in (bundle.get('data') or {}).get('networks', {}).items():
        for row in rows or []:
            stations.append(dict(row, network=kind))
    stations.sort(key=lambda row: row.get('distance_km') if row.get('distance_km') is not None else 1e9)
    chosen = stations[:MAX_STATIONS]
    for station in chosen:
        distance = station.get('distance_km')
        where = str(station.get('name') or station.get('station_code') or 'station')
        if distance is not None:
            where += ' · ' + str(round(float(distance), 2)) + ' km from the requested point'
        result['facts'].extend(_station_facts(result, station, where, source_id, evidence_version,
                                              (bundle.get('sources') or [{}])[0].get('citation_id') if bundle.get('sources') else ''))
        age = station.get('age_minutes')
        result['notes'].append(str(station.get('network', 'station')).upper() + ' ' + str(station.get('name')) +
                               (' observed ' + str(station.get('observed_at_utc')) if station.get('observed_at_utc') else '') +
                               (', ' + str(age) + ' minutes old at retrieval' if age is not None else '') + '.')
    result['trace']['tools'].append({'name': 'observations_bundle', 'station_rows': len(stations), 'shown': len(chosen),
                                     'source_id': source_id})
    result['notes'].append('A station report describes that station at its own instant. It is not a district average, '
                           'not a forecast, and not a statement about whether a warning applies.')
    if not chosen:
        result['notes'].append('No station in the connected METAR or AWS layers reported within 150 km of this point. '
                               'That is an absence of station evidence here, not a statement that nothing is happening.')
    # What the official product publishes for today, and what the model holds for the next hours.
    from .now_view import day_state, next_hours
    try:
        warning = product_api.warnings_place(foundation, latitude, longitude)
        state = day_state(warning)
        if state:
            result['notes'].append('Official district product for ' + str(state.get('district') or 'this point') + ': ' +
                                   str(state.get('status_line')) + ' (source ' + str(state.get('source_id')) +
                                   ', issued ' + str(state.get('issued_at_utc')) + '). A quiet day in one product is not an all-clear.')
            result['trace']['tools'].append({'name': 'warnings_place', 'district': state.get('district'),
                                             'source_id': state.get('source_id'), 'status': 'retrieved'})
    except (SourceError, ValueError, OSError) as failure:
        result['notes'].append('The official district product could not be read for this point: ' + str(failure)[:160])
    try:
        forecast = product_api.forecast(foundation, latitude, longitude, days=1)
        hours = next_hours(forecast, hours=NEXT_HOURS, now=engine.workspace.clock())
        if hours.get('rows'):
            result['notes'].append('Model hours next (' + str(hours['starts']) + ' to ' + str(hours['ends']) + ', source ' +
                                   str(hours.get('source_id')) + '): ' + '; '.join(
                                       str(row['at']) + ' ' + str(row['temperature_2m']) + ' °C' +
                                       (', rain chance ' + str(row['precipitation_probability']) + '%' if row.get('precipitation_probability') is not None else '')
                                       for row in hours['rows']))
            result['trace']['tools'].append({'name': 'forecast_hours', 'rows': len(hours['rows']),
                                             'source_id': hours.get('source_id'), 'status': 'retrieved'})
    except (SourceError, ValueError, OSError) as failure:
        result['notes'].append('The next hours could not be read from the model product: ' + str(failure)[:160])
    result['notes'].append('Not connected here: ' + '; '.join(NOT_CONNECTED) + '.')
    result['status'] = 'answered' if result['facts'] else 'partial'
    result['answer'] = ('Live station reports near ' + str(label or 'the requested point') + ':' if result['facts'] else
                        'No live station report was retrieved near ' + str(label or 'the requested point') + '.')
    return result
