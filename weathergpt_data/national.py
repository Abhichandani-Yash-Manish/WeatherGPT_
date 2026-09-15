"""National network and basin status from official IMD layers.

Two collections that a disaster-management surface needs and that no adapter
previously reached:

* imd:radar_station_status - the radar network and each station's reported state.
* imd:indian_river_basin   - sub-basin outlines carrying day fields.

The basin day fields are exposed verbatim and are explicitly not interpreted.
This layer does not document what day1, day2 and day3 mean, and inventing a
severity or a flood class from them would be a fabricated warning. A reader sees
the source text and the fact that its meaning is not established here.
"""
from .transport import SourceError

RADAR_LAYER = 'imd:radar_station_status'
BASIN_LAYER = 'imd:indian_river_basin'
DAY_FIELDS = ('day1', 'day2', 'day3')
RADAR_FIELDS = ('code', 'station', 'status', 'remarks', 'last_updated_date', 'last_updated_time', 'checked_at')
BASIN_FIELDS = ('BASIN', 'SUBBASIN', 'AREA_SQKM', 'FMO', 'FMO_Code', 'River_Basi')


def parser_for(label, low, high, geometry_type=None):
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
            if not isinstance(feature.get('properties'), dict) or not isinstance(feature.get('geometry'), dict):
                raise ValueError(label + ': malformed feature')
            if geometry_type and feature['geometry'].get('type') != geometry_type:
                raise ValueError(label + ': expected ' + geometry_type + ' geometry')
    return parse


def text(value):
    if value is None:
        return None
    text_value = str(value).strip()
    return None if text_value in {'', 'NULL', 'null', 'NA'} else text_value


def radar_status(foundation, refresh=False, ttl=600):
    params = {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature', 'typeName': RADAR_LAYER,
              'outputFormat': 'application/json', 'srsName': 'EPSG:4326'}
    data, meta = foundation.get('S63', 'https://reactjs.imd.gov.in/geoserver/wfs', params,
                                product_parser=parser_for('radar', 30, 60, 'Point'), ttl=ttl, refresh=refresh,
                                max_bytes=40_000_000)
    stations, rejected = [], []
    for index, feature in enumerate(data['features']):
        properties = feature['properties']
        coordinates = feature['geometry'].get('coordinates') or []
        name = text(properties.get('station'))
        code = text(properties.get('code'))
        if not name and not code:
            rejected.append({'index': index, 'reason': 'no station name or code'})
            continue
        if len(coordinates) < 2:
            rejected.append({'index': index, 'reason': 'no coordinates'})
            continue
        # The feature geometry is a GeoJSON pair, so the first element is the longitude.
        # Measured 15 September 2026: the layer serves (77.28, 34.28) for Leh, and all 39
        # stations were outside India while the pair was read in the served order but inside
        # it read as (longitude, latitude). The other station layers in this workspace are
        # already read this way (observations.station_identity).
        row = {'name': name or code, 'code': code, 'longitude': float(coordinates[0]), 'latitude': float(coordinates[1]),
               'source_id': 'S63', 'source_locator': '$.features[' + str(index) + ']'}
        for field in RADAR_FIELDS:
            row[field] = text(properties.get(field))
        stations.append(row)
    return {'stations': stations, 'rejected': rejected, 'meta': meta, 'layer': RADAR_LAYER,
            'as_of_utc': meta.get('retrieved_at_utc')}


def river_basins(foundation, refresh=False, ttl=3600):
    params = {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature', 'typeName': BASIN_LAYER,
              'outputFormat': 'application/json', 'srsName': 'EPSG:4326'}
    data, meta = foundation.get('S63', 'https://reactjs.imd.gov.in/geoserver/wfs', params,
                                product_parser=parser_for('basins', 200, 240), ttl=ttl, refresh=refresh,
                                max_bytes=200_000_000)
    basins, rejected = [], []
    for index, feature in enumerate(data['features']):
        properties = feature['properties']
        name = text(properties.get('SUBBASIN')) or text(properties.get('River_Basi'))
        if not name:
            rejected.append({'index': index, 'reason': 'no sub-basin name'})
            continue
        row = {'name': name, 'source_id': 'S63', 'source_locator': '$.features[' + str(index) + ']'}
        for field in BASIN_FIELDS:
            row[field.lower()] = text(properties.get(field))
        row['day_fields'] = {field: text(properties.get(field)) for field in DAY_FIELDS}
        basins.append(row)
    listed = [row for row in basins if any(row['day_fields'].values())]
    return {'basins': basins, 'with_day_fields': len(listed), 'rejected': rejected, 'meta': meta, 'layer': BASIN_LAYER,
            'as_of_utc': meta.get('retrieved_at_utc')}


LIMITATIONS = [
    'Radar status reports the network as the source publishes it and is not a rainfall or nowcast product.',
    'Sub-basin day fields are reproduced verbatim; this layer does not document their meaning, so no flood class, '
    'severity or warning level is derived from them.',
    'A basin outline is not a gauge, a river reach or an administrative boundary, and it is not a flood warning.',
]
