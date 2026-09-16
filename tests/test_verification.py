"""Verification-source normalisation: lead-time columns and the ERA5 hourly reference."""
import unittest
from datetime import date, datetime, timezone

from decimal import Decimal

from weathergpt_data.adapters import ERA5_HOURLY, PREVIOUS_RUNS, era5_hourly, previous_runs
from weathergpt_data.transport import SourceError
from weathergpt_data.verification import MIN_SAMPLE_HOURS, error_statistics, summarise

import test_conversation as fixtures

UTC = timezone.utc
META = {'source_id': 'S70', 'sha256': 'e' * 64}
POINT = {'latitude': 23.0, 'longitude': 72.5}


def hours(count, start=datetime(2026, 8, 1, 0, 0, tzinfo=UTC)):
    return [int(start.timestamp()) + 3600 * index for index in range(count)]


def body(values_by_column, times=None, offset=0, units=None):
    times = times if times is not None else hours(1)
    units = units if units is not None else {name: PREVIOUS_RUNS[name.split('_previous_day')[0]][0]
                                             for name in values_by_column}
    return {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': offset,
            'hourly': {'time': times, **values_by_column}, 'hourly_units': units}


def records(result):
    return {(record['parameter']): record for record in result['records']}


class PreviousRunsTests(unittest.TestCase):
    def test_lead_columns_carry_their_lead_time_and_units(self):
        payload = body({'temperature_2m_previous_day1': [29.6], 'temperature_2m_previous_day3': [29.5],
                        'precipitation_previous_day1': [0.4], 'precipitation_previous_day3': [0.1]})
        result = previous_runs(payload, META,
                               {'temperature_2m': PREVIOUS_RUNS['temperature_2m'],
                                'precipitation': PREVIOUS_RUNS['precipitation']},
                               'gfs_seamless', [1, 3], POINT)
        row = records(result)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['source_id'], 'S70')
        self.assertEqual(row['temperature_2m_previous_day1']['lead_days'], 1)
        self.assertEqual(row['temperature_2m_previous_day3']['lead_days'], 3)
        self.assertEqual(row['temperature_2m_previous_day1']['unit'], '°C')
        self.assertEqual(row['precipitation_previous_day1']['interval_start_utc'] is not None, True)
        self.assertIsNone(row['temperature_2m_previous_day1']['interval_start_utc'])

    def test_an_all_null_lead_is_missing_not_zero(self):
        payload = body({'temperature_2m_previous_day7': [None, None, None]}, times=hours(3))
        result = previous_runs(payload, META, {'temperature_2m': PREVIOUS_RUNS['temperature_2m']},
                               'gfs_seamless', [7], POINT)
        self.assertEqual([record['value'] for record in result['records']], [None, None, None])
        self.assertTrue(all('source_value_missing' in record['quality_flags'] for record in result['records']))
        self.assertEqual(result['status'], 'no_data')

    def test_a_missing_lead_column_is_refused(self):
        payload = body({'temperature_2m_previous_day1': [29.6]})
        with self.assertRaises(SourceError):
            previous_runs(payload, META, {'temperature_2m': PREVIOUS_RUNS['temperature_2m']},
                          'gfs_seamless', [3], POINT)

    def test_a_lead_beyond_seven_is_refused_by_the_adapter(self):
        payload = body({'temperature_2m_previous_day1': [29.6]})
        with self.assertRaises(SourceError):
            previous_runs(payload, META, {'temperature_2m': PREVIOUS_RUNS['temperature_2m']},
                          'gfs_seamless', [8], POINT)

    def test_wrong_unit_and_unknown_model_are_refused(self):
        payload = body({'temperature_2m_previous_day1': [29.6]}, units={'temperature_2m_previous_day1': 'K'})
        with self.assertRaises(SourceError):
            previous_runs(payload, META, {'temperature_2m': PREVIOUS_RUNS['temperature_2m']}, 'gfs_seamless', [1], POINT)
        with self.assertRaises(SourceError):
            previous_runs(body({'temperature_2m_previous_day1': [29.6]}), META,
                          {'temperature_2m': PREVIOUS_RUNS['temperature_2m']}, 'not_a_model', [1], POINT)

    def test_non_hourly_or_non_utc_is_refused(self):
        with self.assertRaises(SourceError):
            previous_runs(body({'temperature_2m_previous_day1': [1.0, 2.0]},
                               times=[hours(1)[0], hours(1)[0] + 1800]), META,
                          {'temperature_2m': PREVIOUS_RUNS['temperature_2m']}, 'gfs_seamless', [1], POINT)
        with self.assertRaises(SourceError):
            previous_runs(body({'temperature_2m_previous_day1': [1.0]}, offset=19800), META,
                          {'temperature_2m': PREVIOUS_RUNS['temperature_2m']}, 'gfs_seamless', [1], POINT)


