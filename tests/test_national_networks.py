"""National network layers: the radar status board and the river sub-basin list.

Offline component checks over synthetic features. They do not call the network and they
are not acceptance of the live layers; what they pin is the served coordinate order, the
rejection record and that a sub-basin day field is carried verbatim.
"""
import unittest

from weathergpt_data import national


class StubFoundation:
    def __init__(self, features, meta=None):
        self.features = features
        self.meta = meta or {'retrieved_at_utc': '2026-09-15T15:40:03+00:00', 'sha256': 'a' * 64}

    def get(self, source_id, url, params, product_parser=None, ttl=None, refresh=False, max_bytes=None):
        payload = {'type': 'FeatureCollection', 'totalFeatures': len(self.features), 'features': self.features}
        if product_parser:
            product_parser(payload, self.meta)
        return payload, dict(self.meta, source_id=source_id, url=url, params=params, layer=params.get('typeName'))


def radar_feature(longitude, latitude, station='Leh', code='leh', status='0', remarks='The image has not been updated.'):
    return {'type': 'Feature',
            'properties': {'station': station, 'code': code, 'status': status, 'remarks': remarks,
                           'last_updated_date': '04 JUN 2026', 'last_updated_time': '05:10:01 UTC'},
            'geometry': {'type': 'Point', 'coordinates': [longitude, latitude]}}


class RadarStatusTests(unittest.TestCase):
    def test_the_served_geojson_pair_is_read_as_longitude_then_latitude(self):
        rows = [radar_feature(77.28333333, 34.28333333, station='Leh', code='leh')]
        rows += [radar_feature(72.0 + index * 0.1, 20.0 + index * 0.1, station='S' + str(index), code='s' + str(index))
                 for index in range(38)]
        packet = national.radar_status(StubFoundation(rows))
        leh = packet['stations'][0]
        self.assertAlmostEqual(leh['latitude'], 34.28333333, places=6)
        self.assertAlmostEqual(leh['longitude'], 77.28333333, places=6)
        inside = [row for row in packet['stations'] if 6 <= row['latitude'] <= 38.5 and 68 <= row['longitude'] <= 98]
        self.assertEqual(len(inside), len(packet['stations']),
                         'every station must sit inside the country it belongs to')

    def test_a_feature_without_identity_or_coordinates_is_recorded_not_dropped_silently(self):
        rows = [radar_feature(72.0 + index * 0.1, 20.0 + index * 0.1, station='S' + str(index), code='s' + str(index))
                for index in range(30)]
        rows.append(radar_feature(77.2, 34.2, station=None, code=None))
        rows.append({'type': 'Feature', 'properties': {'station': 'NoGeometry', 'code': 'ng'},
                     'geometry': {'type': 'Point', 'coordinates': []}})
        packet = national.radar_status(StubFoundation(rows))
        self.assertEqual(len(packet['stations']), 30)
        self.assertEqual([row['reason'] for row in packet['rejected']],
                         ['no station name or code', 'no coordinates'])


class RiverBasinTests(unittest.TestCase):
    def test_a_day_field_is_carried_verbatim_and_counted(self):
        def basin(name, day1, subbasin='Brahmaputra'):
            return {'type': 'Feature',
                    'properties': {'BASIN': 'Brahmaputra', 'SUBBASIN': name, 'AREA_SQKM': '10472.6',
                                   'FMO': 'GUWAHATI', 'FMO_Code': '12', 'River_Basi': '014',
                                   'day1': day1, 'day2': '', 'day3': ''},
                    'geometry': {'type': 'Point', 'coordinates': [91.0, 26.0]}}
        rows = [basin('Jiabharali at NT road Xing', '2')] + [basin('Basin ' + str(index), None) for index in range(199)]
        packet = national.river_basins(StubFoundation(rows))
        self.assertEqual(len(packet['basins']), 200)
        self.assertEqual(packet['with_day_fields'], 1)
        self.assertEqual(packet['basins'][0]['day_fields'], {'day1': '2', 'day2': None, 'day3': None})
