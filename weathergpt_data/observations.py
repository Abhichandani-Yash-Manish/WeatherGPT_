"""Official station observations: nearest AWS and METAR stations, never a forecast.

Observations and forecasts are different products and are never substituted for
one another here. A station row names its station, its distance from the asked
point, its own observation instant and its own age, and a stale station is
reported as stale rather than quietly presented as current.

Two source traps are handled here, because either would otherwise publish a
fabricated observation time:

* imd:aws_data_layer carries a placeholder time field fixed at 1970-01-01 for
  every station. The instant is therefore taken from the dat date field and the
  update_time string, and the placeholder is reported as unusable instead of
  being displayed.
* several imd:metar_data_layer rows are years old, so staleness is decided per
  row and carried on the row.

This layer does not state units, so no unit is asserted: every value is reported
verbatim with the field name it came from.
"""
import math
import re
from datetime import datetime, timedelta, timezone

from .transport import SourceError, stamp

AWS_LAYER = 'imd:aws_data_layer'
METAR_LAYER = 'imd:metar_data_layer'
AWS_FIELDS = ('rainfall', 'temp', 'temp_min', 'temp_max', 'rh', 'windspeed', 'winddir', 'mslp', 'nebulosity', 'weather')
METAR_FIELDS = ('temp', 'dewtemp', 'mslp', 'winddir', 'windsp', 'rh', 'visibility', 'nebulosity', 'weather',
                '3hrlyrain', '6hrlyrain', '12hrlyrain', '24hrlyrain')
PLACEHOLDER_YEAR = 1970
STALE_METAR_AFTER = timedelta(hours=6)
STALE_AWS_AFTER = timedelta(hours=24)
NULLISH = {'', 'null', 'NULL', 'NA', 'N/A', '-'}


def parser_for(label, low, high):
    def parse(data, meta):
        if not isinstance(data, dict) or data.get('type') != 'FeatureCollection':
            raise ValueError(label + ': expected a FeatureCollection')
        features = data.get('features')
        if not isinstance(features, list) or not features:
            raise ValueError(label + ': no features')
        total = data.get('totalFeatures')
        if total is not None and int(total) != len(features):
            raise ValueError(label + ': truncated, ' + str(total) + ' reported vs ' + str(len(features)))
        if not low <= len(features) <= high:
            raise ValueError(label + ': ' + str(len(features)) + ' features outside ' + str((low, high)))
        for feature in features:
            properties = feature.get('properties')
            if not isinstance(properties, dict) or not isinstance(feature.get('geometry'), dict):
                raise ValueError(label + ': malformed station feature')
            if feature['geometry'].get('type') != 'Point':
                raise ValueError(label + ': station geometry must be a Point')
    return parse


def clean(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return None if text in NULLISH else text
    return value


def number(value):
    value = clean(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def station_identity(kind, properties, geometry):
    name = clean(properties.get('station')) or clean(properties.get('station_name'))
    code = clean(properties.get('station_id')) or clean(properties.get('id')) or clean(properties.get('call_sign'))
    if not name and not code:
        raise SourceError(kind + ' station without a name or an identifier')
    coordinates = geometry.get('coordinates') or []
    if len(coordinates) < 2:
        raise SourceError(kind + ' station without coordinates')
    return (name or str(code)), (str(code) if code else None), float(coordinates[0]), float(coordinates[1])


def metar_instant(properties):
    day = clean(properties.get('dat'))
    clock = clean(properties.get('utc'))
    if not day or not clock:
        return None, 'the layer did not supply both a date and a UTC time'
    match = re.match(r'^(\d{4})-(\d{2})-(\d{2})Z?$', day)
    if not match:
        return None, 'the date field is not a plain UTC date'
    try:
        hour, minute = [int(part) for part in str(clock).split(':')[:2]]
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), hour, minute, tzinfo=timezone.utc), None
    except (ValueError, TypeError):
        return None, 'the date and time fields could not be combined'