class Era5HourlyTests(unittest.TestCase):
    def test_reference_series_parse_with_units(self):
        payload = {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': 0,
                   'hourly': {'time': hours(2), 'temperature_2m': [28.0, 29.0], 'precipitation': [0.0, 1.0]},
                   'hourly_units': {'temperature_2m': '°C', 'precipitation': 'mm'}}
        result = era5_hourly(payload, META, {'temperature_2m': ERA5_HOURLY['temperature_2m'],
                                             'precipitation': ERA5_HOURLY['precipitation']}, POINT)
        self.assertEqual(result['family'], 'reanalysis_hourly')
        self.assertEqual(len(result['records']), 4)
        self.assertEqual({record['unit'] for record in result['records']}, {'°C', 'mm'})

    def test_wrong_unit_is_refused(self):
        payload = {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': 0,
                   'hourly': {'time': hours(1), 'temperature_2m': [28.0]},
                   'hourly_units': {'temperature_2m': 'K'}}
        with self.assertRaises(SourceError):
            era5_hourly(payload, META, {'temperature_2m': ERA5_HOURLY['temperature_2m']}, POINT)


class MetricTests(unittest.TestCase):
    def test_closed_form_statistics(self):
        # forecast = reference + 1 for 24 hours: every error is exactly 1 and the series rise together.
        pairs = [(Decimal(index + 1), Decimal(index)) for index in range(MIN_SAMPLE_HOURS)]
        stats = error_statistics(pairs)
        self.assertEqual(stats['status'], 'measured')
        self.assertEqual(stats['n'], MIN_SAMPLE_HOURS)
        self.assertEqual(str(stats['bias']), '1.000')
        self.assertEqual(str(stats['mae']), '1.000')
        self.assertEqual(str(stats['rmse']), '1.000')
        self.assertEqual(str(stats['correlation']), '1.000')

    def test_too_few_hours_is_unmeasured(self):
        stats = error_statistics([(Decimal(1), Decimal(0))] * 4)
        self.assertEqual(stats['status'], 'unmeasured')
        self.assertNotIn('bias', stats)

    def test_correlation_is_undefined_without_variation(self):
        pairs = [(Decimal(index), Decimal(5)) for index in range(MIN_SAMPLE_HOURS)]
        stats = error_statistics(pairs)
        self.assertEqual(stats['status'], 'measured')
        self.assertIsNone(stats['correlation'])
        self.assertIn('no variation', stats['correlation_note'])

    def test_summarise_matches_leads_and_counts_unmatched_hours(self):
        length = MIN_SAMPLE_HOURS + 1
        times = hours(length)
        forecast_values = [float(index + 1) for index in range(length)]
        forecast_values[0] = None
        forecast = previous_runs(
            body({'temperature_2m_previous_day1': forecast_values}, times=times), META,
            {'temperature_2m': PREVIOUS_RUNS['temperature_2m']}, 'gfs_seamless', [1], POINT)
        reference = era5_hourly(
            {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': 0,
             'hourly': {'time': times, 'temperature_2m': [float(index) for index in range(length)]},
             'hourly_units': {'temperature_2m': '°C'}},
            {'source_id': 'S22', 'sha256': 'r' * 64}, {'temperature_2m': ERA5_HOURLY['temperature_2m']}, POINT)
        result = summarise(forecast, reference)
        lead = result['variables']['temperature_2m'][0]
        self.assertEqual(lead['lead_days'], 1)
        self.assertEqual(lead['n'], MIN_SAMPLE_HOURS)
        self.assertEqual(lead['unmatched_hours'], 1)
        self.assertEqual(str(lead['bias']), '1.000')
        self.assertEqual(str(lead['mae']), '1.000')
        self.assertEqual(result['forecast']['model'], 'gfs_seamless')
        self.assertEqual(result['reference']['source_id'], 'S22')


