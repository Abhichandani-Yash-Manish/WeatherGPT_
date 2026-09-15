"""Read-model views for the product surfaces.

Every function returns one payload shape so the client has a single contract:

    {schema_version, generated_at_utc, view, status, data,
     sources[], coverage{}, limitations[], not_established[]}

Rules this layer holds to:

* every datum keeps the source it came from and the instant it was retrieved;
* a source that cannot be reached produces an explicit unavailable or partial
  status, never an empty success;
* nothing is computed in the client, and nothing here invents a value, a unit,
  a severity or a confidence;
* an observation, a model forecast, an official warning and a source advisory
  stay distinct products with their own limits attached.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import district_warnings as dw
from . import national, observations
from .adapters import COLOURS, HAZARDS
from .foundation import ROOT
from .gazetteer import Gazetteer
from .transport import SourceError, stamp, utcnow

SCHEMA = 'product-view-v1'
MAP_ROOT = ROOT / 'data/processed/map-basemap'
MAP_FILES = {'land': 'land.geojson', 'states': 'states.geojson', 'districts': 'districts.geojson',
             'basins': 'basins.geojson', 'coast-zones': 'coast-zones.geojson', 'places': 'places.geojson'}
WARNING_ATTRIBUTES = ('District,Obj_id,Date,UTC,updated_at,Day_1,Day_2,Day_3,Day_4,Day_5,'
                      'Day1_Color,Day2_Color,Day3_Color,Day4_Color,Day5_Color,'
                      'Day1_text,Day2_text,Day3_text,Day4_text,Day5_text')
WFS = 'https://reactjs.imd.gov.in/geoserver/wfs'
# The single list of product read-model paths, used by the router and by the
# workspace to keep an unknown path a 404 rather than an authorisation failure.
PRODUCT_PATHS = ('/api/overview', '/api/warnings/national', '/api/warnings/place',
                 '/api/observations/near', '/api/observations/network', '/api/radar', '/api/basins',
                 '/api/forecast', '/api/forecast/changes', '/api/marine', '/api/river', '/api/aviation', '/api/places/search',
                 '/api/map/layers', '/api/warnings/cap', '/api/warnings/alert-brief', '/api/settings/capabilities',
                 '/api/climate/index', '/api/climate/series', '/api/advisories/states',
                 '/api/advisories/districts', '/api/personas', '/api/now', '/api/ensemble', '/api/air-quality')
_REGISTRY = {'path': None, 'mtime': None, 'products': {}}


def envelope(view, status, data, sources=None, coverage=None, limitations=None, not_established=None):
    return {'schema_version': SCHEMA, 'generated_at_utc': stamp(utcnow()), 'view': view, 'status': status,
            'data': data, 'sources': sources or [], 'coverage': coverage or {},
            'limitations': limitations or [], 'not_established': not_established or []}


def personas_view():
    """Who is reading: three registered positions, each framing and never finding."""
    from .personas import PERSONA_NOTE, catalogue
    return envelope('personas.catalogue', 'ok', catalogue(),
                    limitations=[PERSONA_NOTE,
                                 'The same question under two personas retrieves the same evidence; only the emphasis, the '
                                 'starting surfaces and the listed limits differ.'])


def now_view(foundation, latitude, longitude, refresh=False, now=None):
    """The right-now reading: observed, in force, and the next hours, kept apart."""
    from .now_view import NOT_CONNECTED, NOT_ESTABLISHED, compose
    reading = compose(foundation, latitude, longitude, now=now, refresh=refresh)
    limitations = list(reading.get('limitations') or [])
    limitations += [note for note in reading.get('not_connected') or [] if note not in limitations]
    return envelope('now.composed', 'ok' if reading.get('status') == 'ok' else 'unavailable', reading,
                    sources=[source_entry(item.get('source_id'), item) for item in reading.get('source_entries') or []]
                            or [source_entry(source_id, None) for source_id in reading.get('sources') or []],
                    coverage={'stations': len((reading.get('observed') or {}).get('stations') or []),
                              'day': (reading.get('in_force') or {}).get('day'),
                              'hours': len((reading.get('next_hours') or {}).get('rows') or [])},
                    limitations=limitations, not_established=list(NOT_ESTABLISHED))


def registry_products():
    path = ROOT / 'data/registry/sources.json'
    stat = path.stat()
    if _REGISTRY['path'] != str(path) or _REGISTRY['mtime'] != stat.st_mtime:
        record = json.loads(path.read_text(encoding='utf-8'))
        _REGISTRY.update(path=str(path), mtime=stat.st_mtime,
                         products={entry['id']: entry for entry in record['products']})
    return _REGISTRY['products']


def source_entry(source_id, meta, product=None, layer=None):
    entry = registry_products().get(source_id, {})
    return {'source_id': source_id,
            'product': product or entry.get('product') or (layer or 'unspecified layer'),
            'layer': layer,
            'url': (meta or {}).get('url'),
            'retrieved_at_utc': (meta or {}).get('retrieved_at_utc'),
            'sha256_prefix': str((meta or {}).get('sha256') or '')[:12],
            'integration_status': (entry.get('integration') or {}).get('status') or entry.get('evidence_stage'),
            'usage_terms': entry.get('usage_terms'),
            'user_review': entry.get('user_review')}


def registry_limitations(source_ids):
    notes = []
    for source_id in sorted(set(source_ids)):
        entry = registry_products().get(source_id, {})
        if entry.get('user_review') == 'pending':
            notes.append(source_id + ' carries user_review pending and unresolved usage terms.')
    return notes


def norm(value):
    return re.sub(r'[^A-Z]', '', str(value or '').upper())


def newest_build():
    builds = sorted(path for path in MAP_ROOT.glob('basemap-v1-*') if path.is_dir())
    if not builds:
        raise SourceError('No vendored basemap build is present; run scripts/build_map_basemap.py')
    return builds[-1]


def district_join():
    build = newest_build()
    return build, json.loads((build / 'district-join.json').read_text(encoding='utf-8'))


def state_for(district_name, join=None):
    if join is None:
        _, join = district_join()
    entry = join['districts'].get(norm(district_name)) or {}
    return entry.get('state'), entry


def map_manifest():
    build = newest_build()
    manifest = json.loads((build / 'manifest.json').read_text(encoding='utf-8'))
    audit = json.loads((build / 'audit.json').read_text(encoding='utf-8'))
    layers = []
    for name, filename in sorted(MAP_FILES.items()):
        path = build / filename
        if not path.exists():
            continue
        entry = next((item for item in manifest['layers'] if item['file'] == filename), {})
        layers.append({'name': name, 'file': filename, 'bytes': path.stat().st_size,
                       'budget_bytes': entry.get('budget_bytes')})
    return envelope('map.layers', 'ok',
                    {'build_id': manifest['build_id'], 'layers': layers, 'join_file': manifest.get('join_file'),
                     'attribution': manifest.get('attribution'),
                     'state_attribution': audit.get('state_attribution', {}),
                     'district_polygons': audit.get('district_polygons_written'),
                     'skipped_without_a_name': len(audit.get('skipped_without_a_district_name') or [])},
                    sources=[source_entry('S63', {'url': manifest.get('service'),
                                                  'retrieved_at_utc': manifest.get('created_at_utc')},
                                          product='Vendored basemap geometry')],
                    coverage={'layers': len(layers)},
                    limitations=list(manifest.get('limitations') or []),
                    not_established=['The basemap is display geometry, not a survey boundary and not an LGD crosswalk.'])


def map_layer_path(name):
    filename = MAP_FILES.get(name)
    if not filename:
        raise SourceError('Unknown map layer: ' + str(name))
    build = newest_build()
    path = (build / filename).resolve()
    if build.resolve() not in path.parents or not path.exists():
        raise SourceError('Map layer is unavailable')
    return path


def warning_attributes(foundation, refresh=False, ttl=900):
    params = {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature',
              'typeName': 'imd:district_warnings_india', 'outputFormat': 'application/json',
              'propertyName': WARNING_ATTRIBUTES, 'srsName': 'EPSG:4326'}

    def validate(data, meta):
        if not isinstance(data, dict) or data.get('type') != 'FeatureCollection':
            raise ValueError('warning attributes: expected a FeatureCollection')
        features = data.get('features')
        if not isinstance(features, list) or not features:
            raise ValueError('warning attributes: no features')
        total = data.get('totalFeatures')
        if total is not None and int(total) != len(features):
            raise ValueError('warning attributes: truncated collection')
        if not 700 <= len(features) <= 800:
            raise ValueError('warning attributes: unexpected feature count ' + str(len(features)))

    return foundation.get('S63', WFS, params, product_parser=validate, ttl=ttl, refresh=refresh,
                          max_bytes=80_000_000)


def decode_days(properties):
    issued = None
    day_value = str(properties.get('Date') or '').strip()
    hour = properties.get('UTC')
    if day_value:
        try:
            issued = datetime.fromisoformat(day_value).replace(tzinfo=timezone.utc)
            if isinstance(hour, int) and not isinstance(hour, bool) and 0 <= hour <= 23:
                issued = issued.replace(hour=hour)
        except ValueError:
            issued = None
    days = []
    for index in range(1, 6):
        raw = properties.get('Day_%d' % index)
        colour_code = properties.get('Day%d_Color' % index)
        source_text = (properties.get('Day%d_text' % index) or '').strip() or None
        codes = [int(token.strip()) for token in str(raw or '').split(',') if token.strip().isdigit()]
        unknown = [code for code in codes if code not in HAZARDS]
        days.append({'day': index,
                     'date_utc': issued.date().isoformat() if issued else None,
                     'hazard_codes': codes,
                     'hazards': [HAZARDS[code] for code in codes if code in HAZARDS],
                     'colour_code': colour_code if isinstance(colour_code, int) else None,
                     'colour': COLOURS.get(colour_code) if isinstance(colour_code, int) else None,
                     'source_text': source_text,
                     'unknown_hazard_codes': unknown,
                     'quiet': bool(codes) and all(code == 1 for code in codes) and not source_text})
    return issued, days


def warnings_national(foundation, refresh=False):
    data, meta = warning_attributes(foundation, refresh=refresh)
    build, join = district_join()
    districts, skipped, tally = [], [], {}
    for properties in (feature.get('properties') or {} for feature in data['features']):
        raw = properties.get('District')
        key = norm(raw)
        if not key:
            skipped.append({'obj_id': properties.get('Obj_id'), 'reason': 'the source feature carries no district name'})
            continue
        issued, days = decode_days(properties)
        for day in days:
            if not day['quiet']:
                label = day['colour'] or 'unset'
                tally[label] = tally.get(label, 0) + 1
        districts.append({'key': key, 'district': raw,
                          'state': (join['districts'].get(key) or {}).get('state'),
                          'bulletin_date': properties.get('Date') or None,
                          'issued_at_utc': stamp(issued) if issued else None,
                          'updated_at': properties.get('updated_at'),
                          'days': days})
    return envelope('warnings.national', 'ok' if districts else 'unavailable',
                    {'districts': districts, 'tally': tally, 'skipped': skipped, 'basemap_build': build.name},
                    sources=[source_entry('S63', meta, layer='imd:district_warnings_india')],
                    coverage={'features_returned': len(data['features']), 'districts_listed': len(districts),
                              'skipped_without_a_name': len(skipped), 'basemap_districts': len(join['districts'])},
                    limitations=['Day fields are official hazard code lists, not severity stages. The colour is the product colour for that district-day.',
                                 'State names are attributed geometrically from a second official layer and each attribution records its overlap ratio.',
                                 'A quiet day means the source published no hazard for that district-day in this product. It is not an all-clear.',
                                 'Total per-day colour counts include only districts whose source colour code is recognised.'],
                    not_established=['No live update, cancel or supersede edition has been observed for this layer.',
                                     'Origin authentication of the service is not established.'])


def warnings_place(foundation, latitude, longitude, refresh=False):
    snapshot = foundation.warning_snapshot(latitude, longitude, refresh=refresh)
    records = snapshot.get('records') or []
    meta = snapshot.get('provenance')
    if not records:
        return envelope('warnings.place', 'unavailable',
                        {'district': None, 'state': None, 'days': []},
                        sources=[source_entry('S63', meta, layer='imd:district_warnings_india')],
                        coverage=snapshot.get('coverage'),
                        limitations=list(snapshot.get('limitations') or []),
                        not_established=['The point does not fall inside any district polygon of this product, so no district guidance applies there.'])
    record = records[0]
    rows, issued = dw.day_rows(record)
    state, attribution = state_for(record.get('district_label'))
    # The headline is derived from the same day rows the strip shows, never from a field the
    # endpoint does not supply. An absent summary is unknown, not "no warning": the opening
    # Ahmedabad card read a missing data.severity and showed a quiet headline above a hazard
    # day (measured 15 September 2026).
    hazard_rows = [row for row in rows if any(code != 1 for code in row['hazard_codes'])
                   or row['source_text'] or (row['hazards'] and not row['quiet'])]
    level, _ = dw.severity(hazard_rows)
    has_hazard = True if hazard_rows else (False if all(row['quiet'] for row in rows) else None)
    if has_hazard and level:
        headline = 'A ' + level + ' warning is published for this district'
    elif has_hazard:
        headline = 'A warning is published for this district'
    elif has_hazard is False:
        headline = 'No warning in this product'
    else:
        headline = 'Warning state not established'
    return envelope('warnings.place', 'ok',
                    {'district': record.get('district_label'), 'state': state,
                     'issued_at_utc': stamp(issued), 'temporal_applicability': record.get('temporal_applicability'),
                     'day_boundary_basis': record.get('day_boundary_basis'),
                     'overlap': attribution.get('overlap'), 'days': rows,
                     'severity': level if has_hazard else None, 'has_hazard': has_hazard,
                     'headline': headline, 'summary': dw.summary(record, rows, issued),
                     'source_locator': record.get('source_locator')},
                    sources=[source_entry('S63', meta, layer='imd:district_warnings_india')],
                    coverage=snapshot.get('coverage'),
                    limitations=list(snapshot.get('limitations') or []) +
                                ['The headline severity is derived from the published day colours and hazards, not a new IMD field.'],
                    not_established=['This is district-level warning guidance, not a flood warning, not a CAP alert and not an all-clear.',
                                     'Origin authentication of the service is not established.'])


def observations_near(foundation, latitude, longitude, kind='metar', radius_km=150.0, limit=10, refresh=False, now=None):
    if kind not in ('metar', 'aws'):
        raise SourceError('Use metar or aws')
    rows, meta, rejected = observations.load(foundation, kind, refresh=refresh)
    found = observations.nearest(rows, latitude, longitude, radius_km=radius_km, limit=limit, now=now)
    return envelope('observations.near', 'ok' if found else 'unavailable',
                    {'kind': kind, 'stations': found, 'rejected': rejected,
                     'query': {'latitude': latitude, 'longitude': longitude, 'radius_km': radius_km, 'limit': limit}},
                    sources=[source_entry('S63', meta,
                                          layer=('imd:metar_data_layer' if kind == 'metar' else 'imd:aws_data_layer'))],
                    coverage={'stations_in_layer': len(rows), 'stations_within_radius': len(found)},
                    limitations=list(observations.LIMITATIONS),
                    not_established=['No station here has been matched to an official station register.',
                                     'Nothing here establishes whether a warning applies.'])


def radar_status(foundation, refresh=False):
    packet = national.radar_status(foundation, refresh=refresh)
    reported = [station for station in packet['stations'] if station.get('status') is not None]
    return envelope('networks.radar', 'ok' if packet['stations'] else 'unavailable',
                    {'stations': packet['stations'], 'rejected': packet['rejected'],
                     'reported': len(reported), 'not_reported': len(packet['stations']) - len(reported)},
                    sources=[source_entry('S63', packet['meta'], layer=packet['layer'])],
                    coverage={'stations': len(packet['stations'])},
                    limitations=['Radar status is the network reporting on itself, not a rainfall, nowcast or warning product.',
                                 'The status code is shown verbatim beside the source remarks field; neither is interpreted here.'],
                    not_established=['No radar imagery, rainfall estimate or derived product is retrieved.'])


def river_basins(foundation, refresh=False):
    packet = national.river_basins(foundation, refresh=refresh)
    return envelope('networks.basins', 'ok' if packet['basins'] else 'unavailable',
                    {'basins': packet['basins'], 'with_day_fields': packet['with_day_fields'],
                     'rejected': packet['rejected']},
                    sources=[source_entry('S63', packet['meta'], layer=packet['layer'])],
                    coverage={'basins': len(packet['basins']), 'with_day_fields': packet['with_day_fields']},
                    limitations=list(national.LIMITATIONS),
                    not_established=['The meaning of the sub-basin day fields is not documented by this layer, so no flood class, severity or warning level is derived from them.'])


def series_from_packet(packet):
    parameters = {}
    for record in packet.get('records') or []:
        name = record.get('parameter')
        bucket = parameters.setdefault(name, {'unit': record.get('unit'), 'points': [],
                                              'aggregation': record.get('aggregation'),
                                              'model': record.get('model'), 'quality_flags': []})
        bucket['points'].append({'t': record.get('valid_time_utc') or record.get('period_start_utc') or record.get('date'),
                                 'v': record.get('value'),
                                 'start': record.get('interval_start_utc') or record.get('period_start_utc'),
                                 'end': record.get('interval_end_utc') or record.get('period_end_utc'),
                                 'source_locator': record.get('source_locator')})
        for flag in record.get('quality_flags') or []:
            if flag not in bucket['quality_flags']:
                bucket['quality_flags'].append(flag)
    for bucket in parameters.values():
        bucket['points'].sort(key=lambda point: str(point['t']))
    return parameters


def _series_view(view, packet, extra, sources, limitations, not_established):
    parameters = series_from_packet(packet)
    data = {'parameters': parameters}
    data.update(extra)
    return envelope(view, 'ok' if parameters else 'unavailable', data,
                    sources=[source_entry(packet.get('source_id'), packet.get('provenance'), product=packet.get('family'))],
                    coverage=packet.get('coverage'),
                    limitations=list(packet.get('limitations') or []) + list(limitations),
                    not_established=list(not_established))


def forecast(foundation, latitude, longitude, days=3, source='hourly_forecast', refresh=False):
    if source not in ('hourly_forecast', 'forecast_summary'):
        raise SourceError('Use hourly_forecast or forecast_summary')
    packet = (foundation.extended_forecast(latitude, longitude, days, refresh=refresh) if source == 'hourly_forecast'
              else foundation.forecast(latitude, longitude, days, refresh=refresh))
    coverage = packet.get('coverage') or {}
    return _series_view('forecast.point', packet,
                        {'days': days, 'source_family': source, 'grid': coverage.get('returned_grid'),
                         'requested': coverage.get('requested_point'), 'time_basis': coverage.get('time_basis')},
                        None, [],
                        ['Model run lineage is unspecified for this delivery, so run-to-run comparison is not established.',
                         'No forecast skill or probability calibration is validated here.'])


def ensemble(foundation, latitude, longitude, days=3, model='gfs025', variables=None, threshold=None, refresh=False):
    packet = foundation.ensemble(latitude, longitude, days=days, model=model, variables=variables,
                                 threshold=threshold, refresh=refresh)
    coverage = packet.get('coverage') or {}
    return _series_view('ensemble.spread', packet,
                        {'days': days, 'model': coverage.get('model'),
                         'member_total': coverage.get('member_total'), 'statistics': coverage.get('statistics'),
                         'grid': coverage.get('returned_grid'), 'requested': coverage.get('requested_point'),
                         'time_basis': coverage.get('time_basis')},
                        None, [],
                        ['The spread is a property of the returned ensemble members, not a forecast probability, '
                         'a confidence or a skill measure.'])


def air_quality(foundation, latitude, longitude, days=3, variables=None, refresh=False):
    packet = foundation.air_quality(latitude, longitude, days=days, variables=variables, refresh=refresh)
    coverage = packet.get('coverage') or {}
    parameters = series_from_packet(packet)
    data = {'parameters': parameters, 'current': coverage.get('current'), 'domain': coverage.get('domain'),
            'grid': coverage.get('returned_grid'), 'requested': coverage.get('requested_point'),
            'time_basis': coverage.get('time_basis')}
    return envelope('air_quality.point', 'ok' if parameters else 'unavailable', data,
                    sources=[source_entry(packet.get('source_id'), packet.get('provenance'), product=packet.get('family'))],
                    coverage=coverage, limitations=list(packet.get('limitations') or []),
                    not_established=['An air-quality index is the source\'s own index, and no health advice, '
                                     'risk score or official warning is produced from it.'])


def forecast_changes(latitude, longitude, database=None, limit=40):
    """How stored forecast retrievals for this point differ for the same valid hour.

    This is vintage variance, not forecast skill or calibration. Upstream model run
    identity is not exposed by the store, so a change cannot be attributed to a rerun,
    and retrieval time is not issue time. Only windows retrieved more than once can be
    compared at all.
    """
    import sqlite3
    from .answers import ROOT as ANSWER_ROOT
    database = Path(database or (ANSWER_ROOT / 'data/runtime/ingestion/ingestion.sqlite'))
    if not database.exists():
        return envelope('forecast.changes', 'unavailable', {'point': {'latitude': latitude, 'longitude': longitude},
                        'retrievals': [], 'parameters': {}, 'overlapping_valid_hours': 0,
                        'interpretation': 'vintage_variance_not_skill'},
                        coverage={'requested_point': {'latitude': latitude, 'longitude': longitude}},
                        limitations=['No ingestion store exists yet, so no stored retrieval can be compared.'],
                        not_established=['Forecast skill, calibration and accuracy are not measured here.'])
    connection = sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)
    try:
        rows = connection.execute(
            'SELECT v.committed,v.sha256,v.result,j.spec FROM versions v JOIN jobs j ON j.id=v.job_id '
            "WHERE json_extract(j.spec,'$.product') IN ('forecast','extended_forecast') ORDER BY v.committed").fetchall()
    finally:
        connection.close()
    groups = {}
    for committed, sha, result, spec in rows:
        try:
            spec_data = json.loads(spec); payload = json.loads(result)
        except (TypeError, ValueError):
            continue
        if spec_data.get('latitude') is None or spec_data.get('longitude') is None:
            continue
        key = (round(float(spec_data['latitude']), 4), round(float(spec_data['longitude']), 4))
        groups.setdefault(key, []).append({'committed': float(committed), 'sha256': sha, 'product': spec_data.get('product'),
                                           'request_date': spec_data.get('request_date'), 'payload': payload})
    if not groups:
        return envelope('forecast.changes', 'unavailable', {'point': {'latitude': latitude, 'longitude': longitude},
                        'retrievals': [], 'parameters': {}, 'overlapping_valid_hours': 0,
                        'interpretation': 'vintage_variance_not_skill'},
                        coverage={'requested_point': {'latitude': latitude, 'longitude': longitude}},
                        limitations=['No stored forecast retrieval exists for any point yet.'],
                        not_established=['Forecast skill, calibration and accuracy are not measured here.'])
    nearest = min(groups, key=lambda point: abs(point[0] - latitude) + abs(point[1] - longitude))
    distance = abs(nearest[0] - latitude) + abs(nearest[1] - longitude)
    if distance > 0.1:
        return envelope('forecast.changes', 'unavailable', {'point': {'latitude': latitude, 'longitude': longitude},
                        'retrievals': [], 'parameters': {}, 'overlapping_valid_hours': 0,
                        'interpretation': 'vintage_variance_not_skill'},
                        coverage={'requested_point': {'latitude': latitude, 'longitude': longitude},
                                  'nearest_stored_point': {'latitude': nearest[0], 'longitude': nearest[1]}},
                        limitations=['No stored forecast retrieval is close enough to this point to compare.'],
                        not_established=['Forecast skill, calibration and accuracy are not measured here.'])
    retrievals = sorted(groups[nearest], key=lambda row: row['committed'])
    series = {}
    units = {}
    for retrieval in retrievals:
        for record in (retrieval['payload'].get('records') or []):
            if record.get('value') is None or not record.get('valid_time_utc'):
                continue
            parameter = record.get('parameter')
            units.setdefault(parameter, record.get('unit'))
            series.setdefault((parameter, record['valid_time_utc']), {})[retrieval['committed']] = record['value']
    parameters = {}
    overlapping = 0
    for (parameter, valid_time), values in series.items():
        if len(values) < 2:
            continue
        ordered = sorted(values.items())
        try:
            change = abs(float(ordered[-1][1]) - float(ordered[0][1]))
        except (TypeError, ValueError):
            continue
        entry = parameters.setdefault(parameter, {'unit': units.get(parameter), 'valid_hours': 0,
                                                  'total_abs_change': 0.0, 'max_abs_change': 0.0, 'example': None})
        entry['valid_hours'] += 1
        entry['total_abs_change'] += change
        if change > entry['max_abs_change']:
            entry['max_abs_change'] = round(change, 4)
            entry['example'] = {'valid_time_utc': valid_time, 'first_value': ordered[0][1], 'last_value': ordered[-1][1],
                                'first_retrieved_utc': stamp(datetime.fromtimestamp(ordered[0][0], timezone.utc)),
                                'last_retrieved_utc': stamp(datetime.fromtimestamp(ordered[-1][0], timezone.utc))}
        overlapping += 1
    for entry in parameters.values():
        entry['mean_abs_change'] = round(entry['total_abs_change'] / entry['valid_hours'], 4)
        entry.pop('total_abs_change')
    parameters = dict(sorted(parameters.items(), key=lambda item: -item[1]['valid_hours']))
    product_ids = sorted({retrieval['product'] for retrieval in retrievals})
    source_ids = [{'forecast': 'S21', 'extended_forecast': 'S62'}.get(product, 'S21') for product in product_ids]
    sources = [source_entry(source_id, {'retrieved_at_utc': stamp(datetime.fromtimestamp(retrievals[-1]['committed'], timezone.utc)),
                                        'sha256': retrievals[-1]['sha256']}) for source_id in source_ids]
    status = 'ok' if overlapping else 'partial'
    if len(retrievals) == 1:
        status = 'partial'
    return envelope('forecast.changes', status,
                    {'point': {'latitude': nearest[0], 'longitude': nearest[1]},
                     'requested_point': {'latitude': latitude, 'longitude': longitude},
                     'retrievals': [{'retrieved_at_utc': stamp(datetime.fromtimestamp(row['committed'], timezone.utc)),
                                     'product': row['product'], 'request_date': row['request_date'],
                                     'response_sha256_prefix': str(row['sha256'] or '')[:12]} for row in retrievals[-limit:]],
                     'retrieval_count': len(retrievals), 'parameters': parameters,
                     'overlapping_valid_hours': overlapping, 'interpretation': 'vintage_variance_not_skill'},
                    sources=sources,
                    coverage={'requested_point': {'latitude': latitude, 'longitude': longitude},
                              'stored_point': {'latitude': nearest[0], 'longitude': nearest[1]},
                              'retrievals': len(retrievals), 'overlapping_valid_hours': overlapping},
                    limitations=['This compares stored retrievals of the same valid hour; it conflates model updates with shorter horizons because run identity is not exposed.',
                                 'Retrieval time is not the upstream model issue time, and only windows retrieved more than once can be compared.',
                                 'A change is not an error: neither retrieval is validated by this view.'],
                    not_established=['Forecast skill, calibration and accuracy: no observation or verified analysis is matched here.',
                                     'Attribution of a change to a model run: upstream run identity is not exposed.',
                                     'Spatial representativeness: modelled grid values are not local measurements.'])


def marine(foundation, latitude, longitude, days=3, refresh=False):
    packet = foundation.marine(latitude, longitude, days, refresh=refresh)
    coverage = packet.get('coverage') or {}
    return _series_view('marine.point', packet,
                        {'days': days, 'grid': coverage.get('returned_grid'), 'requested': coverage.get('requested_point'),
                         'grid_distance_km': coverage.get('grid_distance_km')},
                        None, [],
                        ['No official sea-area bulletin, observed buoy value, tide, current or sea-surface temperature is retrieved here.'])


def river(foundation, latitude, longitude, days=3, refresh=False):
    packet = foundation.river(latitude, longitude, days, refresh=refresh)
    coverage = packet.get('coverage') or {}
    return _series_view('river.point', packet,
                        {'days': days, 'grid': coverage.get('returned_grid'),
                         'grid_distance_km': coverage.get('grid_distance_km')},
                        None, [],
                        ['No observed gauge level, danger level, inundation extent or official flood warning is established by a discharge value.'])


def aviation(foundation, stations, kind='metar', refresh=False):
    packet = foundation.aviation(stations, kind, refresh=refresh)
    return envelope('aviation.station', packet.get('status') or 'unavailable',
                    {'stations': packet.get('records') or [], 'kind': kind,
                     'missing': (packet.get('coverage') or {}).get('missing_stations')},
                    sources=[source_entry(packet.get('source_id'), packet.get('provenance'), product=packet.get('family'))],
                    coverage=packet.get('coverage'),
                    limitations=list(packet.get('limitations') or []),
                    not_established=['A station report is not a flight status, a route briefing or a clearance.'])


def places_search(query, limit=12):
    if not isinstance(query, str) or len(query.strip()) < 2:
        raise SourceError('Type at least two characters to search for a place')
    matches = Gazetteer().search(query.strip())[:limit]
    return envelope('places.search', 'ok' if matches else 'unavailable',
                    {'query': query, 'matches': matches},
                    sources=[source_entry('S61', {'url': (registry_products().get('S61') or {}).get('access_url')})],
                    coverage={'matches': len(matches)},
                    limitations=['Place records are GeoNames source labels, not authoritative LGD entities, and a shared name requires a choice.',
                                 'A settlement point is not a district boundary and not a district average.'],
                    not_established=['No reviewed dated administrative crosswalk is applied here.'])

# A place is resolved against the vendored district geometry rather than by
# re-fetching the 19 MB warning layer with a point in the URL, which would create
# a separate cache entry per point. The vendored geometry is the same official
# geometry the map draws, so the table and the map agree by construction.
_GEOMETRY = {'build': None, 'rows': None}


def district_geometry():
    build = newest_build()
    if _GEOMETRY['build'] != build.name or _GEOMETRY['rows'] is None:
        data = json.loads((build / 'districts.geojson').read_text(encoding='utf-8'))
        _, join = district_join()
        rows = []
        for feature in data['features']:
            key = feature['properties']['k']
            rows.append({'key': key, 'name': feature['properties'].get('n'), 'state': feature['properties'].get('s'),
                         'geometry': feature['geometry'], 'attribution': join['districts'].get(key, {})})
        _GEOMETRY.update(build=build.name, rows=rows)
    return _GEOMETRY['rows']


def districts_for_point(latitude, longitude):
    from shapely.geometry import Point, shape
    point = Point(float(longitude), float(latitude))
    hits = []
    for row in district_geometry():
        try:
            area = shape(row['geometry'])
        except (ValueError, TypeError, KeyError):
            continue
        if not area.is_empty and area.is_valid and area.covers(point):
            hits.append(row)
    return hits


def district_rows_by_key(foundation, refresh=False):
    packet = warnings_national(foundation, refresh=refresh)
    return {row['key']: row for row in packet['data']['districts']}, packet


def observations_bundle(foundation, latitude, longitude, kinds=('metar', 'aws'), radius_km=150.0, limit=6, refresh=False, now=None):
    """Both station networks in one read, keeping each network's own status."""
    collected = {}
    sources = []
    notes = []
    for kind in kinds:
        view = observations_near(foundation, latitude, longitude, kind=kind, radius_km=radius_km, limit=limit,
                                 refresh=refresh, now=now)
        collected[kind] = view['data']['stations']
        sources += view['sources']
        notes += [note for note in view['limitations'] if note not in notes]
    status = 'ok' if any(collected.values()) else 'unavailable'
    return envelope('observations.both', status,
                    {'networks': collected, 'query': {'latitude': latitude, 'longitude': longitude,
                                                      'radius_km': radius_km, 'limit': limit}},
                    sources=sources,
                    coverage={kind: len(rows) for kind, rows in collected.items()},
                    limitations=notes,
                    not_established=['A station observation is not a district average and not a forecast.',
                                     'Nothing here establishes whether a warning applies.'])


