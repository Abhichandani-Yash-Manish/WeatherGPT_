"""Regressions for the six stakeholder findings of 15 September 2026.

Each case is a component check over synthetic or recorded inputs. They establish the
specific repaired behaviour, not live product acceptance or a completion measure.
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from test_district_warnings import record

NOW = datetime(2026, 9, 15, 4, 0, tzinfo=timezone.utc)


# --- SA01: the opening warning headline is derived from the same day rows as the strip ---

class WarningHeadlineTests(unittest.TestCase):
    def foundation(self, saved):
        class Stub:
            def warning_snapshot(self, latitude, longitude, refresh=False):
                return {'records': [saved], 'provenance': {'source_id': 'S63'}, 'coverage': {}, 'limitations': []}
        return Stub()

    def test_a_hazard_day_cannot_sit_under_a_quiet_headline(self):
        from weathergpt_data import product_api
        view = product_api.warnings_place(self.foundation(record()), 25.6, 85.1)
        data = view['data']
        self.assertTrue(data['has_hazard'])
        self.assertEqual(data['severity'], 'yellow')
        self.assertNotEqual(data['headline'], 'No warning in this product')
        self.assertIn('day', data['summary'].lower())

    def test_a_genuinely_quiet_record_is_stated_as_quiet(self):
        days = [{'source_day': 1, 'hazard_codes': [1], 'hazards': ['No warning in this product'],
                 'colour': 'green', 'colour_code': 4, 'source_text': ''}]
        from weathergpt_data import product_api
        view = product_api.warnings_place(self.foundation(record(days=days)), 25.6, 85.1)
        data = view['data']
        self.assertFalse(data['has_hazard'])
        self.assertIsNone(data['severity'])
        self.assertEqual(data['headline'], 'No warning in this product')

    def test_an_absent_summary_is_unknown_not_a_quiet_claim(self):
        from weathergpt_data import product_api
        days = [{'source_day': 1, 'hazard_codes': [], 'hazards': [],
                 'colour': None, 'colour_code': None, 'source_text': ''}]
        data = product_api.warnings_place(self.foundation(record(days=days)), 25.6, 85.1)['data']
        self.assertIsNone(data['has_hazard'])
        self.assertEqual(data['headline'], 'Warning state not established')



# --- SA02: every requested historical measure is preserved ---

class MultiMeasureHistoryTests(unittest.TestCase):
    def plan(self, question):
        from weathergpt_data.rule_planner import rule_request
        return rule_request(question, NOW, [])

    def test_both_parameter_orderings_keep_both_measures(self):
        for question, expected in [
                ('Show India annual rainfall and mean temperature for 2024.', ['rainfall', 'temperature']),
                ('Show India annual mean temperature and rainfall for 2024.', ['temperature', 'rainfall'])]:
            with self.subTest(question=question):
                request = self.plan(question)
                self.assertEqual(request['tasks'][0]['parameters'], expected)

    def test_a_single_measure_is_unchanged(self):
        self.assertEqual(self.plan('Show India annual rainfall for 2024.')['tasks'][0]['parameters'], ['rainfall'])

    def test_execute_history_answers_every_requested_measure(self):
        from weathergpt_data.historical_tasks import execute_history
        seen = []

        def lookup(query):
            parameter = query['history_parameter']
            seen.append(parameter)
            return {'status': 'answered', 'text': parameter + ' value',
                    'facts': [{'value': '1', 'unit': 'mm' if parameter == 'rainfall' else '°C',
                               'place': 'India', 'source_id': 'S25'}],
                    'citations': [{'id': 'c', 'source_id': 'S25'}], 'notes': [],
                    'raw': {'provenance': {'series_id': 'all-india'}}}

        plan = {'places': [{'name': 'India', 'state': '', 'district': '', 'kind': 'country'}]}
        task = {'kind': 'history', 'operation': 'lookup', 'parameters': ['rainfall', 'temperature'],
                'years': [2024], 'period': 'annual', 'place_indices': [0]}
        result = execute_history(plan, task, lookup=lookup)
        self.assertEqual(seen, ['rainfall', 'temperature'])
        self.assertEqual(result['status'], 'answered')
        self.assertEqual({f['parameter'] for f in result['facts']}, {'rainfall', 'temperature'})


# --- SA03: an unsupported water level is stated, not answered with weather ---

class WaterLevelTests(unittest.TestCase):
    def test_the_planner_routes_a_water_level_to_the_river_tool(self):
        from weathergpt_data.rule_planner import rule_request
        request = rule_request('What is the observed water level near Patna, Bihar now?', NOW, [])
        task = request['tasks'][0]
        self.assertEqual((task['kind'], task['parameters']), ('river', ['water_level']))

    def test_the_tool_states_the_unsupported_quantity_without_a_window(self):
        from weathergpt_data.specialist_tasks import execute_specialist
        result = {'facts': [], 'citations': [], 'notes': [], 'charts': [], 'trace': {'tools': []}}
        plan = {'start_local': '', 'end_local': '', 'places': [{'name': 'Patna'}]}
        task = {'kind': 'river', 'operation': 'lookup', 'parameters': ['water_level'],
                'request_quote': 'observed water level near Patna, Bihar now'}
        out = execute_specialist(object(), result, plan, task, {}, None)
        self.assertEqual(out['status'], 'unavailable')
        self.assertIn('water level', out['answer'])
        self.assertIn('never substituted by a discharge value', out['answer'])
        self.assertFalse(out['facts'])

    def test_groundwater_is_still_out_of_scope_research(self):
        from weathergpt_data.rule_planner import rule_request
        request = rule_request('What is the groundwater level in Ahmedabad?', NOW, [])
        self.assertEqual(request['tasks'][0]['kind'], 'research')

    def test_an_ordinary_warning_level_question_keeps_the_warning_route(self):
        from weathergpt_data.rule_planner import rule_request
        request = rule_request('What is the warning level for Ahmedabad?', NOW, [])
        self.assertEqual((request['tasks'][0]['kind'], request['tasks'][0]['parameters']),
                         ('warning', ['official_warning']))

    def test_a_river_danger_level_is_still_routed_to_the_river_tool(self):
        from weathergpt_data.rule_planner import rule_request
        request = rule_request('What is the danger level of the river at Patna tomorrow?', NOW, [])
        self.assertEqual((request['tasks'][0]['kind'], request['tasks'][0]['parameters']),
                         ('river', ['danger_level']))


# --- SA04: model readiness separates service reachability from installed model ---

class ProviderReadinessTests(unittest.TestCase):
    def test_ollama_reports_a_reachable_service_with_a_missing_model(self):
        from weathergpt_data.providers import OllamaClient
        client = OllamaClient(model='qwen3.6:latest')
        with patch.object(client, 'catalogue', return_value=['kimi-k2.6:cloud']):
            available, reason = client.available()
        self.assertFalse(available)
        self.assertIn('qwen3.6:latest', reason)
        self.assertIn('reachable', reason)
        self.assertNotIn('unreachable', reason)

    def test_ollama_is_available_when_the_model_is_installed(self):
        from weathergpt_data.providers import OllamaClient
        client = OllamaClient(model='local:latest')
        with patch.object(client, 'catalogue', return_value=['local:latest']):
            self.assertEqual(client.available(), (True, ''))

    def test_preflight_separates_reachable_from_installed(self):
        from weathergpt_data import preflight
        from weathergpt_data.providers import ProviderUnavailable
        with patch('weathergpt_data.providers.OllamaClient.catalogue', side_effect=ProviderUnavailable('refused')):
            report = preflight.providers(probe_ollama=True)
        self.assertFalse(report['ollama']['reachable'])
        self.assertIn('refused', report['ollama']['why'])
        with patch('weathergpt_data.providers.OllamaClient.catalogue', return_value=['kimi-k2.6:cloud']):
            report = preflight.providers(probe_ollama=True)
        self.assertTrue(report['ollama']['reachable'])
        self.assertFalse(report['ollama']['wanted_installed'])
        self.assertIn('not installed', report['ollama']['why'])


# --- SA05: saved source fixtures resolve from tracked curated evidence ---

class SavedFixtureTests(unittest.TestCase):
    def test_every_bulletin_layout_fixture_resolves(self):
        import source_fixtures
        shas = ['653f005c5eb6069e2d4b21afb2700b993f7d1d0699781876d698ef553811cd90',
                '99b77dc84e6bec60bfe3a5cd64b0d8247761b43abed6af3a63b056b0edfe7b9f',
                'f5e9fbe91b5fe14b3b9a3290517696b279cf93b327c4067b9c7ee0225df71e07',
                '57e47b6892371cb3a87f9aa9ca648deee8adaa055f5bc36f7c935b00263ec8ee',
                '5e8120cf3b228944634faa709f524f3a76c0c4e043635e4a3fce7b4739bcf9bb',
                '2a5c1798e89380e862a2c429522f7a1c18b459f912bf600c1d449c787954b730']
        for sha in shas:
            with self.subTest(sha=sha):
                self.assertGreater(len(source_fixtures.bulletin_blob(sha)), 1000)

    def test_a_missing_fixture_names_itself_rather_than_skipping(self):
        import source_fixtures
        with self.assertRaises(FileNotFoundError) as raised:
            source_fixtures.bulletin_blob('0' * 64)
        self.assertIn('0' * 64, str(raised.exception))


# --- SA06: a notification request is not a place called Notify ---

class WatchIntentPlaceTests(unittest.TestCase):
    def test_notify_is_not_extracted_as_a_place(self):
        from weathergpt_data.rule_planner import rule_request
        for question in ('Notify me if there is a weather warning for Ahmedabad, Gujarat.',
                         'Notify me if a cyclone warning is issued for Kochi.'):
            with self.subTest(question=question):
                request = rule_request(question, NOW, [])
                self.assertEqual([place['name'] for place in request['places']], ['Ahmedabad']
                                 if 'Ahmedabad' in question else ['Kochi'])

    def test_places_of_never_returns_a_watch_verb(self):
        from weathergpt_data.rule_planner import places_of
        self.assertEqual([p['name'] for p in places_of('Notify me if a warning is issued for Patna, Bihar.')],
                         ['Patna'])


if __name__ == '__main__':
    unittest.main()
