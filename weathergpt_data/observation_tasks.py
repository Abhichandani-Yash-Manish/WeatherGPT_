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
from datetime import timedelta

from .transport import SourceError, parsed, stamp, utcnow

# The fields a station report is read for, in the order a reader wants them. A field the station did
# not report is left out rather than defaulted.
#
# Each entry names the PARAMETER first and then every field spelling the two station layers actually
# print, because they spell the same measurement differently and neither says so: the METAR layer
# (S63, imd:metar_data_layer) prints `temp`, `rh`, `windsp`; the AWS layer prints `temp`, `rh`,
# `windspeed`. This tuple used to accept only the product's own spelling for temperature and humidity,
# so a METAR station could never produce either. Measured 21 September 2026: "What is it like right
# now in Surat?" was answered with wind speed 0.0, wind direction 0.0 and pressure 1009.0, while the
# same station's own report for the same instant held 26 °C, 94 % humidity and mist. Wind and pressure
# matched only because their spellings happened to be the layer's.
#
# The unit stays off the fact: neither layer states one (`unit_stated_by_source` is false for every
# value this adapter emits), so a fact row records what the source printed and the sentence states the
# unit the parameter is read in - exactly what the opening sentence already did for temperature and
# wind before either of them had a fact to be built from.
FIELDS = (('temperature_c', ('temp', 'temperature_c', 'temperature'), 'Observed station temperature'),
          ('dew_point_2m', ('dewtemp', 'dew_point_2m'), 'Observed station dew point'),
          ('wind_speed_kt', ('windsp', 'windspeed', 'wind_speed_kt'), 'Observed station wind speed'),
          ('wind_direction', ('winddir', 'wind_direction'), 'Observed station wind direction'),
          ('relative_humidity_2m', ('rh', 'humidity', 'relative_humidity_2m'), 'Observed station humidity'),
          ('mslp', ('mslp', 'pressure_msl'), 'Observed station pressure'),
          ('visibility', ('visibility',), 'Observed station visibility'))

# What the station can see. A METAR prints present weather as words ('mist', 'rain') and sky condition
# as a sentence; the AWS layer prints both as bare numeric codes this product holds no decoding table
# for. Only the words are read, and a code is left out rather than printed as a number beside a
# reader's question about the weather, where a zero would read as a condition nobody established.
TEXT_FIELDS = (('present_weather', ('weather',), 'Present weather the station reported'),
               ('sky_condition', ('nebulosity',), 'Sky condition the station reported'))

# The unit each parameter is READ IN. Neither station layer states one - every value this adapter emits
# carries `unit_stated_by_source: false` - so this is the product's own statement about the parameter,
# never the source's statement about the value, and each fact says which of the two its unit is in
# `unit_source`. It exists because a number with no unit is not a reading: an answer was writing
# "visibility 3000.0" and "a dew point of 25" into prose, and the unit check downstream cannot police a
# unit the fact does not carry.
READ_IN_UNITS = {'temperature_c': '°C', 'dew_point_2m': '°C', 'wind_speed_kt': 'kt',
                 'wind_direction': '°', 'relative_humidity_2m': '%', 'mslp': 'hPa', 'visibility': 'm'}
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

    def row(parameter, label_text, value, entry):
        # The source's own unit when it stated one, else the unit this parameter is read in - and the
        # row keeps the difference rather than presenting a product's convention as a source's word.
        stated = entry.get('unit')
        return {'id': 'f' + str(len(result['facts']) + len(made) + 1), 'parameter': parameter,
                'label': label_text, 'value': str(value),
                'unit': stated or READ_IN_UNITS.get(parameter),
                'unit_source': 'source' if stated else ('parameter_convention' if parameter in READ_IN_UNITS else None),
                'place': label, 'entity_id': 'station:' + str(station.get('station_code') or station.get('name')),
                'observed_at': observed, 'start': observed, 'end': observed, 'sample_at': observed,
                'source_id': source_id, 'evidence_kind': 'observation', 'evidence_version': evidence_version,
                'citation_ids': [citation_id] if citation_id else [], 'source_locators': [],
                'method': 'reported_station_observation'}

    reported = {}
    for entry in station.get('parameters') or []:
        if str(entry.get('field') or '') not in reported and entry.get('value') not in (None, ''):
            reported[str(entry.get('field'))] = entry
    for parameter, spellings, label_text in FIELDS:
        entry = next((reported[spelling] for spelling in spellings if spelling in reported), None)
        if entry is not None:
            made.append(row(parameter, label_text, entry.get('value'), entry))
    for parameter, spellings, label_text in TEXT_FIELDS:
        entry = next((reported[spelling] for spelling in spellings if spelling in reported), None)
        if entry is None:
            continue
        # A bare code is not a reading. `0` or `4` in the AWS `weather` column is a number this
        # workspace holds no table for, and printing it would hand a reader a condition the product
        # cannot claim to have understood.
        try:
            float(str(entry.get('value')).strip())
        except (TypeError, ValueError):
            made.append(row(parameter, label_text, entry.get('value'), entry))
    return made


