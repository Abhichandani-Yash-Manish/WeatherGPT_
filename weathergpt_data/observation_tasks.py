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
def _point(plan, resolved, coordinates, gazetteer=None, notes=None, probe=None):
    """The requested point: the resolved place, an explicit pin, or the index itself.

    Observation-only plans never reach the point resolver, so the tool grounds the place it was
    given rather than asking the reader to repeat a name the question carried. Where several
    places share the name, the station layers decide: a candidate with no station in range is
    evidence for the others, and the reading is disclosed.
    """
    from .gazetteer import choose_by_probe, preferred_match
    if isinstance(coordinates, dict) and coordinates.get('latitude') is not None:
        return coordinates, 'the supplied pin'
    for place in plan.get('places') or []:
        entry = (resolved or {}).get(place.get('name'))
        if isinstance(entry, dict) and isinstance(entry.get('coordinates'), dict):
            return entry['coordinates'], entry.get('label') or place.get('name')
    if gazetteer is None:
        return None, None
    for place in plan.get('places') or []:
        matches = gazetteer.search(place.get('name') or '', place.get('state') or '', place.get('district') or '')
        # The ranked preference decides first (a state capital outranks villages that share the
        # name). Only when the candidates are genuinely tied does a fresh station decide, and the
        # choice is disclosed either way rather than being made silently.
        chosen, why = preferred_match(matches)
        if chosen and chosen.get('coordinates'):
            if notes is not None:
                notes.append('Place read as ' + str(chosen.get('label') or chosen.get('name')) + ' — ' + str(why) + '.')
            return chosen['coordinates'], chosen.get('label') or place.get('name')
        if (len(matches) > 1 and probe is not None
                and all(match.get('match_type') != 'approximate_name_requires_confirmation' for match in matches)):
            probed, _tried, _answer = choose_by_probe(matches, probe,
                                                         score=lambda rows: min(
                                                             (row.get('distance_km') if row.get('distance_km') is not None else 1e9)
                                                             for row in rows))
            if probed and probed.get('coordinates'):
                others = [match['label'] for match in matches if match.get('id') != probed.get('id')]
                if notes is not None:
                    notes.append('Place read as ' + str(probed.get('label')) + ' — the place(s) with this name are tied on rank, and '
                                 'only this one has a station reporting within the last three hours' +
                                 (': ' + '; '.join(others) + '. Say which one you meant to switch.' if others else '.'))
                return probed['coordinates'], probed.get('label') or place.get('name')
    return None, None

def execute_observation(engine, result, plan, task, resolved=None, coordinates=None):
    """Read the live station layers and the right-now reading composed around them."""
    from . import product_api
    from .now_view import compose as compose_now
    foundation = engine.workspace.foundation()

    def probe(_candidate, coordinates):
        """A fresh station near this candidate: a village whose only station is stale does not answer."""
        bundle = product_api.observations_bundle(foundation, coordinates['latitude'], coordinates['longitude'], limit=3)
        rows = []
        for _kind, stations in ((bundle.get('data') or {}).get('networks') or {}).items():
            rows.extend(stations or [])
        return [row for row in rows if row.get('age_minutes') is not None and row['age_minutes'] <= 180] or None

    point, label = _point(plan, resolved, coordinates, gazetteer=getattr(engine, 'gazetteer', None),
                          notes=result['notes'], probe=probe)
    if point is None:
        result.update(status='needs_clarification',
                      answer='Which place should I read a live station report for? Give a town or city, or a pin.',
                      follow_up='Place name and state, or an explicit pin')
        return result
    latitude, longitude = float(point['latitude']), float(point['longitude'])
    reading = compose_now(foundation, latitude, longitude, hours=6, now=engine.workspace.clock(), label=label)
    observed = (reading.get('observed') or {})
    stations = observed.get('stations') or []
    source_ids = [item.get('source_id') for item in reading.get('source_entries') or [] if item.get('source_id')]
    source_id = source_ids[0] if source_ids else 'S63'
    evidence_version = ''
    for item in observed.get('sources') or []:
        evidence_version = str(item or '')
    for station in stations:
        distance = station.get('distance_km')
        where = str(station.get('name') or station.get('station_code') or 'station')
        if distance is not None:
            where += ' · ' + str(round(float(distance), 2)) + ' km from the requested point'
        result['facts'].extend(_station_facts(result, station, where, source_id, evidence_version, ''))
        age = station.get('age_minutes')
        result['notes'].append(str(station.get('network', 'station')).upper() + ' ' + str(station.get('name')) +
                               (' observed ' + str(station.get('observed_at_utc')) if station.get('observed_at_utc') else '') +
                               (', ' + str(age) + ' minutes old at retrieval' if age is not None else '') + '.')
    result['trace']['tools'].append({'name': 'right_now_reading', 'station_rows': len(stations),
                                     'hours': len(((reading.get('next_hours') or {}).get('rows')) or []),
                                     'source_id': source_id})
    result['notes'].append('A station report describes that station at its own instant. It is not a district average, '
                           'not a forecast, and not a statement about whether a warning applies.')
    result['now_reading'] = reading
    result['answer'] = reading.get('summary') or ('No live station report was retrieved near ' + str(label or 'the requested point') + '.')
    result['status'] = 'answered' if result['facts'] else 'partial'
    return result
