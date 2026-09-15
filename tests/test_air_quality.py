"""Air-quality normalisation: pollutants and indices stay apart, and nothing is scored."""
import unittest
from datetime import datetime, timezone

from weathergpt_data.adapters import AIR_QUALITY, air_quality
from weathergpt_data.transport import SourceError

UTC = timezone.utc
META = {'source_id': 'S69', 'sha256': 'c' * 64}
POINT = {'latitude': 23.0, 'longitude': 72.6}


def hours(count, start=datetime(2026, 9, 15, 0, 0, tzinfo=UTC)):
    return [int(start.timestamp()) + 3600 * index for index in range(count)]


def payload(values_by_variable, times=None, current=None, offset=0, units=None):
    times = times if times is not None else hours(1)
    units = units if units is not None else {name: AIR_QUALITY[name][0] for name in values_by_variable}
    body = {'latitude': 23.0, 'longitude': 72.6, 'utc_offset_seconds': offset,
            'hourly_units': units, 'hourly': {'time': times, **values_by_variable}}
    if current is not None:
        body['current'] = current
    return body


def records(result):
    return {(record['parameter'], record['aggregation']): record for record in result['records']}


class AirQualityAdapterTests(unittest.TestCase):
    def test_pollutants_and_indices_keep_their_own_units(self):
        body = payload({'pm2_5': [15.3], 'us_aqi': [56]},
                       current={'time': hours(1)[0], 'interval': 3600, 'pm2_5': 14.3, 'us_aqi': 56})
        result = air_quality(body, META, {'pm2_5': AIR_QUALITY['pm2_5'], 'us_aqi': AIR_QUALITY['us_aqi']},
                             POINT)
        row = records(result)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['source_id'], 'S69')
        self.assertEqual(row[('pm2_5', 'instant')]['value'], 15.3)
        self.assertEqual(row[('pm2_5', 'instant')]['unit'], 'μg/m³')
        self.assertEqual(row[('us_aqi', 'instant')]['unit'], 'USAQI')
        self.assertEqual(row[('us_aqi', 'current_instant')]['value'], 56)
        self.assertEqual(result['coverage']['current'], {'pm2_5': 14.3, 'us_aqi': 56})

    def test_a_missing_current_variable_is_unknown_not_zero(self):
        body = payload({'pm2_5': [15.3], 'pm10': [20.0]},
                       current={'time': hours(1)[0], 'interval': 3600, 'pm2_5': 14.3})
        result = air_quality(body, META, {'pm2_5': AIR_QUALITY['pm2_5'], 'pm10': AIR_QUALITY['pm10']}, POINT)
        self.assertIsNone(records(result)[('pm10', 'current_instant')]['value'])
        self.assertIn('source_value_missing', records(result)[('pm10', 'current_instant')]['quality_flags'])

    def test_wrong_unit_is_refused(self):
        body = payload({'pm2_5': [15.3]}, units={'pm2_5': 'mg/m³'})
        with self.assertRaises(SourceError):
            air_quality(body, META, {'pm2_5': AIR_QUALITY['pm2_5']}, POINT)

    def test_missing_variable_is_refused(self):
        body = payload({'pm2_5': [15.3]})
        with self.assertRaises(SourceError):
            air_quality(body, META, {'pm10': AIR_QUALITY['pm10']}, POINT)

    def test_negative_concentration_is_refused(self):
        body = payload({'pm2_5': [-1.0]})
        with self.assertRaises(SourceError):
            air_quality(body, META, {'pm2_5': AIR_QUALITY['pm2_5']}, POINT)

    def test_non_hourly_axis_is_refused(self):
        body = payload({'pm2_5': [1.0, 2.0]}, times=[hours(1)[0], hours(1)[0] + 1800])
        with self.assertRaises(SourceError):
            air_quality(body, META, {'pm2_5': AIR_QUALITY['pm2_5']}, POINT)

    def test_non_utc_offset_is_refused(self):
        body = payload({'pm2_5': [15.3]}, offset=19800)
        with self.assertRaises(SourceError):
            air_quality(body, META, {'pm2_5': AIR_QUALITY['pm2_5']}, POINT)

    def test_incomplete_requested_interval_is_refused(self):
        from datetime import date
        body = payload({'pm2_5': [15.3]})
        with self.assertRaises(SourceError):
            air_quality(body, META, {'pm2_5': AIR_QUALITY['pm2_5']}, POINT,
                        expected_dates=(date(2026, 9, 15), date(2026, 9, 15)))