def bulletin_date_counts(rows):
    counts = {}
    for row in rows:
        key = row.get('bulletin_date') or 'date not stated'
        counts[key] = counts.get(key, 0) + 1
    return counts


def most_common_date(rows):
    counts = bulletin_date_counts(rows)
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))[0][0]

def overview(foundation, places=None, refresh=False, now=None):
    """One situational read: the national warning picture, the radar network, and a strip per place."""
    national_view = warnings_national(foundation, refresh=refresh)
    rows = national_view['data']['districts']
    by_key = {row['key']: row for row in rows}
    network = national.radar_status(foundation, refresh=False)
    place_strips = []
    for place in places or []:
        hits = districts_for_point(place['latitude'], place['longitude'])
        if not hits:
            place_strips.append({'label': place.get('label'), 'latitude': place['latitude'], 'longitude': place['longitude'],
                                 'district': None, 'state': None, 'days': [],
                                 'note': 'This point is not inside any district polygon of the district warning product.'})
            continue
        row = by_key.get(hits[0]['key'])
        place_strips.append({'label': place.get('label'), 'latitude': place['latitude'], 'longitude': place['longitude'],
                             'district': (row or {}).get('district') or hits[0]['name'], 'state': hits[0]['state'],
                             'bulletin_date': (row or {}).get('bulletin_date'),
                             'issued_at_utc': (row or {}).get('issued_at_utc'),
                             'days': (row or {}).get('days') or [],
                             'note': None if row else 'The district polygon is present but the warning table has no row for it.'})
    return envelope('overview', 'ok' if rows else 'unavailable',
                    {'national': {'districts': len(rows), 'tally': national_view['data']['tally'],
                                  'skipped': len(national_view['data']['skipped']),
                                  'bulletin_date': most_common_date(rows),
                                  'bulletin_dates': bulletin_date_counts(rows)},
                     'radar': {'stations': len(network['stations']),
                               'reported': len([s for s in network['stations'] if s.get('status') is not None])},
                     'places': place_strips},
                    sources=national_view['sources'] + [source_entry('S63', network['meta'], layer=network['layer'])],
                    coverage=national_view['coverage'],
                    limitations=national_view['limitations'],
                    not_established=national_view['not_established'] + [
                        'The radar summary states how many stations report a state, not whether any station is degraded.',
                        'A place strip is the district warning for the containing district, not a forecast.'])


