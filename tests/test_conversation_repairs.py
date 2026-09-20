"""Conversation-level repairs: the station fields a reader means, the follow-up that must not fail,
and the explanation that must not be small talk.

Each of these was measured on the live engine on 21 September 2026, and each is asserted from both
sides - the repair must fire where it exists to, and must not fire where it would change a correct
answer - because a rule that misfires is a worse defect than the one it fixes.
"""
import datetime
import json
import unittest

import test_answers as fixture
from test_conversation import Model, Places
from test_ingestion import Response, payload
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.dialogue import CORE_FORECAST_MEASURES, EXPLAIN_ONLY, reconcile
from weathergpt_data.leadline import lead_sentence
from weathergpt_data.observation_tasks import _hour_facts, _station_facts
from weathergpt_data.workspace import Workspace
from weathergpt_data.workspace_brief import brief, wired_source_ids


def station(observed, parameters):
    return {'observed_at_utc': observed, 'station_code': 'VASU', 'name': 'SURAT',
            'network': 'metar', 'parameters': parameters}


class StationFieldTests(unittest.TestCase):
    """The two station layers spell the same measurement differently, and neither says so."""

    def facts(self, parameters):
        result = {'facts': []}
        made = _station_facts(result, station('2026-09-21T00:00:00+00:00', parameters),
                              'SURAT · 13.4 km from the requested point', 'S63', 'v1', 'c1')
        return {row['parameter']: row for row in made}

    def test_a_metar_station_yields_temperature_and_humidity(self):
        """The layer prints `temp` and `rh`; the reader's question is answered in °C and %."""
        made = self.facts([{'field': 'temp', 'value': 26, 'unit': None},
                           {'field': 'rh', 'value': '94.0', 'unit': None},
                           {'field': 'windsp', 'value': '0.0', 'unit': None}])
        self.assertEqual(made['temperature_c']['value'], '26')
        self.assertEqual(made['relative_humidity_2m']['value'], '94.0')
        self.assertEqual(made['wind_speed_kt']['value'], '0.0')

    def test_the_aws_spelling_of_wind_is_read_too(self):
        made = self.facts([{'field': 'windspeed', 'value': '6.1', 'unit': None}])
        self.assertEqual(made['wind_speed_kt']['value'], '6.1')

    def test_a_unit_the_layer_did_not_state_is_recorded_as_the_parameters_own(self):
        made = self.facts([{'field': 'temp', 'value': 26, 'unit': None}])
        row = made['temperature_c']
        self.assertEqual(row['unit'], '°C')
        self.assertEqual(row['unit_source'], 'parameter_convention')

    def test_a_station_that_can_see_says_so_in_words(self):
        made = self.facts([{'field': 'weather', 'value': 'mist', 'unit': None},
                           {'field': 'nebulosity', 'value': 'a few clouds at 2000 feet', 'unit': None}])
        self.assertEqual(made['present_weather']['value'], 'mist')
        self.assertEqual(made['sky_condition']['value'], 'a few clouds at 2000 feet')

    def test_a_bare_numeric_weather_code_is_not_a_condition(self):
        """The AWS layer prints `weather: 0`; this product holds no table that decodes it."""
        made = self.facts([{'field': 'weather', 'value': 0, 'unit': None},
                           {'field': 'nebulosity', 'value': 4, 'unit': None}])
        self.assertNotIn('present_weather', made)
        self.assertNotIn('sky_condition', made)

    def test_a_field_the_station_did_not_report_is_absent_rather_than_zero(self):
        made = self.facts([{'field': 'temp', 'value': 26, 'unit': None}])
        self.assertNotIn('mslp', made)


class HourFactTests(unittest.TestCase):
    """The right-now reading's model hours reach the composer as facts, and as FORECAST facts."""

    def reading(self):
        return {'next_hours': {'status': 'ok', 'source_id': 'S62', 'model': 'gfs_seamless',
                               'unit': {'temperature_2m': '°C', 'precipitation': 'mm',
                                        'precipitation_probability': '%', 'wind_speed_10m': 'km/h'},
                               'rows': [{'at': '2026-09-20T22:00:00+00:00', 'temperature_2m': 25.5,
                                         'precipitation_probability': 0, 'precipitation': 0.0,
                                         'wind_speed_10m': 3.1},
                                        {'at': '2026-09-20T23:00:00+00:00', 'temperature_2m': 25.4,
                                         'precipitation_probability': 0, 'precipitation': 0.0,
                                         'wind_speed_10m': 3.7}]}}

    def test_the_hours_are_facts_with_a_window_and_a_source(self):
        rows = _hour_facts({'facts': []}, self.reading(), 'Surat')
        self.assertEqual(len(rows), 8)
        first = rows[0]
        self.assertEqual(first['evidence_kind'], 'forecast')
        self.assertEqual(first['source_id'], 'S62')
        self.assertEqual(first['start'], '2026-09-20T22:00:00+00:00')
        self.assertEqual(first['end'], '2026-09-20T23:00:00+00:00')
        self.assertEqual(first['unit'], '°C')

    def test_a_hour_is_not_placed_at_the_station(self):
        """A grid-cell hour read as a station reading is the substitution this product refuses."""
        rows = _hour_facts({'facts': []}, self.reading(), 'Surat')
        self.assertTrue(all(row['place'] == 'Surat' for row in rows))
        self.assertTrue(all(row['method'] == 'model_hour_for_point' for row in rows))
        self.assertTrue(all(row['observed_at'] is None for row in rows))

    def test_an_unavailable_reading_contributes_nothing(self):
        self.assertEqual(_hour_facts({'facts': []}, {'next_hours': {'status': 'unavailable'}}, 'Surat'), [])

    def test_the_opening_sentence_states_the_hours_as_grid_cell_output(self):
        packet = {'lead': '', 'plan': {'intent': 'observation'},
                  'resolved_points': {'Surat': {'label': 'Surat, Sūrat, State of Gujarāt'}},
                  'facts': [{'id': 'f1', 'parameter': 'temperature_c', 'value': '26', 'unit': '°C',
                             'place': 'SURAT · 13.4 km from the requested point', 'start': '2026-09-20T22:00:00+00:00',
                             'end': '2026-09-20T22:00:00+00:00', 'observed_at': '2026-09-20T22:00:00+00:00'}]
                  + _hour_facts({'facts': []}, self.reading(), 'Surat')}
        sentence = lead_sentence(packet, 'observation')
        self.assertIn('26 °C', sentence)
        self.assertIn('grid-cell output', sentence)
        self.assertNotIn('T22:00:00', sentence)


