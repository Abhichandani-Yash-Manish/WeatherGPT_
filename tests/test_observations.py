"""Station observation reader: identity, time honesty, distance and staleness.

Offline component checks over synthetic features. They do not call the network
and they are not an acceptance test of the live station layers.
"""
import unittest
from datetime import datetime, timedelta, timezone

from weathergpt_data import observations as obs
from weathergpt_data.transport import SourceError

NOW = datetime(2026, 9, 14, 16, 0, tzinfo=timezone.utc)


def point(longitude, latitude):
    return {'type': 'Point', 'coordinates': [longitude, latitude]}


def metar(**overrides):
    properties = {'station_id': 'VAAH', 'station_name': 'AHMEDABAD', 'dat': '2026-09-14Z', 'utc': '15:30',
                  'temp': 23, 'rh': '89.0', 'windsp': '6.0', 'nebulosity': 'scattered clouds at 2500 feet',
                  'visibility': '7000.0', 'weather': None}
    properties.update(overrides)
    return properties


def aws(**overrides):
    properties = {'id': '99935', 'station': 'AHMEDABAD', 'dat': '2026-09-14Z',
                  'time': '1970-01-01T12:15:00Z', 'update_time': '2026-09-14 15:20:04',
                  'rainfall': '0.0', 'temp': '29.9', 'temp_min': '27.0', 'temp_max': '32.8',
                  'rh': 'NULL', 'windspeed': '5.9', 'mslp': None}
    properties.update(overrides)
    return properties


class IdentityTests(unittest.TestCase):
    def test_identity_and_coordinates_are_read(self):
        row = obs.normalise('metar', metar(), point(72.63, 23.07))
        self.assertEqual(row['name'], 'AHMEDABAD')
        self.assertEqual(row['station_code'], 'VAAH')
        self.assertAlmostEqual(row['latitude'], 23.07)
        self.assertAlmostEqual(row['longitude'], 72.63)

    def test_aws_identity_falls_back_to_the_station_id(self):
        row = obs.normalise('aws', aws(station=None), point(72.6, 23.0))
        self.assertEqual(row['station_code'], '99935')
        self.assertEqual(row['name'], '99935')

    def test_a_station_without_identity_is_refused(self):
        with self.assertRaises(SourceError):
            obs.normalise('aws', aws(station=None, id=None, call_sign=None), point(72.6, 23.0))

    def test_a_station_without_coordinates_is_refused(self):
        with self.assertRaises(SourceError):
            obs.normalise('metar', metar(), {'type': 'Point', 'coordinates': []})


class MetarTimeTests(unittest.TestCase):
    def test_the_instant_comes_from_the_date_and_utc_fields(self):
        row = obs.normalise('metar', metar(), point(72.6, 23.0))
        self.assertEqual(row['observed_at_utc'], '2026-09-14T15:30:00+00:00')
        self.assertEqual(row['observed_date_utc'], '2026-09-14')

    def test_a_missing_time_field_is_reported_not_invented(self):
        row = obs.normalise('metar', metar(utc=None), point(72.6, 23.0))
        self.assertIsNone(row['observed_at_utc'])
        self.assertTrue(any('date and a UTC time' in note for note in row['time_notes']))

    def test_an_unparseable_date_is_reported(self):
        row = obs.normalise('metar', metar(dat='14-09-2026'), point(72.6, 23.0))
        self.assertIsNone(row['observed_at_utc'])
        self.assertTrue(row['time_notes'])


class AwsTimeTests(unittest.TestCase):
    def test_the_placeholder_year_is_never_used_as_the_instant(self):
        row = obs.normalise('aws', aws(), point(72.6, 23.0))
        self.assertEqual(row['observed_at_utc'], '2026-09-14T00:00:00+00:00')
        self.assertEqual(row['unusable_time_field'], '1970-01-01T12:15:00Z')
        self.assertTrue(any('placeholder' in note for note in row['time_notes']))

    def test_the_placeholder_is_reported_when_no_other_instant_exists(self):
        row = obs.normalise('aws', aws(dat=None, update_time=None), point(72.6, 23.0))
        self.assertIsNone(row['observed_at_utc'])
        self.assertEqual(row['unusable_time_field'], '1970-01-01T12:15:00Z')
        self.assertTrue(any('no usable observation instant' in note for note in row['time_notes']))

    def test_the_update_string_is_used_only_with_a_timezone_note(self):
        row = obs.normalise('aws', aws(dat=None, update_time='2026-09-14 15:20:04'), point(72.6, 23.0))
        self.assertEqual(row['observed_at_utc'], '2026-09-14T15:20:04+00:00')
        self.assertEqual(row['reported_local_update'], '2026-09-14 15:20:04')
        self.assertTrue(any('states no timezone' in note for note in row['time_notes']))