def _first(params, name, default=None):
    values = params.get(name)
    if not values:
        return default
    value = values[0]
    return value if value != '' else default


def _flag(params, name):
    return str(_first(params, name, '')).lower() in {'1', 'true', 'yes'}


def _float(params, name, default=None, low=None, high=None, required=False):
    raw = _first(params, name)
    if raw is None:
        if required:
            raise SourceError('The ' + name + ' parameter is required')
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise SourceError('The ' + name + ' parameter must be a number')
    if (low is not None and value < low) or (high is not None and value > high):
        raise SourceError('The ' + name + ' parameter is outside its permitted range')
    return value


def _int(params, name, default=None, low=None, high=None):
    raw = _first(params, name)
    if raw is None:
        return default
    if not str(raw).lstrip('-').isdigit():
        raise SourceError('The ' + name + ' parameter must be a whole number')
    value = int(raw)
    if (low is not None and value < low) or (high is not None and value > high):
        raise SourceError('The ' + name + ' parameter is outside its permitted range')
    return value


def _point_params(params):
    return (_float(params, 'lat', required=True, low=-90, high=90),
            _float(params, 'lon', required=True, low=-180, high=180))


def _places_param(params):
    places = []
    for raw in params.get('place') or []:
        parts = str(raw).split(',')
        if len(parts) != 2:
            raise SourceError('Each place must be written as latitude,longitude')
        try:
            latitude, longitude = float(parts[0]), float(parts[1])
        except ValueError:
            raise SourceError('Each place must be written as latitude,longitude')
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise SourceError('A place coordinate is outside its permitted range')
        places.append({'label': _first(params, 'label') or (str(latitude) + ', ' + str(longitude)),
                       'latitude': latitude, 'longitude': longitude})
    return places


