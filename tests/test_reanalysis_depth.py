"""Reanalysis model selection and capability refusal for daily history.

The archive API answers a variable a model does not carry with null rather than an
error, so the workspace has to know which variables a model supports before it asks.
These checks pin that the model named in a question becomes part of the collection
identity, that a variable a model does not carry is refused instead of being shown as
an empty series, and that the catalogue stays consistent with the recorded probe.
"""
import json
import unittest

import test_conversation as fixtures
from test_ingestion import Response
from test_point_tasks import daily
from test_product_stage_one import task
from weathergpt_data.adapters import (REANALYSIS_DAILY, reanalysis_label, reanalysis_model_for,
                                      reanalysis_supported)
from weathergpt_data.foundation import Foundation
from weathergpt_data.transport import SourceError


class ReanalysisModelJourneys(unittest.TestCase):
    setUp = fixtures.ConversationTests.setUp
    publish = fixtures.ConversationTests.publish
    add_place = fixtures.ConversationTests.add_place
    ask = fixtures.ConversationTests.ask
    chat = fixtures.ConversationTests.chat

    def setup_history(self, parameters, quote):
        self.calls = 0
        self.response = daily()

        def open_(*args, **kw):
            self.calls += 1
            return Response(json.dumps(self.response).encode())
        self.app.opener = open_
        t = task(kind='history', operation='daily', parameters=parameters, years=[],
                 start_local='2025-07-01T00:00:00+05:30', end_local='2025-07-04T00:00:00+05:30',
                 request_quote=quote)
        self.model.value['tasks'] = [t]
        return t

    def stored_spec(self):
        row = self.db.db.execute("SELECT spec FROM jobs WHERE spec LIKE '%history_local%' "
                                 "ORDER BY rowid DESC LIMIT 1").fetchone()
        return json.loads(row[0])

    def test_named_model_reaches_the_collection_identity(self):
        self.setup_history(['temperature_2m_mean'],
                           'ERA5-Land daily mean temperature in Ahmedabad from 1 through 3 July 2025.')
        r = self.chat()
        self.assertEqual(r['status'], 'answered', r['answer'])
        self.assertEqual(self.stored_spec()['models'], 'era5_land')
        self.assertTrue(all(f['source_id'] == 'S22' and f['evidence_kind'] == 'reanalysis' for f in r['facts']))
        self.assertIn('ERA5-Land', r['citations'][0]['product'])

    def test_era5_land_refuses_a_variable_it_does_not_carry(self):
        self.setup_history(['rainfall'],
                           'ERA5-Land daily rainfall in Ahmedabad from 1 through 3 July 2025.')
        r = self.chat()
        self.assertEqual(r['status'], 'unavailable')
        self.assertIn('does not carry', r['answer'])
        self.assertIn('era5_seamless', r['answer'])
        self.assertEqual(self.calls, 0)

    def test_default_model_is_era5_and_is_recorded(self):
        self.setup_history(['rainfall', 'temperature'],
                           'Daily rainfall and mean temperature in Ahmedabad from 1 through 3 July 2025.')
        r = self.chat()
        self.assertEqual(r['status'], 'answered', r['answer'])
        self.assertEqual(self.stored_spec()['models'], 'era5')

    def test_all_null_supported_variable_is_not_published(self):
        self.setup_history(['relative_humidity_2m_mean'],
                           'Daily mean relative humidity in Ahmedabad from 1 through 3 July 2025.')
        self.response['daily']['relative_humidity_2m_mean'] = [None, None, None]
        r = self.chat()
        self.assertEqual(r['status'], 'unavailable')
        self.assertFalse(r['facts'])

    def test_model_word_is_read_deterministically(self):
        self.assertEqual(reanalysis_model_for('ERA5-Seamless for 1960'), 'era5_seamless')
        self.assertEqual(reanalysis_model_for('era5 land high resolution'), 'era5_land')
        self.assertEqual(reanalysis_model_for('a plain rainfall question'), 'era5')


class CatalogueContract(unittest.TestCase):
    def test_every_entry_carries_a_complete_contract(self):
        for name, spec in REANALYSIS_DAILY.items():
            self.assertTrue(spec['models'], name)
            self.assertIsInstance(spec['unit'], str, name)
            self.assertTrue(set(spec['models']) <= {'era5', 'era5_land', 'era5_seamless'}, name)

    def test_era5_land_does_not_claim_precipitation_or_wind(self):
        supported = reanalysis_supported('era5_land')
        for name in ('precipitation_sum', 'rain_sum', 'wind_speed_10m_max', 'wind_gusts_10m_max'):
            self.assertNotIn(name, supported)
        self.assertIn('soil_moisture_0_to_7cm_mean', supported)

    def test_unknown_model_is_refused(self):
        self.assertRaises(SourceError, reanalysis_supported, 'era5_unknown')
        self.assertRaises(SourceError, reanalysis_label, 'era5_unknown')

    def test_daily_validator_applies_the_upper_bound(self):
        body = {'latitude': 23.0, 'longitude': 72.5, 'utc_offset_seconds': 19800, 'timezone': 'Asia/Kolkata',
                'daily_units': {'relative_humidity_2m_mean': '%'},
                'daily': {'time': ['2025-07-01'], 'relative_humidity_2m_mean': [140]}}
        meta = {'source_id': 'S22', 'sha256': 'x', 'url': 'https://example.invalid', 'delivery': 'network'}
        with self.assertRaises(SourceError):
            Foundation.daily(body, meta, {'latitude': 23.0, 'longitude': 72.5},
                             {'relative_humidity_2m_mean': ('%', 0, 100)}, 'reanalysis',
                             'ERA5 via Open-Meteo', timezone_name='Asia/Kolkata')


if __name__ == '__main__':
    unittest.main()
