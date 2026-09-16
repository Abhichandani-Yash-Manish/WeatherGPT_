"""Verification-source normalisation: lead-time columns and the ERA5 hourly reference."""
import unittest
from datetime import date, datetime, timezone

from decimal import Decimal

from weathergpt_data.adapters import ERA5_HOURLY, PREVIOUS_RUNS, era5_hourly, previous_runs
from weathergpt_data.transport import SourceError
from weathergpt_data.verification import MIN_SAMPLE_HOURS, error_statistics, summarise

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


if __name__ == '__main__':
    unittest.main()
