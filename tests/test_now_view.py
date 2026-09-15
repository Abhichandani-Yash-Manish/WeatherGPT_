"""The right-now reading: observed, in force and next hours, kept apart.

These are offline checks over synthetic product views. They pin the discipline the PS feature
needs: what a station reported is not a district average and not a forecast; the published day is
one product with its own bulletin identity and a quiet day is not an all-clear; the model hours
are grid-cell output quoted as returned; and the reading states where radar and satellite imagery,
sub-hourly refresh and push are not connected.
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from weathergpt_data import now_view, product_api
from weathergpt_data.rule_planner import rule_request

NOW = datetime(2026, 9, 15, 6, 30, tzinfo=timezone.utc)
PLACE = {'latitude': 23.02579, 'longitude': 72.58727, 'label': 'Ahmedabad, Gujarat'}


def warnings_view(colour='yellow', quiet=False):
    return {'schema_version': 'product-view-v1', 'view': 'warnings.place', 'status': 'ok',
            'generated_at_utc': '2026-09-15T06:30:00+00:00',
            'data': {'district': 'AHMADABAD', 'state': 'GUJARAT', 'issued_at_utc': '2026-09-15T06:00:00+00:00',
                     'source_locator': '$.features[17]',
                     'days': [{'day': 1, 'label': '15 Sep 2026', 'colour': colour, 'colour_code': 3,
                               'hazards': ['Thunderstorm/lightning/squall'], 'quiet': quiet, 'source_text': None,
                               'starts_utc': '2026-09-14T18:30:00+00:00', 'ends_utc': '2026-09-15T18:30:00+00:00'},
                              {'day': 2, 'label': '16 Sep 2026', 'colour': 'green', 'colour_code': 1,
                               'hazards': ['No warning in this product'], 'quiet': True, 'source_text': None,
                               'starts_utc': '2026-09-15T18:30:00+00:00', 'ends_utc': '2026-09-16T18:30:00+00:00'}]},
            'sources': [{'source_id': 'S63', 'retrieved_at_utc': '2026-09-15T06:31:00+00:00'}],
            'limitations': ['Day windows are derived from the bulletin date.']}


def bundle_view():
    return {'data': {'networks': {'metar': [{'name': 'AHMEDABAD', 'station_code': 'VAAH', 'distance_km': 5.76,
                                                   'observed_at_utc': '2026-09-15T05:30:00+00:00', 'age_minutes': 60.0,
                                                   'parameters': [{'field': 'temperature_c', 'value': '28.0', 'unit': '°C', 'unit_stated_by_source': True}]}],
                             'aws': [{'name': 'AHMEDABAD', 'station_code': 'AWS1', 'distance_km': 4.2,
                                      'observed_at_utc': '2026-09-15T00:00:00+00:00', 'age_minutes': 390.0,
                                      'parameters': [{'field': 'temperature_c', 'value': '25.0', 'unit': '°C', 'unit_stated_by_source': True}]}]}},
            'sources': [{'source_id': 'S63', 'retrieved_at_utc': '2026-09-15T06:31:00+00:00'}]}


def forecast_view():
    def points(name, start_hour, count):
        return {'unit': '°C', 'model': 'test model', 'points': [
            {'t': '2026-09-15T%02d:00:00+00:00' % (start_hour + index), 'v': 25.0 + index,
             'source_locator': '$.hourly.%s[%d]' % (name, start_hour + index)} for index in range(count)]}
    return {'data': {'parameters': {'temperature_2m': points('temperature_2m', 6, 8),
                                    'precipitation_probability': points('precipitation_probability', 6, 8)}},
            'sources': [{'source_id': 'S62', 'retrieved_at_utc': '2026-09-15T06:31:00+00:00'}]}


class DayStateTests(unittest.TestCase):
    def test_the_published_day_containing_now_is_the_one_reported(self):
        day = now_view.day_state(warnings_view(), now=NOW)
        self.assertEqual(day['day'], 1)
        self.assertEqual(day['district'], 'AHMADABAD')
        self.assertEqual(day['source_id'], 'S63')
        self.assertIn('Official district warning: yellow', day['status_line'])

    def test_a_quiet_day_is_reported_as_a_quiet_day_in_one_product(self):
        day = now_view.day_state(warnings_view(quiet=True, colour='green'), now=NOW)
        self.assertTrue(day['quiet'])
        self.assertIn('No warning in this product', day['status_line'])
        self.assertNotIn('all-clear is in force', day['status_line'])

    def test_no_published_day_is_an_absence_not_a_day(self):
        self.assertIsNone(now_view.day_state({'data': {'days': []}}, now=NOW))


class NextHoursTests(unittest.TestCase):
    def test_the_next_hours_start_at_the_current_source_hour(self):
        hours = now_view.next_hours(forecast_view(), hours=6, now=NOW)
        self.assertEqual(len(hours['rows']), 6)
        self.assertEqual(hours['rows'][0]['at'], '2026-09-15T06:00:00+00:00')
        self.assertEqual(hours['source_id'], 'S62')
        self.assertEqual(hours['rows'][0]['temperature_2m'], 25.0)

    def test_no_series_is_an_absence_not_a_zero(self):
        hours = now_view.next_hours({'data': {'parameters': {}}, 'sources': []}, hours=6, now=NOW)
        self.assertEqual(hours['rows'], [])
        self.assertEqual(hours['status'], 'unavailable')


class ComposedReadingTests(unittest.TestCase):
    def compose(self):
        with patch('weathergpt_data.product_api.observations_bundle', return_value=bundle_view()), \
             patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            return now_view.compose(object(), PLACE['latitude'], PLACE['longitude'], now=NOW)

    def test_the_three_parts_keep_their_own_status_and_source(self):
        reading = self.compose()
        self.assertEqual(reading['observed']['status'], 'ok')
        self.assertEqual(reading['in_force']['status'], 'ok')
        self.assertEqual(reading['next_hours']['status'], 'ok')
        self.assertEqual(reading['observed']['sources'], ['S63'])
        self.assertEqual(reading['in_force']['source_id'], 'S63')
        self.assertEqual(reading['next_hours']['source_id'], 'S62')
        self.assertEqual(reading['sources'], ['S63', 'S62'])

    def test_the_summary_names_the_nearest_and_the_freshest_station(self):
        summary = self.compose()['summary']
        self.assertIn('Nearest station AHMEDABAD', summary)
        self.assertIn('(4.2 km)', summary)
        self.assertIn('Freshest report in range', summary)
        self.assertIn('The nearest station is not always the freshest one', summary)

    def test_the_summary_says_what_is_not_connected(self):
        summary = self.compose()['summary']
        self.assertIn('radar and satellite imagery', summary)
        self.assertIn('sub-hourly refresh between source hours', summary)
        self.assertIn('any push or notification', summary)

    def test_a_missing_part_is_recorded_and_the_reading_still_stands(self):
        def refuse(*args, **kwargs):
            raise ValueError('the product refused the request')

        with patch('weathergpt_data.product_api.observations_bundle', side_effect=refuse), \
             patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            reading = now_view.compose(object(), PLACE['latitude'], PLACE['longitude'], now=NOW)
        self.assertEqual(reading['observed']['status'], 'unavailable')
        self.assertIn('refused the request', reading['observed']['why'])
        self.assertEqual(reading['in_force']['status'], 'ok')
        self.assertEqual(reading['status'], 'ok')

    def test_the_reading_does_not_claim_a_warning_or_a_forecast_from_a_station(self):
        reading = self.compose()
        joined = ' '.join(reading['not_established'])
        self.assertIn('not a district average', joined)
        self.assertIn('not an all-clear', joined)
        self.assertIn('not observations', joined)

    def test_the_view_and_its_envelope_carry_the_reading(self):
        with patch('weathergpt_data.product_api.observations_bundle', return_value=bundle_view()), \
             patch('weathergpt_data.product_api.warnings_place', return_value=warnings_view()), \
             patch('weathergpt_data.product_api.forecast', return_value=forecast_view()):
            view = product_api.now_view(object(), PLACE['latitude'], PLACE['longitude'], now=NOW)
        self.assertEqual(view['view'], 'now.composed')
        self.assertEqual(view['status'], 'ok')
        self.assertEqual(view['coverage']['stations'], 2)
        self.assertEqual([source['source_id'] for source in view['sources']], ['S63', 'S62'])
        self.assertTrue(any('radar and satellite imagery' in note for note in view['limitations']))


class RightNowPlanningTests(unittest.TestCase):
    def test_a_right_now_question_is_an_observation_task(self):
        request = rule_request("What's it like right now in Ahmedabad?", NOW)
        self.assertIsNotNone(request)
        self.assertEqual([(task['kind'], task['operation']) for task in request['tasks']], [('observation', 'lookup')])

    def test_a_station_code_in_a_right_now_question_is_an_airport_report(self):
        # Measured live: "what is being observed at VOBL right now" was planned as a settlement
        # observation and asked the reader to name a place the question already named.
        request = rule_request('What is being observed at VOBL right now?', NOW)
        self.assertEqual([task['kind'] for task in request['tasks']], ['aviation'])
        self.assertEqual([place['name'] for place in request['places']], ['VOBL'])


if __name__ == '__main__':
    unittest.main()