class ReconcileRepairTests(unittest.TestCase):
    """Two repairs in reconcile, each measured on the live engine."""

    def plan(self, kind='forecast', parameters=None, action='follow_up'):
        return {'intent': kind, 'language': 'en', 'places': [], 'start_local': '', 'end_local': '',
                'context_action': action, 'changed_fields': [],
                'explicit_times': False, 'variables': [], 'year': 0, 'period': 'annual',
                'history_parameter': 'rainfall', 'unsupported_parameters': [], 'assumptions': [],
                'clarification': '', 'requested_outcome': '', 'tasks': [
                    {'kind': kind, 'operation': 'lookup', 'parameters': list(parameters or []),
                     'years': [], 'period': 'annual', 'start_local': '2026-09-22T00:30:00+05:30',
                     'end_local': '2026-09-23T00:30:00+05:30', 'place_indices': [0],
                     'request_quote': 'and tomorrow?'}]}

    def history(self, kind='observation', start='', end=''):
        return {'last_plan': {'tasks': [{'kind': kind, 'operation': 'lookup', 'parameters': [],
                                         'years': [], 'period': 'annual', 'start_local': start,
                                         'end_local': end, 'place_indices': [0],
                                         'request_quote': 'what is it like right now?'}]}}

    def test_a_forecast_that_names_no_measure_gets_the_measures_a_reader_means(self):
        """Measured: "and tomorrow?" after an observation came back "No supported parameters requested"."""
        # The prior turn was the observation, so the window moving past it is what makes this a
        # forecast at all - the same shape the live engine produced for "and tomorrow?".
        state = self.history(start='2026-09-20T00:00:00+05:30', end='2026-09-21T00:00:00+05:30')
        plan = reconcile(self.plan('forecast', []), state, 'and tomorrow?')
        self.assertEqual(plan['tasks'][0]['kind'], 'forecast')
        self.assertEqual(plan['tasks'][0]['parameters'], list(CORE_FORECAST_MEASURES))

    def test_a_forecast_that_names_a_measure_keeps_it(self):
        state = self.history()
        plan = reconcile(self.plan('forecast', ['wind_speed_10m']), state, 'and the wind?')
        self.assertEqual(plan['tasks'][0]['parameters'], ['wind_speed_10m'])

    def test_a_running_observation_keeps_its_empty_parameter_list(self):
        """An observation reads a fixed station field set; the repair is for forecasts only."""
        plan = reconcile(self.plan('observation', []), self.history(), 'what is it like right now?')
        self.assertEqual(plan['tasks'][0]['parameters'], [])

    def test_a_bare_why_is_an_explanation_when_there_is_evidence_behind_it(self):
        plan = reconcile(self.plan('chat', []), self.history(), 'why?')
        self.assertEqual(plan['context_action'], 'explain_previous')
        self.assertEqual(plan['tasks'][0]['kind'], 'explanation')

    def test_a_bare_why_with_nothing_behind_it_stays_conversational(self):
        plan = reconcile(self.plan('chat', []), {}, 'why?')
        self.assertNotEqual(plan.get('context_action'), 'explain_previous')

    def test_a_question_about_a_place_is_not_read_as_an_explanation_request(self):
        for question in ('why is it raining in Surat', 'and tomorrow?', 'what is the wind doing'):
            with self.subTest(question=question):
                self.assertIsNone(EXPLAIN_ONLY.match(question))


class WorkspacePictureTests(unittest.TestCase):
    """The picture handed to a conversational turn has to be true, because a reply repeats it."""

    def test_the_wired_sources_are_read_from_where_the_ledger_keeps_them(self):
        """`wired_to_chat` is nested under `connector`; read at the top level it is always false."""
        self.assertTrue(wired_source_ids(), 'the ledger says sources are wired to chat; the brief must say so')
        picture = json.loads(brief(datetime.datetime.now(datetime.timezone.utc)))
        self.assertTrue(picture['sources']['wired_to_chat'])
        self.assertEqual(picture['sources']['connected'], picture['sources']['wired_to_chat'])

    def test_a_reply_that_denies_the_workspace_has_sources_is_refused(self):
        self.assertIsNotNone(ConversationEngine.CHAT_WIRING.search('no source is wired to this chat'))
        self.assertIsNotNone(ConversationEngine.CHAT_WIRING.search('There are no sources wired into this workspace.'))
        self.assertIsNone(ConversationEngine.CHAT_WIRING.search(
            'I can check the forecast for Surat if you name the day.'))


if __name__ == '__main__':
    unittest.main()