def dispatch(foundation, path, params):
    """Route a product view. Raises SourceError for an unknown view or a bad parameter."""
    if path == '/api/overview':
        return overview(foundation, _places_param(params), refresh=_flag(params, 'refresh'))
    if path == '/api/warnings/national':
        return warnings_national(foundation, refresh=_flag(params, 'refresh'))
    if path == '/api/warnings/place':
        latitude, longitude = _point_params(params)
        return warnings_place(foundation, latitude, longitude, refresh=_flag(params, 'refresh'))
    if path == '/api/observations/near':
        latitude, longitude = _point_params(params)
        return observations_bundle(foundation, latitude, longitude,
                                   radius_km=_float(params, 'radius_km', 150.0, low=1.0, high=600.0),
                                   limit=_int(params, 'limit', 6, low=1, high=25),
                                   refresh=_flag(params, 'refresh'))
    if path == '/api/observations/network':
        latitude, longitude = _point_params(params)
        kind = _first(params, 'kind', 'metar')
        if kind not in ('metar', 'aws'):
            raise SourceError('Use metar or aws')
        return observations_near(foundation, latitude, longitude, kind=kind,
                                 radius_km=_float(params, 'radius_km', 150.0, low=1.0, high=600.0),
                                 limit=_int(params, 'limit', 10, low=1, high=50),
                                 refresh=_flag(params, 'refresh'))
    if path == '/api/radar':
        return radar_status(foundation, refresh=_flag(params, 'refresh'))
    if path == '/api/basins':
        return river_basins(foundation, refresh=_flag(params, 'refresh'))
    if path == '/api/forecast':
        latitude, longitude = _point_params(params)
        return forecast(foundation, latitude, longitude,
                        days=_int(params, 'days', 3, low=1, high=7),
                        source=_first(params, 'source', 'hourly_forecast'),
                        refresh=_flag(params, 'refresh'))
    if path == '/api/forecast/changes':
        latitude, longitude = _point_params(params)
        return forecast_changes(latitude, longitude, limit=_int(params, 'limit', 40, low=1, high=200))
    if path == '/api/marine':
        latitude, longitude = _point_params(params)
        return marine(foundation, latitude, longitude, days=_int(params, 'days', 3, low=1, high=7),
                      refresh=_flag(params, 'refresh'))
    if path == '/api/river':
        latitude, longitude = _point_params(params)
        return river(foundation, latitude, longitude, days=_int(params, 'days', 3, low=1, high=7),
                     refresh=_flag(params, 'refresh'))
    if path == '/api/aviation':
        raw = _first(params, 'icao')
        if not raw:
            raise SourceError('Give one or more four-letter ICAO codes')
        kind = _first(params, 'kind', 'metar')
        if kind not in ('metar', 'taf'):
            raise SourceError('Use metar or taf')
        stations = [code.strip().upper() for code in str(raw).split(',') if code.strip()]
        return aviation(foundation, stations, kind=kind, refresh=_flag(params, 'refresh'))
    if path == '/api/now':
        latitude, longitude = _point_params(params)
        return now_view(foundation, latitude, longitude, refresh=_flag(params, 'refresh'))
    if path == '/api/ensemble':
        latitude, longitude = _point_params(params)
        raw = _first(params, 'variable') or ''
        variables = [name.strip() for name in str(raw).split(',') if name.strip()] or None
        threshold = (_float(params, 'threshold', None, low=0.0)
                     if _first(params, 'threshold') not in (None, '') else None)
        return ensemble(foundation, latitude, longitude,
                        days=_int(params, 'days', 3, low=1, high=7),
                        model=_first(params, 'model', 'gfs025'), variables=variables,
                        threshold=threshold, refresh=_flag(params, 'refresh'))
    if path == '/api/air-quality':
        latitude, longitude = _point_params(params)
        raw = _first(params, 'variable') or ''
        variables = [name.strip() for name in str(raw).split(',') if name.strip()] or None
        return air_quality(foundation, latitude, longitude,
                           days=_int(params, 'days', 3, low=1, high=7),
                           variables=variables, refresh=_flag(params, 'refresh'))
    if path == '/api/personas':
        return personas_view()
    if path == '/api/places/search':
        return places_search(_first(params, 'q', ''), limit=_int(params, 'limit', 12, low=1, high=30))
    if path == '/api/map/layers':
        return map_manifest()
    return dispatch_extra(foundation, path, params)