class FoundationVerificationTests(unittest.TestCase):
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

    def foundation(self, forecast_body, reference_body):
        import json
        import tempfile
        from datetime import datetime as dt
        from weathergpt_data.foundation import Foundation
        from weathergpt_data.transport import Store

        def opener(request, *args, **kwargs):
            url = request.full_url if hasattr(request, 'full_url') else str(request)
            body = reference_body if 'archive-api' in url else forecast_body
            return self.Response(json.dumps(body).encode())
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = Store(directory.name, opener=opener, clock=lambda: dt(2026, 9, 15, tzinfo=UTC))
        return Foundation(store)

    def test_verification_matches_a_lead_to_the_reference(self):
        length = 48
        times = hours(length, start=datetime(2026, 8, 1, tzinfo=UTC))
        forecast_body = body({'temperature_2m_previous_day1': [float(index + 1) for index in range(length)]}, times=times)
        reference_body = {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': 0,
                          'hourly': {'time': times, 'temperature_2m': [float(index) for index in range(length)]},
                          'hourly_units': {'temperature_2m': '°C'}}
        result = self.foundation(forecast_body, reference_body).verification(
            23.0, 72.5, '2026-08-01', '2026-08-02', model='gfs_seamless', variables=['temperature_2m'], leads=[1])
        lead = result['variables']['temperature_2m'][0]
        self.assertEqual(result['forecast']['source_id'], 'S70')
        self.assertEqual(result['reference']['source_id'], 'S22')
        self.assertEqual(lead['n'], length)
        self.assertEqual(str(lead['bias']), '1.000')
        self.assertEqual(result['method'], {'bias': 'mean of (forecast minus reference) over matched hours',
                                            'mae': 'mean of the absolute error over matched hours',
                                            'rmse': 'square root of the mean squared error over matched hours',
                                            'correlation': 'Pearson product-moment correlation over matched hours'})

    def test_a_window_inside_the_reanalysis_delay_is_refused(self):
        times = hours(24, start=datetime(2026, 9, 12, tzinfo=UTC))
        forecast_body = body({'temperature_2m_previous_day1': [float(index) for index in range(24)]}, times=times)
        reference_body = {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': 0,
                          'hourly': {'time': times, 'temperature_2m': [float(index) for index in range(24)]},
                          'hourly_units': {'temperature_2m': '°C'}}
        with self.assertRaises(SourceError):
            self.foundation(forecast_body, reference_body).verification(
                23.0, 72.5, '2026-09-12', '2026-09-12', variables=['temperature_2m'], leads=[1])


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

    def foundation_with(self, forecast_body, reference_body):
        import json
        import tempfile
        from datetime import datetime as dt
        from weathergpt_data.foundation import Foundation
        from weathergpt_data.transport import Store

        def opener(request, *args, **kwargs):
            url = request.full_url if hasattr(request, 'full_url') else str(request)
            body = reference_body if 'archive-api' in url else forecast_body
            return self.Response(json.dumps(body).encode())
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = Store(directory.name, opener=opener, clock=lambda: dt(2026, 9, 15, tzinfo=UTC))
        return Foundation(store)

    def bodies(self):
        length = 48
        times = hours(length, start=datetime(2026, 8, 1, tzinfo=UTC))
        forecast = body({'temperature_2m_previous_day1': [float(index) for index in range(length)]}, times=times)
        reference = {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': 0,
                     'hourly': {'time': times, 'temperature_2m': [float(index) for index in range(length)]},
                     'hourly_units': {'temperature_2m': '°C'}}
        return forecast, reference

    def test_route_returns_the_metric_series(self):
        from weathergpt_data import product_api
        forecast, reference = self.bodies()
        view = product_api.dispatch(self.foundation_with(forecast, reference), '/api/verification',
                                    {'lat': ['23.0'], 'lon': ['72.5'], 'start': ['2026-08-01'],
                                     'end': ['2026-08-02'], 'model': ['gfs_seamless'],
                                     'variable': ['temperature_2m'], 'leads': ['1']})
        self.assertEqual(view['view'], 'verification.skill')
        self.assertEqual(view['status'], 'ok')
        self.assertIn('temperature_2m', view['data']['variables'])
        self.assertEqual({source['source_id'] for source in view['sources']}, {'S70', 'S22'})
        import json
        self.assertTrue(json.dumps(view))  # the packet must serialise exactly as the server serves it

    def test_route_requires_a_window(self):
        from weathergpt_data import product_api
        with self.assertRaises(SourceError):
            product_api.dispatch(self.foundation_with({}, {}), '/api/verification', {'lat': ['23'], 'lon': ['72']})


