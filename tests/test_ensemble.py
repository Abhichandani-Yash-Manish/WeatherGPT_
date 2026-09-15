"""Ensemble normalisation and member statistics, with independent fixed oracles."""
import unittest
from datetime import datetime, timezone
from decimal import Decimal

import test_conversation as fixtures

from weathergpt_data.adapters import (ENSEMBLE, ENSEMBLE_MODELS, ensemble, ensemble_model_for,
                                      ensemble_statistics, nearest_rank)
from weathergpt_data.transport import SourceError

UTC = timezone.utc
META = {'source_id': 'S68', 'sha256': 'a' * 64}


def hours(count, start=datetime(2026, 9, 15, 0, 0, tzinfo=UTC)):
    return [int(start.timestamp()) + 3600 * index for index in range(count)]


def payload(member_values, variable='temperature_2m', unit=ENSEMBLE['temperature_2m'][0],
            control=None, offset=0, times=None):
    times = times if times is not None else hours(1)
    hourly = {'time': times}
    if control is not None:
        hourly[variable] = control
    units = {variable: unit}
    for index in range(1, len(member_values) + 1):
        name = variable + '_member%02d' % index
        hourly[name] = member_values[index - 1]
        units[name] = unit
    return {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': offset,
            'hourly': hourly, 'hourly_units': units}


def records(result):
    return {record['parameter']: record for record in result['records']}


class StatisticsTests(unittest.TestCase):
    def test_mean_spread_range_and_nearest_rank_percentiles(self):
        # Ten members with values 1..10 have known closed-form statistics.
        stats = ensemble_statistics([Decimal(value) for value in range(1, 11)])
        self.assertEqual(stats['member_count'], 10)
        self.assertEqual(str(stats['mean']), '5.500')
        self.assertEqual(str(stats['spread']), '2.872')          # sqrt(8.25), population sd
        self.assertEqual(str(stats['min']), '1')
        self.assertEqual(str(stats['max']), '10')
        self.assertEqual(str(stats['p10']), '1')
        self.assertEqual(str(stats['p50']), '5')
        self.assertEqual(str(stats['p90']), '9')

    def test_nearest_rank_never_interpolates(self):
        ordered = [Decimal(value) for value in (1, 2, 3, 4)]
        self.assertEqual(nearest_rank(ordered, 10), Decimal(1))
        self.assertEqual(nearest_rank(ordered, 50), Decimal(2))
        self.assertEqual(nearest_rank(ordered, 90), Decimal(4))

    def test_the_model_word_is_read_deterministically(self):
        self.assertEqual(ensemble_model_for('ECMWF ensemble spread'), 'ecmwf_ifs025')
        self.assertEqual(ensemble_model_for('the ICON ensemble members'), 'icon_seamless')
        self.assertEqual(ensemble_model_for('ensemble spread for Ahmedabad'), 'gfs025')

    def test_fewer_than_two_members_has_no_spread(self):
        stats = ensemble_statistics([Decimal(7)])
        self.assertEqual(stats['member_count'], 1)
        self.assertEqual(str(stats['mean']), '7.000')
        self.assertIsNone(stats['spread'])
        self.assertIsNone(stats['p50'])