def _pass(record, keys):
    return {key: record[key] for key in keys if key in record}


def alert_brief_view(foundation, latitude, longitude, day=None, refresh=False):
    """One place, one day, and what the official product says - as a shareable brief."""
    from .alert_brief import compose
    view = warnings_place(foundation, latitude, longitude, refresh=refresh)
    try:
        relay = cap_state(foundation, refresh=False)
    except (SourceError, ValueError, OSError):
        relay = None
    brief = compose(view, relay, day_number=day)
    status = 'ok' if brief.get('status') == 'ok' else 'unavailable'
    limitations = list(brief.get('limitations') or [])
    if status != 'ok':
        limitations = limitations + [str(brief.get('why') or 'no brief was composed')]
    return envelope('warnings.alert_brief', status, brief,
                    sources=brief.get('sources') or [],
                    coverage={'district': (brief.get('place') or {}).get('district'),
                              'day': (brief.get('day') or {}).get('day'),
                              'relay_messages': (brief.get('relay') or {}).get('messages')},
                    limitations=limitations,
                    not_established=[item for item in brief.get('not_established') or []][:8])


def cap_state(foundation, refresh=False):
    """The IMD-labelled CAP relay state, reported on its own and never merged with district guidance."""
    packet = foundation.cap(refresh=refresh)
    records = packet.get('records') or []
    assessment = packet.get('lifecycle_assessment') or {}
    meta = packet.get('provenance') or {}
    latest = max(records, key=lambda message: str(message.get('sent') or '')) if records else None
    return envelope('warnings.cap', 'ok',
                    {'messages': len(records),
                     'eligible_by_lifecycle': assessment.get('eligible_by_lifecycle'),
                     'latest_sent': (latest or {}).get('sent'),
                     'delivery': meta.get('delivery'),
                     'records': [_pass(record, ('identifier', 'sender', 'sent', 'status', 'msg_type', 'event',
                                                'severity', 'certainty', 'urgency', 'onset', 'expires', 'areas'))
                                 for record in records]},
                    sources=[source_entry('S06', meta)],
                    coverage={'messages': len(records)},
                    limitations=['The relay reports rainfall alerts produced by the National Weather Forecasting Centre; it is not the whole national warning picture.',
                                 'CAP geographic applicability to a place is not computed here and is not established.',
                                 'An empty eligible set is not an all-clear: a reachable feed is not evidence that nothing is in force.'],
                    not_established=['Origin authentication of the relay is not established, so this is a source assessment and not an alert.'])