def verification_packet():
    from datetime import timedelta
    base = datetime(2026, 8, 28, tzinfo=UTC)
    forecast_records, reference_records = [], []
    for lead in (1, 2, 3, 5, 7):
        for index in range(48):
            moment = (base + timedelta(hours=index)).isoformat()
            reference_records.append({'variable': 'temperature_2m', 'valid_time_utc': moment,
                                      'value': 30.0 + index * 0.1})
            forecast_records.append({'variable': 'temperature_2m', 'valid_time_utc': moment,
                                     'value': 30.0 + index * 0.1 + 0.2 * lead, 'lead_days': lead,
                                     'unit': '°C',
                                     'source_locator': '$.hourly.temperature_2m_previous_day%d[%d]' % (lead, index)})
    forecast = {'source_id': 'S70', 'records': forecast_records,
                'coverage': {'model': 'gfs_seamless', 'returned_grid': {'latitude': 23.02, 'longitude': 72.54}}}
    reference = {'source_id': 'S22', 'records': reference_records,
                 'coverage': {'returned_grid': {'latitude': 23.02, 'longitude': 72.54}}}
    result = summarise(forecast, reference)
    result['forecast'].update({'retrieved_at_utc': '2026-09-16T00:00:00+00:00',
                               'url': 'https://previous-runs-api.open-meteo.com/v1/forecast', 'sha256': 'e' * 64})
    result['reference'].update({'retrieved_at_utc': '2026-09-16T00:00:00+00:00',
                                'url': 'https://archive-api.open-meteo.com/v1/archive', 'sha256': 'f' * 64})
    result['window'] = {'start': '2026-08-28', 'end': '2026-09-10'}
    return result


class VerificationPlannerTests(unittest.TestCase):
    NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)

    def request(self, question):
        from zoneinfo import ZoneInfo
        from weathergpt_data.rule_planner import rule_request
        return rule_request(question, self.NOW.astimezone(ZoneInfo('Asia/Kolkata')))

    def test_a_verification_question_is_a_verification_task(self):
        request = self.request('How accurate was the temperature forecast for Ahmedabad over the last two weeks?')
        self.assertIsNotNone(request)
        self.assertEqual([(task['kind'], task['operation']) for task in request['tasks']],
                         [('verification', 'lookup')])
        self.assertEqual(request['tasks'][0]['parameters'], ['temperature_2m'])

    def test_naming_precipitation_narrows_the_verification_variable(self):
        request = self.request('Verify the precipitation forecast for Surat.')
        self.assertEqual(request['tasks'][0]['parameters'], ['precipitation'])

    def test_an_ordinary_forecast_stays_a_forecast(self):
        request = self.request('Will it rain in Ahmedabad tomorrow?')
        self.assertEqual(request['tasks'][0]['kind'], 'forecast')


class VerificationChatTests(unittest.TestCase):
    setUp = fixtures.ConversationTests.setUp
    publish = fixtures.ConversationTests.publish
    add_place = fixtures.ConversationTests.add_place
    ask = fixtures.ConversationTests.ask
    chat = fixtures.ConversationTests.chat

    def test_a_verification_question_answers_with_computed_statistics(self):
        from unittest.mock import patch
        from test_product_stage_one import task
        question = 'How accurate was the temperature forecast for Ahmedabad over the last two weeks?'
        self.model.value['tasks'] = [task(kind='verification', operation='lookup', parameters=['temperature_2m'],
                                          years=[], start_local='', end_local='', request_quote=question)]
        with patch('weathergpt_data.foundation.Foundation.verification', return_value=verification_packet()):
            result = self.chat(question=question)
        self.assertEqual(result['status'], 'answered', result['answer'])
        parameters = {fact['parameter'] for fact in result['facts']}
        self.assertIn('temperature_2m_mae', parameters)
        self.assertIn('temperature_2m_bias', parameters)
        self.assertIn('temperature_2m_correlation', parameters)
        self.assertTrue(all('matched hours' in fact['method'] for fact in result['facts']))
        self.assertTrue(all(fact['evidence_kind'] == 'verification_statistic' for fact in result['facts']))
        self.assertTrue(any('reanalysis' in note for note in result['notes']))
        self.assertTrue(any('most recent completed fourteen-day window' in note for note in result['notes']))
        self.assertIn('mean absolute error by lead time', result['answer'])
        self.assertFalse(result['operational_eligible'])
        self.assertTrue(result['citations'])
        self.assertEqual(result['charts'], [])

    def test_a_window_inside_the_reanalysis_delay_is_not_verified(self):
        from test_product_stage_one import task
        question = 'How accurate was the temperature forecast for Ahmedabad yesterday?'
        self.model.value['tasks'] = [task(kind='verification', operation='lookup', parameters=['temperature_2m'],
                                          years=[], start_local='2026-09-10T00:30:00+05:30',
                                          end_local='2026-09-11T00:30:00+05:30', request_quote=question)]
        result = self.chat(question=question)
        self.assertEqual(result['status'], 'unavailable', result['answer'])
        self.assertIn('five-day delay', result['answer'])
        self.assertFalse(result['facts'])


if __name__ == '__main__':
    unittest.main()