class FoundationAirQualityTests(unittest.TestCase):
    class Response:
        status = 200
        headers = {'Content-Type': 'application/json'}

        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            return self.body[:size]

    def foundation_with(self, body):
        import json
        import tempfile
        from datetime import datetime as dt
        from weathergpt_data.foundation import Foundation
        from weathergpt_data.transport import Store
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = Store(directory.name, opener=lambda *a, **k: self.Response(json.dumps(body).encode()),
                      clock=lambda: dt(2026, 9, 15, tzinfo=UTC))
        return Foundation(store)

    def test_foundation_fetches_and_normalises_the_reading(self):
        from datetime import datetime as dt
        times = hours(24, start=dt(2026, 9, 15, tzinfo=UTC))
        body = payload({'pm2_5': [10.0] * 24, 'us_aqi': [50] * 24}, times=times,
                       current={'time': times[0], 'interval': 3600, 'pm2_5': 10.0, 'us_aqi': 50})
        result = self.foundation_with(body).air_quality(23.0, 72.6, days=1, variables=['pm2_5', 'us_aqi'])
        self.assertEqual(result['source_id'], 'S69')
        self.assertEqual(result['coverage']['current'], {'pm2_5': 10.0, 'us_aqi': 50})
        self.assertEqual({record['unit'] for record in result['records']}, {'μg/m³', 'USAQI'})

    def test_foundation_refuses_an_unknown_variable(self):
        from weathergpt_data.foundation import Foundation
        with self.assertRaises(SourceError):
            Foundation().air_quality(23.0, 72.6, days=1, variables=['pm1'])


class ProductViewTests(unittest.TestCase):
    class Response:
        status = 200
        headers = {'Content-Type': 'application/json'}

        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            return self.body[:size]

    def foundation_with(self, body):
        import json
        import tempfile
        from datetime import datetime as dt
        from weathergpt_data.foundation import Foundation
        from weathergpt_data.transport import Store
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = Store(directory.name, opener=lambda *a, **k: self.Response(json.dumps(body).encode()),
                      clock=lambda: dt(2026, 9, 15, tzinfo=UTC))
        return Foundation(store)

    def test_route_returns_parameters_and_the_current_reading(self):
        from datetime import datetime as dt
        from weathergpt_data import product_api
        times = hours(24, start=dt(2026, 9, 15, tzinfo=UTC))
        body = payload({'pm2_5': [10.0] * 24, 'us_aqi': [50] * 24}, times=times,
                       current={'time': times[0], 'interval': 3600, 'pm2_5': 10.0, 'us_aqi': 50})
        view = product_api.dispatch(self.foundation_with(body), '/api/air-quality',
                                    {'lat': ['23.0'], 'lon': ['72.6'], 'days': ['1'], 'variable': ['pm2_5,us_aqi']})
        self.assertEqual(view['view'], 'air_quality.point')
        self.assertEqual(view['status'], 'ok')
        self.assertEqual(view['data']['current'], {'pm2_5': 10.0, 'us_aqi': 50})
        self.assertIn('pm2_5', view['data']['parameters'])

    def test_route_refuses_an_unknown_variable(self):
        from weathergpt_data import product_api
        body = payload({'pm2_5': [1.0]})
        with self.assertRaises(SourceError):
            product_api.dispatch(self.foundation_with(body), '/api/air-quality',
                                 {'lat': ['23.0'], 'lon': ['72.6'], 'variable': ['pm1']})


if __name__ == '__main__':
    unittest.main()