class EnsembleAdapterTests(unittest.TestCase):
    def test_member_statistics_and_control_are_normalised(self):
        body = payload([[value] for value in range(1, 11)], control=[100])
        result = ensemble(body, META, {'temperature_2m': ENSEMBLE['temperature_2m']}, 'gfs025',
                          {'latitude': 23.0, 'longitude': 72.5})
        row = records(result)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['source_id'], 'S68')
        self.assertEqual(result['coverage']['member_total'], {'temperature_2m': 10})
        self.assertEqual(row['temperature_2m_mean']['value'], '5.500')
        self.assertEqual(row['temperature_2m_spread']['value'], '2.872')
        self.assertEqual(row['temperature_2m_control']['value'], '100')

    def test_precipitation_exceedance_is_a_member_frequency(self):
        body = payload([[value] for value in range(1, 11)], variable='precipitation',
                       unit=ENSEMBLE['precipitation'][0])
        result = ensemble(body, META, {'precipitation': ENSEMBLE['precipitation']}, 'gfs025',
                          {'latitude': 23.0, 'longitude': 72.5}, threshold=6)
        record = records(result)['precipitation_exceedance']
        self.assertEqual(record['value'], '0.500')
        self.assertEqual(record['exceedance_count'], 5)
        self.assertEqual(record['threshold'], '6')
        self.assertEqual(record['interval_start_utc'] is not None, True)

    def test_a_negative_or_non_numeric_threshold_is_refused(self):
        body = payload([[1], [2]], variable='precipitation', unit=ENSEMBLE['precipitation'][0])
        for threshold in (-1, 'wet'):
            with self.subTest(threshold=threshold):
                with self.assertRaises(SourceError):
                    ensemble(body, META, {'precipitation': ENSEMBLE['precipitation']}, 'gfs025',
                             {'latitude': 23.0, 'longitude': 72.5}, threshold=threshold)

    def test_null_member_makes_the_hour_partial_not_zero(self):
        body = payload([[1], [None]])
        result = ensemble(body, META, {'temperature_2m': ENSEMBLE['temperature_2m']}, 'gfs025',
                          {'latitude': 23.0, 'longitude': 72.5})
        row = records(result)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(row['temperature_2m_mean']['value'], '1.000')
        self.assertIsNone(row['temperature_2m_spread']['value'])
        self.assertEqual(row['temperature_2m_mean']['member_count'], 1)

    def test_wrong_unit_is_refused(self):
        body = payload([[1], [2]], unit='K')
        with self.assertRaises(SourceError):
            ensemble(body, META, {'temperature_2m': ENSEMBLE['temperature_2m']}, 'gfs025',
                     {'latitude': 23.0, 'longitude': 72.5})

    def test_missing_members_are_refused(self):
        body = {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': 0,
                'hourly': {'time': hours(1), 'temperature_2m': [1.0]},
                'hourly_units': {'temperature_2m': '°C'}}
        with self.assertRaises(SourceError):
            ensemble(body, META, {'temperature_2m': ENSEMBLE['temperature_2m']}, 'gfs025',
                     {'latitude': 23.0, 'longitude': 72.5})

    def test_non_utc_or_unknown_model_is_refused(self):
        body = payload([[1], [2]])
        with self.assertRaises(SourceError):
            ensemble(body, META, {'temperature_2m': ENSEMBLE['temperature_2m']}, 'not_a_model',
                     {'latitude': 23.0, 'longitude': 72.5})
        self.assertNotIn('not_a_model', ENSEMBLE_MODELS)

    def test_incomplete_requested_interval_is_refused(self):
        body = payload([[1], [2]], times=hours(1))
        with self.assertRaises(SourceError):
            ensemble(body, META, {'temperature_2m': ENSEMBLE['temperature_2m']}, 'gfs025',
                     {'latitude': 23.0, 'longitude': 72.5},
                     expected_dates=(datetime(2026, 9, 15, tzinfo=UTC).date(),
                                     datetime(2026, 9, 16, tzinfo=UTC).date()))