class ParameterTests(unittest.TestCase):
    def test_no_unit_is_ever_asserted(self):
        for row in (obs.normalise('metar', metar(), point(72.6, 23.0)), obs.normalise('aws', aws(), point(72.6, 23.0))):
            for parameter in row['parameters']:
                self.assertIsNone(parameter['unit'])
                self.assertFalse(parameter['unit_stated_by_source'])

    def test_nullish_values_are_dropped_rather_than_shown_as_zero(self):
        row = obs.normalise('aws', aws(rh='NULL', mslp=None), point(72.6, 23.0))
        fields = {parameter['field'] for parameter in row['parameters']}
        self.assertNotIn('rh', fields)
        self.assertNotIn('mslp', fields)

    def test_text_parameters_survive_verbatim(self):
        row = obs.normalise('metar', metar(), point(72.6, 23.0))
        cloud = [parameter for parameter in row['parameters'] if parameter['field'] == 'nebulosity'][0]
        self.assertEqual(cloud['value'], 'scattered clouds at 2500 feet')


class NearestTests(unittest.TestCase):
    def rows(self):
        return [obs.normalise('metar', metar(station_id='A', station_name='NEAR'), point(72.6, 23.0)),
                obs.normalise('metar', metar(station_id='B', station_name='FAR', utc='09:00'), point(73.6, 23.0)),
                obs.normalise('aws', aws(id='C', station='AWSNEAR', dat='2026-09-13Z'), point(72.65, 23.02))]

    def test_results_are_ordered_by_distance_and_filtered_by_radius(self):
        found = obs.nearest(self.rows(), 23.0, 72.6, radius_km=20, limit=10, now=NOW)
        self.assertEqual([row['station_code'] for row in found], ['A', 'C'])
        self.assertLess(found[0]['distance_km'], found[1]['distance_km'])

    def test_the_limit_is_respected(self):
        found = obs.nearest(self.rows(), 23.0, 72.6, radius_km=500, limit=1, now=NOW)
        self.assertEqual(len(found), 1)

    def test_staleness_is_decided_per_row_and_per_kind(self):
        found = obs.nearest(self.rows(), 23.0, 72.6, radius_km=20, limit=10, now=NOW)
        by_code = {row['station_code']: row for row in found}
        self.assertFalse(by_code['A']['stale'], 'a METAR from 30 minutes ago is current')
        self.assertTrue(by_code['C']['stale'], 'an AWS dated the previous day is stale beyond its window')

    def test_a_row_without_an_instant_is_stale_not_current(self):
        rows = [obs.normalise('metar', metar(utc=None), point(72.6, 23.0))]
        found = obs.nearest(rows, 23.0, 72.6, now=NOW)
        self.assertTrue(found[0]['stale'])
        self.assertIsNone(found[0]['age_minutes'])

    def test_distance_is_great_circle(self):
        self.assertAlmostEqual(obs.distance_km(23.0, 72.6, 23.0, 72.6), 0.0, places=6)
        span = obs.distance_km(23.0, 72.6, 23.0, 73.6)
        self.assertGreater(span, 100)
        self.assertLess(span, 105)


class ParserTests(unittest.TestCase):
    def test_a_truncated_collection_is_refused(self):
        with self.assertRaises(ValueError):
            obs.parser_for('metar', 1, 10)({'type': 'FeatureCollection', 'totalFeatures': 5,
                                            'features': [{'properties': {}, 'geometry': {'type': 'Point', 'coordinates': [1, 1]}}]}, {})

    def test_an_out_of_range_count_is_refused(self):
        with self.assertRaises(ValueError):
            obs.parser_for('metar', 100, 400)({'type': 'FeatureCollection', 'features': [
                {'properties': {}, 'geometry': {'type': 'Point', 'coordinates': [1, 1]}}]}, {})

    def test_non_point_geometry_is_refused(self):
        with self.assertRaises(ValueError):
            obs.parser_for('aws', 1, 10)({'type': 'FeatureCollection', 'features': [
                {'properties': {}, 'geometry': {'type': 'Polygon', 'coordinates': []}}]}, {})


class LimitationTests(unittest.TestCase):
    def test_the_limitations_state_what_an_observation_is_not(self):
        joined = ' '.join(obs.LIMITATIONS)
        self.assertIn('not the surrounding district', joined)
        self.assertIn('not that no weather occurred', joined)
        self.assertIn('never shown as an observation', joined)
        self.assertIn('no unit is asserted', joined.lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