def aws_instant(properties):
    notes = []
    placeholder = clean(properties.get('time'))
    if placeholder and str(placeholder).startswith(str(PLACEHOLDER_YEAR)):
        notes.append('the layer carries a ' + str(PLACEHOLDER_YEAR) + ' placeholder time field, which is not the observation instant')
    moment = None
    day = clean(properties.get('dat'))
    if day:
        match = re.match(r'^(\d{4})-(\d{2})-(\d{2})Z?$', day)
        if match:
            moment = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), tzinfo=timezone.utc)
    update = clean(properties.get('update_time'))
    if moment is None and update:
        try:
            moment = datetime.fromisoformat(str(update).replace(' ', 'T')).replace(tzinfo=timezone.utc)
            notes.append('the observation instant was taken from an update timestamp that states no timezone')
        except ValueError:
            moment = None
    if moment is None:
        notes.append('no usable observation instant was supplied')
    return moment, update, placeholder, notes


def normalise(kind, properties, geometry, now=None):
    name, code, longitude, latitude = station_identity(kind, properties, geometry)
    if kind == 'metar':
        moment, problem = metar_instant(properties)
        notes = [problem] if problem else []
        local_update, placeholder = None, None
        fields = METAR_FIELDS
    else:
        moment, local_update, placeholder, notes = aws_instant(properties)
        fields = AWS_FIELDS
    parameters = []
    for field in fields:
        value = clean(properties.get(field))
        if value is None:
            continue
        parameters.append({'field': field, 'value': value, 'unit': None, 'unit_stated_by_source': False})
    return {'kind': kind, 'name': name, 'station_code': code, 'latitude': latitude, 'longitude': longitude,
            'observed_at_utc': stamp(moment) if moment else None,
            'observed_date_utc': moment.date().isoformat() if moment else None,
            'reported_local_update': local_update, 'unusable_time_field': placeholder,
            'time_notes': notes, 'parameters': parameters, 'source_id': 'S63',
            'source_layer': METAR_LAYER if kind == 'metar' else AWS_LAYER,
            'locator_prefix': '$.features'}


def load(foundation, kind='metar', refresh=False, ttl=1800):
    """Read one station layer. Returns (rows, meta, rejected)."""
    if kind not in ('metar', 'aws'):
        raise SourceError('Unsupported station layer: ' + str(kind))
    layer = METAR_LAYER if kind == 'metar' else AWS_LAYER
    low, high = (100, 400) if kind == 'metar' else (1500, 3000)
    params = {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature', 'typeName': layer,
              'outputFormat': 'application/json', 'srsName': 'EPSG:4326'}
    data, meta = foundation.get('S63', 'https://reactjs.imd.gov.in/geoserver/wfs', params,
                                product_parser=parser_for(kind, low, high), ttl=ttl, refresh=refresh,
                                max_bytes=200_000_000)
    rows, rejected = [], []
    for index, feature in enumerate(data['features']):
        try:
            row = normalise(kind, feature['properties'], feature['geometry'])
        except SourceError as exc:
            rejected.append({'index': index, 'reason': str(exc)})
            continue
        row['source_locator'] = '$.features[' + str(index) + ']'
        rows.append(row)
    return rows, meta, rejected


def distance_km(latitude, longitude, station_latitude, station_longitude):
    radius = 6371.0
    phi1, phi2 = math.radians(latitude), math.radians(station_latitude)
    delta_phi = math.radians(station_latitude - latitude)
    delta_lambda = math.radians(station_longitude - longitude)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def nearest(rows, latitude, longitude, radius_km=150.0, limit=10, now=None):
    """Nearest stations by great-circle distance, each carrying its own age and staleness."""
    now = now or datetime.now(timezone.utc)
    found = []
    for row in rows:
        span = distance_km(latitude, longitude, row['latitude'], row['longitude'])
        if span > radius_km:
            continue
        entry = dict(row)
        entry['distance_km'] = round(span, 2)
        if row['observed_at_utc']:
            moment = datetime.fromisoformat(row['observed_at_utc'])
            age = (now - moment).total_seconds() / 60.0
            entry['age_minutes'] = round(age, 1)
            window = STALE_METAR_AFTER if row['kind'] == 'metar' else STALE_AWS_AFTER
            entry['stale'] = age > window.total_seconds() / 60.0
        else:
            entry['age_minutes'] = None
            entry['stale'] = True
        found.append(entry)
    found.sort(key=lambda item: item['distance_km'])
    return found[:limit]


LIMITATIONS = [
    'A station observation describes its station, not the surrounding district or city.',
    'No unit is asserted for any value: this layer does not state units, so values are reported verbatim.',
    'A missing station near a point means no connected station reported there, not that no weather occurred.',
    'Observations and forecasts are separate products; a forecast value is never shown as an observation.',
    'Station identity here comes from the source layer and has not been matched to an official station register.',
]