def settings_view():
    from .capabilities import CAPABILITIES
    products = registry_products()
    used = []
    for capability in CAPABILITIES:
        for source_id in capability.get('sources') or []:
            if source_id in used:
                continue
            used.append(source_id)
    sources = []
    for source_id in sorted(used):
        entry = products.get(source_id, {})
        sources.append({'source_id': source_id, 'product': entry.get('product'),
                        'integration_status': (entry.get('integration') or {}).get('status') or entry.get('evidence_stage'),
                        'user_review': entry.get('user_review'), 'usage_terms': entry.get('usage_terms'),
                        'selection': entry.get('selection')})
    from .providers import RULE_MODEL, free_model_choices, key_source
    choices = free_model_choices()
    configured = key_source() != 'not configured'
    provider = {'rules_floor': {'model': RULE_MODEL, 'available': True,
                                'detail': 'the core question shapes are planned with no model at all'},
                 'openrouter': {'configured': configured, 'key_source': key_source(),
                                'routing_order': list(choices.get('routing_order') or []),
                                'refused': list(choices.get('refused') or []),
                                'note': ('Only ids ending in :free are routed. The order is a capability judgement for this workload, '
                                         'most capable first, not a provider statement, and only a keyed probe measures what the '
                                         'account can actually reach.')},
                 'set_key_command': 'python3 scripts/models.py --set-key',
                 'probe_command': 'python3 scripts/models.py --probe-free',
                 'key_note': ('The key is written to local configuration on this machine with owner-only permissions, is never sent '
                              'anywhere except the provider it belongs to, and is never printed by the workspace.')}
    return envelope('settings.capabilities', 'ok',
                    {'capabilities': [{key: value for key, value in capability.items() if key != 'sources'}
                                      for capability in CAPABILITIES],
                     'sources': sources,
                     'registered_sources': len(products),
                     'connected_sources': len([s for s in sources if s['integration_status'] == 'prototype_adapter_tested']),
                     'provider': provider},
                    sources=[],
                    coverage={'capabilities': len(CAPABILITIES), 'sources_in_use': len(sources)},
                    limitations=['A registered source is not a serving approval, and a connected adapter is not operational readiness.',
                                 'The model routing order is a capability judgement for this workload, not a provider statement; only the keyed probe measures availability.',
                                 'Every source remains user_review pending with its usage terms unresolved.'],
                    not_established=['No user-level acceptance benchmark exists for every promised operation or language.',
                                     'Voice, mobile acceptance and hosted distribution remain incomplete.'])