class FoundationEnsembleTests(unittest.TestCase):
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

    def test_foundation_fetches_normalises_and_caches_the_ensemble(self):
        import json
        import tempfile
        from datetime import datetime as dt
        from weathergpt_data.foundation import Foundation
        from weathergpt_data.transport import Store
        clock = lambda: dt(2026, 9, 15, tzinfo=UTC)
        times = hours(24, start=dt(2026, 9, 15, tzinfo=UTC))
        body = payload([[value] * 24 for value in range(1, 11)], control=[7] * 24, times=times)
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory, opener=lambda *a, **k: self.Response(json.dumps(body).encode()), clock=clock)
            result = Foundation(store).ensemble(23.0, 72.5, days=1, model='gfs025', variables=['temperature_2m'])
        self.assertEqual(result['source_id'], 'S68')
        self.assertEqual(result['coverage']['member_total'], {'temperature_2m': 10})
        row = records(result)
        self.assertEqual(row['temperature_2m_mean']['value'], '5.500')
        self.assertEqual(row['temperature_2m_spread']['value'], '2.872')


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

    def test_route_returns_the_member_statistics(self):
        from datetime import datetime as dt
        from weathergpt_data import product_api
        times = hours(24, start=dt(2026, 9, 15, tzinfo=UTC))
        body = payload([[value] * 24 for value in range(1, 11)], control=[7] * 24, times=times)
        view = product_api.dispatch(self.foundation_with(body), '/api/ensemble',
                                    {'lat': ['23.0'], 'lon': ['72.5'], 'days': ['1'], 'model': ['gfs025'],
                                     'variable': ['temperature_2m']})
        self.assertEqual(view['view'], 'ensemble.spread')
        self.assertEqual(view['status'], 'ok')
        self.assertIn('temperature_2m_mean', view['data']['parameters'])
        self.assertEqual(view['data']['member_total'], {'temperature_2m': 10})

    def test_route_refuses_an_unknown_model(self):
        from weathergpt_data import product_api
        body = payload([[1], [2]])
        with self.assertRaises(SourceError):
            product_api.dispatch(self.foundation_with(body), '/api/ensemble',
                                 {'lat': ['23.0'], 'lon': ['72.5'], 'model': ['not_a_model']})


class EnsembleChatTests(unittest.TestCase):
    setUp = fixtures.ConversationTests.setUp
    publish = fixtures.ConversationTests.publish
    add_place = fixtures.ConversationTests.add_place
    ask = fixtures.ConversationTests.ask
    chat = fixtures.ConversationTests.chat

    def packet(self):
        from datetime import date, datetime as dt
        meta = {'source_id': 'S68', 'sha256': 'b' * 64,
                'url': 'https://ensemble-api.open-meteo.com/v1/ensemble?models=gfs025',
                'retrieved_at_utc': '2026-09-15T00:00:00+00:00', 'delivery': 'network'}
        times = hours(24, start=dt(2026, 9, 15, tzinfo=UTC))
        body = payload([[value] * 24 for value in range(1, 11)], control=[7] * 24, times=times)
        return ensemble(body, meta, {'temperature_2m': ENSEMBLE['temperature_2m']}, 'gfs025',
                        {'latitude': 23.0, 'longitude': 72.5},
                        expected_dates=(date(2026, 9, 15), date(2026, 9, 15)))

    def test_an_ensemble_question_answers_with_member_spread(self):
        from unittest.mock import patch
        from test_product_stage_one import task
        question = 'What is the ensemble spread for Ahmedabad tomorrow morning?'
        self.model.value['tasks'] = [task(kind='ensemble', operation='lookup', parameters=['temperature_2m'],
                                          years=[], start_local='2026-09-15T06:30:00+05:30',
                                          end_local='2026-09-15T09:30:00+05:30', request_quote=question)]
        with patch('weathergpt_data.foundation.Foundation.ensemble', return_value=self.packet()):
            r = self.chat(question=question)
        self.assertEqual(r['status'], 'answered', r['answer'])
        parameters = {fact['parameter'] for fact in r['facts']}
        self.assertIn('temperature_2m_mean', parameters)
        self.assertIn('temperature_2m_spread', parameters)
        self.assertTrue(any('not a probability' in note for note in r['notes']))
        self.assertFalse(r['operational_eligible'])

    def test_an_ensemble_fetch_failure_is_recorded_not_invented(self):
        from unittest.mock import patch
        from test_product_stage_one import task
        question = 'What is the ensemble spread for Ahmedabad tomorrow morning?'
        self.model.value['tasks'] = [task(kind='ensemble', operation='lookup', parameters=['temperature_2m'],
                                          years=[], start_local='2026-09-15T06:30:00+05:30',
                                          end_local='2026-09-15T09:30:00+05:30', request_quote=question)]
        with patch('weathergpt_data.foundation.Foundation.ensemble', side_effect=SourceError('offline')):
            r = self.chat(question=question)
        self.assertEqual(r['status'], 'unavailable')
        self.assertFalse(r['facts'])


if __name__ == '__main__':
    unittest.main()
