"""A briefing over named places: the products as read, and the change since the last run.

These are offline checks with synthetic product views. They pin the discipline: a quiet district-day
is written as a quiet day in one product and never as an all-clear; the CAP relay stays a separate
product; a forecast is quoted as the first and last value of the retrieved series with its sample
count and never summarised into an index; a part that could not be read is recorded as unavailable
rather than filled; and the change since the previous run is measured against that run's record,
with an honest not_comparable reading when the two runs do not hold the same thing.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from weathergpt_data.briefing_run import (NOT_ESTABLISHED, compose, diff, latest, load_previous, markdown,
                                           place_brief, summary_line)

NOW = datetime(2026, 9, 15, 6, 30, tzinfo=timezone.utc)
PLACE = {'label': 'Ahmedabad, Gujarat', 'district': 'Ahmedabad', 'state': 'Gujarat', 'latitude': 23.02579, 'longitude': 72.58727}


def day_row(number, colour='yellow', hazards=('Thunderstorm/lightning/squall',), quiet=False):
    return {'day': number, 'label': '1%d Sep 2026' % number, 'date_local': '2026-09-1%d' % number, 'colour': colour,
            'colour_code': 3, 'hazards': list(hazards), 'quiet': quiet, 'source_text': None,
            'starts_utc': '2026-09-1%dT18:30:00+00:00' % number, 'ends_utc': '2026-09-1%dT18:30:00+00:00' % (number + 1)}


def warnings_view(days=None, district='AHMEDABAD', state='GUJARAT'):
    return {'schema_version': 'product-view-v1', 'view': 'warnings.place', 'status': 'ok',
            'generated_at_utc': '2026-09-15T06:30:00+00:00',
            'data': {'district': district, 'state': state, 'issued_at_utc': '2026-09-15T00:00:00+00:00',
                     'day_boundary_basis': 'Day n is the nth IST calendar day counted from the bulletin date.',
                     'temporal_applicability': 'derived', 'source_locator': '$.features[17]',
                     'days': days if days is not None else [day_row(1), day_row(2, colour='green', hazards=('No warning in this product',), quiet=True)]},
            'sources': [{'source_id': 'S63'}], 'limitations': [], 'not_established': []}


def relay_view(messages=9, eligible=0):
    return {'data': {'messages': messages, 'eligible_by_lifecycle': eligible, 'latest_sent': '2026-09-09T07:24:34+00:00'},
            'sources': [{'source_id': 'S06'}]}


def forecast_view(value=1.2):
    return {'schema_version': 'product-view-v1', 'view': 'forecast.point', 'status': 'ok', 'generated_at_utc': '2026-09-15T06:30:00+00:00',
            'data': {'parameters': {'precipitation': {'unit': 'mm', 'model': 'test model',
                                                      'points': [{'t': '2026-09-15T00:00:00+00:00', 'v': value, 'source_locator': '$.hourly.precipitation[0]'},
                                                                 {'t': '2026-09-15T03:00:00+00:00', 'v': value + 1, 'source_locator': '$.hourly.precipitation[3]'}]}},
                     'days': 3, 'requested': {'latitude': 23.03, 'longitude': 72.59}}, 'sources': [{'source_id': 'S62'}]}


class BriefingTests(unittest.TestCase):
    def test_a_quiet_day_is_a_quiet_day_in_one_product(self):
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.cap_state', return_value=relay_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            briefing = compose(object(), [PLACE], day=2, now=NOW)
        text = markdown(briefing)
        self.assertIn('official day read for 1', summary_line(briefing))
        self.assertIn('quiet in the product for 1', summary_line(briefing))
        self.assertEqual(briefing['places'][0]['official_day']['colour'], 'green')
        self.assertIn('No warning in this product', text)
        import re
        for match in re.finditer('all-clear', text.lower()):
            window = text.lower()[max(0, match.start() - 12):match.start()]
            self.assertIn('not', window, 'an all-clear is only ever named as something this is not')
        self.assertIn('It is not a warning, not an all-clear', text)

    def test_the_relay_is_reported_as_a_separate_product(self):
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.cap_state', return_value=relay_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            briefing = compose(object(), [PLACE], now=NOW)
        text = markdown(briefing)
        self.assertIn('CAP relay (a separate product, never merged', text)
        self.assertEqual(briefing['places'][0]['relay']['messages'], 9)

    def test_a_forecast_is_quoted_as_first_and_last_with_its_sample_count(self):
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.cap_state', return_value=relay_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            briefing = compose(object(), [PLACE], now=NOW)
        window = briefing['places'][0]['forecast']['window']['precipitation']
        self.assertEqual((window['first'], window['last'], window['samples']), (1.2, 2.2, 2))
        self.assertIn('first and last value of the retrieved series', markdown(briefing))
        self.assertIn('model output for a grid cell, not an observation', markdown(briefing))

    def test_a_part_that_cannot_be_read_is_recorded_not_filled(self):
        with patch('weathergpt_data.product_api.warnings_place', side_effect=ValueError('the product refused the request')), \
             patch('weathergpt_data.product_api.cap_state', return_value=None), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            record = place_brief(object(), PLACE)
        self.assertIsNone(record['official_day'])
        self.assertEqual(record['unavailable'][0]['part'], 'official district warning day')
        self.assertIn('the product refused the request', record['unavailable'][0]['why'])

    def test_no_place_is_an_error_rather_than_an_empty_briefing(self):
        with self.assertRaises(Exception):
            compose(object(), [], now=NOW)

    def test_the_change_reading_compares_against_the_previous_record(self):
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()),              patch('weathergpt_data.product_api.cap_state', return_value=relay_view()),              patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            first = compose(object(), [PLACE], now=NOW)
            same = compose(object(), [PLACE], now=NOW, previous=first)
            quiet = json.loads(json.dumps(first))
            quiet['places'][0]['official_day'] = {'quiet': True, 'colour': 'green', 'status_line': 'No warning in this product'}
            changed = compose(object(), [PLACE], now=NOW, previous=quiet)
        self.assertEqual(same['change_since_previous']['reading'], 'same')
        self.assertEqual(same['change_since_previous']['day_changes'][0]['summary'],
                         first['places'][0]['official_day']['status_line'])
        self.assertEqual(changed['change_since_previous']['reading'], 'changed')
        self.assertEqual(changed['change_since_previous']['day_changes'][0]['from']['state'], 'quiet')
        self.assertEqual(changed['change_since_previous']['day_changes'][0]['to']['state'], 'yellow')
        self.assertEqual(changed['change_since_previous']['previous_briefing_id'], first['briefing_id'])

    def test_a_part_read_in_only_one_run_is_not_comparable_not_a_change(self):
        previous = {'briefing_id': 'c' * 64, 'places': [{'label': 'Ahmedabad, Gujarat', 'official_day': None,
                                                          'forecast': {'window': {}}}]}
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.cap_state', return_value=relay_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            briefing = compose(object(), [PLACE], now=NOW, previous=previous)
        change = briefing['change_since_previous']
        self.assertEqual(change['reading'], 'partly_not_comparable')
        self.assertEqual(change['day_changes'][0]['reading'], 'not_comparable')
        self.assertNotEqual(change['reading'], 'changed')

    def test_places_added_and_removed_are_named(self):
        previous = {'briefing_id': 'd' * 64, 'places': [{'label': 'Kochi, Kerala', 'official_day': None, 'forecast': {'window': {}}}]}
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.cap_state', return_value=relay_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            briefing = compose(object(), [PLACE], now=NOW, previous=previous)
        change = briefing['change_since_previous']
        self.assertEqual(change['reading'], 'changed')
        self.assertEqual(change['places_added'], ['Ahmedabad, Gujarat'])
        self.assertEqual(change['places_removed'], ['Kochi, Kerala'])

    def test_the_first_run_says_there_is_nothing_to_compare(self):
        reading = diff(None, {'places': []})
        self.assertEqual(reading['reading'], 'no_previous_run')
        self.assertIn('first briefing in this series', reading['detail'])

    def test_the_identity_is_stable_for_the_same_inputs(self):
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.cap_state', return_value=relay_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            first = compose(object(), [PLACE], now=NOW)
            second = compose(object(), [PLACE], now=NOW)
        self.assertEqual(first['briefing_id'], second['briefing_id'])
        self.assertEqual(len(first['briefing_id']), 64)

    def test_the_document_carries_the_limits_it_is_written_under(self):
        with patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.cap_state', return_value=relay_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            briefing = compose(object(), [PLACE], now=NOW)
        self.assertEqual(briefing['not_established'], NOT_ESTABLISHED)
        text = markdown(briefing)
        self.assertIn('A quiet day in the district warning product is not an all-clear', text)
        self.assertIn('Nothing here is delivered, pushed or scheduled by the workspace itself', text)

    def test_the_series_reader_reads_the_newest_record_and_its_markdown(self):
        folder = Path(tempfile.mkdtemp())
        (folder / 'record-20260915T060000Z.json').write_text(json.dumps({'briefing': {'schema_version': 'briefing-v1', 'places': [], 'not_established': []}}))
        (folder / 'briefing-20260915T060000Z.md').write_text('# Briefing' + chr(10))
        self.assertIsNone(latest(folder / 'missing'))
        found = latest(folder)
        self.assertEqual(found['markdown'], '# Briefing' + chr(10))
        self.assertTrue(found['record_path'].endswith('record-20260915T060000Z.json'))
        self.assertEqual(load_previous(folder / 'record-20260915T060000Z.json')['schema_version'], 'briefing-v1')


if __name__ == '__main__':
    unittest.main()