def _climate_database():
    from .publications import verify_database
    pin = json.loads((ROOT / 'data/registry/historical-publications.json').read_text(encoding='utf-8'))
    entry = pin['publications']['S27']
    path = ROOT / entry['database']
    verify_database(path, entry['manifest_sha256'])
    return path


def climate_index():
    import sqlite3
    path = _climate_database()
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute('select state, district, count(*) as years, min(year), max(year) '
                                 'from rainfall group by state, district order by state, district').fetchall()
    finally:
        connection.close()
    states = {}
    for state, district, years, first, last in rows:
        states.setdefault(state, []).append({'district': district, 'years': years, 'first_year': first, 'last_year': last})
    return envelope('climate.index', 'ok' if states else 'unavailable',
                    {'states': [{'state': state, 'districts': sorted(items, key=lambda item: item['district'])}
                                for state, items in sorted(states.items())],
                     'districts': len(rows)},
                    sources=[source_entry('S27', {'url': (registry_products().get('S27') or {}).get('access_url')},
                                          product='Supplied district historical rainfall collection')],
                    coverage={'states': len(states), 'districts': len(rows)},
                    limitations=['Published district tables as transcribed, not a boundary-harmonised series.',
                                 'Renamed and merged districts appear under the source spelling and are not reconciled to a later administrative version.'],
                    not_established=['No attribution, homogenisation or climate projection is performed on this record.'])