def _hour_facts(result, reading, label):
    """The model's own next hours as facts rather than as a sentence nobody can cite.

    The right-now reading has carried these values since it was built, and they reached the reader only
    inside the composed summary text: the temperature a reader asking "what is it like" most wants was
    in the prose and in no fact, so a model writing the answer could not see it and could not cite it.
    Each row is one source hour for the grid cell, with its window and its own source id, and it stays
    a FORECAST row - `evidence_kind` says so, the label says so, and its place names the requested
    point rather than the station that answered, so nothing here can be read as an observation.
    """
    hours = reading.get('next_hours') or {}
    if hours.get('status') != 'ok':
        return []
    units = hours.get('unit') if isinstance(hours.get('unit'), dict) else {}
    made = []
    for point in hours.get('rows') or []:
        at = point.get('at')
        start = parsed(at)
        if start is None:
            continue
        end = (start + timedelta(hours=1)).isoformat()
        for key, value in point.items():
            if key == 'at' or value is None or isinstance(value, (dict, list)):
                continue
            made.append({'id': 'f' + str(len(result['facts']) + len(made) + 1),
                         'parameter': key, 'label': 'Model hour for the requested point',
                         'value': str(value), 'unit': units.get(key),
                         'place': label, 'entity_id': 'grid:' + str(hours.get('model') or 'model'),
                         'observed_at': None, 'start': at, 'end': end, 'sample_at': at,
                         'source_id': hours.get('source_id'), 'evidence_kind': 'forecast', 'evidence_version': '',
                         'citation_ids': [], 'source_locators': [], 'method': 'model_hour_for_point'})
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
                                 'only this one has a station reporting within the last three hours.')
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
        before = len(result['facts'])
        result['facts'].extend(_station_facts(result, station, where, source_id, evidence_version, ''))
        # A station the layers describe but cannot date would otherwise be a station that silently
        # contributed nothing. Which station answered, and when, is what makes the rows above readable.
        if len(result['facts']) == before:
            result['notes'].append(str(station.get('network', 'station')).upper() + ' ' + str(station.get('name')) +
                                   ' reported no field this workspace reads, so it carries no value here.')
            continue
        age = station.get('age_minutes')
        result['notes'].append(str(station.get('network', 'station')).upper() + ' ' + str(station.get('name')) +
                               (' observed ' + str(station.get('observed_at_utc')) if station.get('observed_at_utc') else '') +
                               (', ' + str(age) + ' minutes old at retrieval' if age is not None else '') + '.')
    result['trace']['tools'].append({'name': 'right_now_reading', 'station_rows': len(stations),
                                     'hours': len(((reading.get('next_hours') or {}).get('rows')) or []),
                                     'source_id': source_id})
    # The model's own hours for the point, after the station rows so the station is what an opening
    # sentence reaches for first. They are forecast rows and they say so.
    result['facts'].extend(_hour_facts(result, reading, str(label or 'the requested point')))
    result['notes'].append('A station report describes that station at its own instant. It is not a district average, '
                           'not a forecast, and not a statement about whether a warning applies.')
    result['now_reading'] = reading
    result['answer'] = reading.get('summary') or ('No live station report was retrieved near ' + str(label or 'the requested point') + '.')
    result['status'] = 'answered' if result['facts'] else 'partial'
    return result
