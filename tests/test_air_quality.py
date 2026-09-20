"""Air-quality normalisation: pollutants and indices stay apart, and nothing is scored."""
import unittest
from datetime import datetime, timezone

import test_conversation as fixtures
from test_task_coverage_battery import assert_coverage_consistent
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


class AirQualityChatTests(unittest.TestCase):
    setUp = fixtures.ConversationTests.setUp
    publish = fixtures.ConversationTests.publish
    add_place = fixtures.ConversationTests.add_place
    ask = fixtures.ConversationTests.ask
    chat = fixtures.ConversationTests.chat

    def packet(self):
        from datetime import date, datetime as dt
        meta = {'source_id': 'S69', 'sha256': 'd' * 64,
                'url': 'https://air-quality-api.open-meteo.com/v1/air-quality?hourly=pm2_5',
                'retrieved_at_utc': '2026-09-15T00:00:00+00:00', 'delivery': 'network'}
        times = hours(24, start=dt(2026, 9, 15, tzinfo=UTC))
        body = payload({'pm2_5': [10.0 + (index % 5) for index in range(24)],
                        'us_aqi': [50 + index for index in range(24)]}, times=times,
                       current={'time': times[0], 'interval': 3600, 'pm2_5': 12.0, 'us_aqi': 55})
        return air_quality(body, meta, {'pm2_5': AIR_QUALITY['pm2_5'], 'us_aqi': AIR_QUALITY['us_aqi']},
                           POINT, expected_dates=(date(2026, 9, 15), date(2026, 9, 15)))

    def test_an_air_quality_question_answers_without_health_advice(self):
        from unittest.mock import patch
        from test_product_stage_one import task
        question = 'What is the air quality in Ahmedabad tomorrow?'
        self.model.value['tasks'] = [task(kind='air_quality', operation='lookup', parameters=['pm2_5', 'us_aqi'],
                                          years=[], start_local='2026-09-15T00:00:00+05:30',
                                          end_local='2026-09-16T00:00:00+05:30', request_quote=question)]
        with patch('weathergpt_data.foundation.Foundation.air_quality', return_value=self.packet()):
            r = self.chat(question=question)
        self.assertEqual(r['status'], 'answered', r['answer'])
        assert_coverage_consistent(self, r)
        parameters = {fact['parameter'] for fact in r['facts']}
        self.assertIn('pm2_5', parameters)
        self.assertIn('us_aqi_current', parameters)
        self.assertTrue(any('source\'s own index' in note for note in r['notes']))
        self.assertFalse(r['operational_eligible'])
        self.assertEqual(len(r['charts']), 2)
        plotted = {p['evidence_id'] for c in r['charts'] for p in c['points']}
        hourly = {f['id'] for f in r['facts'] if not f['parameter'].endswith('_current')}
        self.assertEqual(plotted, hourly)
        self.assertTrue(all('provider current hour' in f['label'] for f in r['facts'] if f['parameter'].endswith('_current')))

    def test_current_reading_does_not_complete_an_absent_forecast_window(self):
        from unittest.mock import patch
        from test_product_stage_one import task
        question = 'What is the air quality in Ahmedabad tomorrow?'
        self.model.value['tasks'] = [task(kind='air_quality', operation='lookup', parameters=['pm2_5'],
                                          years=[], start_local='2026-09-15T00:00:00+05:30',
                                          end_local='2026-09-16T00:00:00+05:30', request_quote=question)]
        data = self.packet()
        data['records'] = [r for r in data['records'] if r['aggregation'] == 'current_instant']
        with patch('weathergpt_data.foundation.Foundation.air_quality', return_value=data):
            answer = self.chat(question=question)
        self.assertEqual(answer['status'], 'partial')
        self.assertTrue(any('no hourly sample' in note for note in answer['notes']))
        self.assertFalse(answer['charts'])

    def test_an_air_quality_fetch_failure_is_recorded_not_invented(self):
        from unittest.mock import patch
        from test_product_stage_one import task
        question = 'What is the air quality in Ahmedabad tomorrow?'
        self.model.value['tasks'] = [task(kind='air_quality', operation='lookup', parameters=['pm2_5'],
                                          years=[], start_local='2026-09-15T00:00:00+05:30',
                                          end_local='2026-09-16T00:00:00+05:30', request_quote=question)]
        with patch('weathergpt_data.foundation.Foundation.air_quality', side_effect=SourceError('offline')):
            r = self.chat(question=question)
        self.assertEqual(r['status'], 'unavailable')
        self.assertFalse(r['facts'])


if __name__ == '__main__':
    unittest.main()