def climate_series(district, state=None, years=None, parameter='rainfall'):
    import sqlite3
    if not district or not isinstance(district, str):
        raise SourceError('A district is required')
    if parameter not in ('rainfall',):
        raise SourceError('Only the published rainfall record is connected')
    path = _climate_database()
    connection = sqlite3.connect(path)
    try:
        query = 'select year, state, district, series_id, source_row, source_file, asset_sha256, payload from rainfall where district = ?'
        params = [district]
        if state:
            query += ' and state = ?'
            params.append(state)
        query += ' order by year'
        rows = connection.execute(query, params).fetchall()
    finally:
        connection.close()
    if not rows:
        return envelope('climate.series', 'unavailable', {'district': district, 'state': state, 'points': []},
                        sources=[source_entry('S27', {'url': (registry_products().get('S27') or {}).get('access_url')})],
                        limitations=['The stored series does not carry this district name.'],
                        not_established=['This is not evidence that no rainfall was recorded; the source spelling may differ.'])
    points = []
    for year, row_state, row_district, series_id, source_row, source_file, asset_sha256, payload in rows:
        if years and not (int(years[0]) <= year <= int(years[1])):
            continue
        try:
            values = json.loads(payload)
        except (TypeError, ValueError):
            values = {}
        points.append({'year': year, 'value': values.get('annual_mm'), 'unit': 'mm',
                       'series_id': series_id, 'source_page': values.get('source_page'),
                       'source_row': source_row, 'source_file': source_file,
                       'asset_sha256_prefix': str(asset_sha256 or '')[:12],
                       'quality_flags': values.get('quality_flags') or '',
                       'label': values.get('district_table_label')})
    return envelope('climate.series', 'ok' if points else 'unavailable',
                    {'district': district, 'state': state or rows[0][1], 'parameter': parameter,
                     'series_id': rows[0][3], 'points': points,
                     'first_year': points[0]['year'] if points else None,
                     'last_year': points[-1]['year'] if points else None},
                    sources=[source_entry('S27', {'url': (registry_products().get('S27') or {}).get('access_url')},
                                          product='Supplied district historical rainfall collection')],
                    coverage={'years': len(points)},
                    limitations=['Values are the published annual totals as transcribed, in millimetres, and missing years are gaps rather than zeros.',
                                 'The source table label may differ from the requested district spelling.'],
                    not_established=['No trend, anomaly or attribution is asserted by this view; a descriptive slope would still not be a projection.'])


def advisory_states(foundation, language='en'):
    from . import advisories
    packet = advisories.catalog(foundation.store, language=language)
    return envelope('advisories.states', 'ok' if packet.get('records') else 'unavailable',
                    {'states': packet.get('records') or []},
                    sources=[source_entry('S57', packet.get('provenance'))],
                    coverage=packet.get('coverage'),
                    limitations=list(packet.get('limitations') or []),
                    not_established=['A listed state is a directory entry, not proof that a bulletin was issued today.'])


def advisory_districts(foundation, state, language='en'):
    from . import advisories
    if not state:
        raise SourceError('A state is required')
    packet = advisories.catalog(foundation.store, state=state, language=language)
    return envelope('advisories.districts', 'ok' if packet.get('records') else 'unavailable',
                    {'state': state, 'districts': packet.get('records') or []},
                    sources=[source_entry('S57', packet.get('provenance'))],
                    coverage=packet.get('coverage'),
                    limitations=list(packet.get('limitations') or []),
                    not_established=['A listed district is a directory entry, not proof of a current bulletin.'])


ADVISORY_EXTRA_PATHS = ('/api/warnings/cap', '/api/warnings/alert-brief', '/api/settings/capabilities', '/api/climate/index', '/api/climate/series',
                        '/api/advisories/states', '/api/advisories/districts')


def dispatch_extra(foundation, path, params):
    """Product views added after the first router. Kept beside it so both stay readable."""
    if path == '/api/warnings/cap':
        return cap_state(foundation, refresh=_flag(params, 'refresh'))
    if path == '/api/warnings/alert-brief':
        latitude, longitude = _point_params(params)
        day = _int(params, 'day')
        if day is not None and not 1 <= day <= 5:
            raise SourceError('Ask for a published day between 1 and 5')
        return alert_brief_view(foundation, latitude, longitude, day=day, refresh=_flag(params, 'refresh'))
    if path == '/api/settings/capabilities':
        return settings_view()
    if path == '/api/climate/index':
        return climate_index()
    if path == '/api/climate/series':
        years = None
        first, last = _int(params, 'from'), _int(params, 'to')
        if first is not None and last is not None:
            years = (first, last)
        return climate_series(_first(params, 'district', ''), _first(params, 'state'), years)
    if path == '/api/advisories/states':
        return advisory_states(foundation, _first(params, 'language', 'en'))
    if path == '/api/advisories/districts':
        return advisory_districts(foundation, _first(params, 'state'), _first(params, 'language', 'en'))
    raise SourceError('Unknown product view')
