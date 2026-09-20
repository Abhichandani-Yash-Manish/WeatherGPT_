"""Model access: provider routing, failover, budgets and the planner policy.

These are component checks over stub endpoints and local configuration. They take no
measurement of any provider: what they pin is the behaviour the architecture promises -
the model plans every turn by default, a provider failure is routed around, and a total provider
outage falls back to the deterministic rules planner while SAYING it did - never silently, and
never at all for a question the rules cannot read. Nothing in this layer can put a value into an
answer: the fallback changes how a question is read, never where a number comes from.
"""
import json
import threading
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from weathergpt_data import providers
from weathergpt_data.providers import (DeepSeekClient, ModelRouter, OllamaClient, OpenRouterClient,
                                       ProviderUnavailable, extract_json)
from weathergpt_data.transport import SourceError
from weathergpt_data.rule_planner import rule_request

NOW = datetime(2026, 9, 15, 3, 0, tzinfo=timezone.utc)
SCHEMA = {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'],
          'additionalProperties': False}


class Stub:
    """A local HTTP endpoint that answers a scripted list of (status, body) and records requests."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                stub.requests.append({'method': 'GET', 'path': self.path, 'headers': dict(self.headers)})
                self._answer()

            def do_POST(self):
                length = int(self.headers.get('Content-Length') or 0)
                raw = self.rfile.read(length) if length else b''
                try:
                    body = json.loads(raw or b'{}')
                except ValueError:
                    body = raw.decode('utf-8', 'replace')
                stub.requests.append({'method': 'POST', 'path': self.path, 'headers': dict(self.headers), 'body': body})
                self._answer()

            def _answer(self):
                if not stub.responses:
                    status, body = 500, {'error': {'message': 'no scripted response'}}
                else:
                    status, body = stub.responses.pop(0)
                payload = json.dumps(body).encode() if not isinstance(body, bytes) else body
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:%d' % self.server.server_port

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def reply(content='{"ok": true}', model='test/model:free', usage=None, provider='TestRoute'):
    return 200, {'choices': [{'message': {'content': content}}], 'model': model,
                 'usage': usage or {'prompt_tokens': 11, 'completion_tokens': 7}, 'provider': provider}


class ExtractionTests(unittest.TestCase):
    def test_plain_fenced_and_prose_wrapped_json_are_read(self):
        self.assertEqual(extract_json('{"ok": true}'), {'ok': True})
        self.assertEqual(extract_json('\n' + chr(96) * 3 + 'json\n{"ok": true}\n' + chr(96) * 3), {'ok': True})
        self.assertEqual(extract_json('Here is the plan:\n{"ok": true}\nHope that helps.'), {'ok': True})
        self.assertEqual(extract_json('nested {"note": {"ok": true}} tail'), {'note': {'ok': True}})

    def test_a_reply_without_json_is_refused(self):
        with self.assertRaises(ProviderUnavailable):
            extract_json('I cannot do that.')
        with self.assertRaises(ProviderUnavailable):
            extract_json('')


class ConfigurationTests(unittest.TestCase):
    def test_the_environment_key_wins_and_the_local_file_is_the_fallback(self):
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'env-key'}, clear=False):
            self.assertEqual(providers.openrouter_key(), 'env-key')
            self.assertIn('environment', providers.key_source())
        with patch.dict('os.environ', {}, clear=True):
            with patch.object(providers, 'local_config', return_value={'openrouter_api_key': 'file-key'}):
                self.assertEqual(providers.openrouter_key(), 'file-key')
                self.assertIn('model-config.json', providers.key_source())
        with patch.dict('os.environ', {}, clear=True):
            with patch.object(providers, 'local_config', return_value={}):
                self.assertEqual(providers.openrouter_key(), '')
                self.assertEqual(providers.key_source(), 'not configured')

    def test_the_model_list_is_free_first_and_configurable(self):
        with patch.dict('os.environ', {}, clear=True):
            with patch.object(providers, 'local_config', return_value={}):
                models = providers.free_models()
                self.assertTrue(all(model.endswith(':free') for model in models))
                # Changed on 15 September 2026: the previous assertion hard-coded one id, and the
                # live catalogue then stopped publishing it. The intent is the registry order, so
                # the assertion now reads the registry instead of naming today's model.
                self.assertEqual(models, providers.free_model_ranking())
        with patch.dict('os.environ', {'WEATHERGPT_MODELS': 'a/b:free, c/d:free'}, clear=True):
            # Changed on 15 September 2026: the curated registry is the routing order, most
            # capable first, and a configured list is appended after it rather than replacing it.
            ranking = providers.free_model_ranking()
            self.assertEqual(providers.free_models(), ranking + ('a/b:free', 'c/d:free'))
            self.assertTrue(all(model.endswith(':free') for model in providers.free_models()))

    def test_the_ollama_adapter_refuses_a_remote_endpoint(self):
        with self.assertRaises(ValueError):
            OllamaClient(base='https://example.com')


class OpenRouterTests(unittest.TestCase):
    def client(self, stub, models=('first/model:free', 'second/model:free')):
        return OpenRouterClient(key='test-key', models=models, timeout=5, base=stub.base)

    def test_the_request_carries_the_schema_and_the_key(self):
        stub = Stub([reply()])
        self.addCleanup(stub.close)
        data, meta = self.client(stub).complete('system text', 'user text', SCHEMA, max_tokens=333)
        self.assertEqual(data, {'ok': True})
        request = stub.requests[0]
        self.assertEqual(request['path'], '/chat/completions')
        self.assertEqual(request['headers'].get('Authorization'), 'Bearer test-key')
        self.assertEqual(request['body']['model'], 'first/model:free')
        self.assertEqual(request['body']['temperature'], 0)
        self.assertEqual(request['body']['max_tokens'], 333)
        self.assertEqual(request['body']['response_format']['type'], 'json_schema')
        self.assertEqual(request['body']['response_format']['json_schema']['schema'], SCHEMA)
        self.assertTrue(request['body']['provider']['require_parameters'])
        self.assertEqual(meta['provider'], 'openrouter')
        self.assertEqual(meta['model'], 'first/model:free')
        self.assertEqual(meta['input_tokens'], 11)
        self.assertEqual(meta['output_tokens'], 7)
        self.assertLessEqual(meta['latency_ms'], 5000)

    def test_a_rate_limit_fails_over_to_the_next_model(self):
        stub = Stub([(429, {'error': {'message': 'rate limited'}}), (429, {'error': {'message': 'rate limited'}}), reply()])
        self.addCleanup(stub.close)
        with patch.object(providers, 'RETRY_BACKOFF_SECONDS', 0.01):
            data, meta = self.client(stub).complete('s', 'u', SCHEMA)
        self.assertEqual(data, {'ok': True})
        self.assertEqual(meta['model'], 'second/model:free')
        self.assertEqual(meta['attempts'], 3)
        self.assertEqual([request['body']['model'] for request in stub.requests],
                         ['first/model:free', 'first/model:free', 'second/model:free'])

    def test_a_refused_key_disables_the_provider_instead_of_retrying(self):
        stub = Stub([(401, {'error': {'message': 'no auth'}})])
        self.addCleanup(stub.close)
        client = self.client(stub)
        with self.assertRaises(ProviderUnavailable) as raised:
            client.complete('s', 'u', SCHEMA)
        self.assertIn('refused', str(raised.exception))
        available, reason = client.available()
        self.assertFalse(available)
        self.assertIn('refused', reason)
        with self.assertRaises(ProviderUnavailable):
            client.complete('s', 'u', SCHEMA)
        self.assertEqual(len(stub.requests), 1, 'a refused key is not retried')

    def test_a_model_level_refusal_moves_on_without_retrying_it(self):
        stub = Stub([(404, {'error': {'message': 'model unavailable'}}), reply(model='second/model:free')])
        self.addCleanup(stub.close)
        data, meta = self.client(stub).complete('s', 'u', SCHEMA)
        self.assertEqual(meta['model'], 'second/model:free')
        self.assertEqual(len(stub.requests), 2)

    def test_a_200_body_carrying_an_upstream_error_moves_down_the_free_order(self):
        overloaded = (200, {'error': {'message': 'Upstream error from Nvidia: Service temporarily overloaded',
                                      'code': 502, 'metadata': {'error_type': 'provider_unavailable'}}})
        stub = Stub([overloaded, overloaded, reply(model='second/model:free')])
        self.addCleanup(stub.close)
        data, meta = self.client(stub).complete('s', 'u', SCHEMA)
        self.assertEqual(data, {'ok': True})
        self.assertEqual(meta['model'], 'second/model:free')
        self.assertEqual([request['body']['model'] for request in stub.requests],
                         ['first/model:free', 'first/model:free', 'second/model:free'],
                         'a body-level failure belongs to the model, so the next free id is tried')

    def test_an_upstream_error_is_named_when_every_attempt_fails(self):
        overloaded = (200, {'error': {'message': 'Upstream error from Nvidia: Service temporarily overloaded',
                                      'code': 502, 'metadata': {'error_type': 'provider_unavailable'}}})
        stub = Stub([overloaded, overloaded])
        self.addCleanup(stub.close)
        with self.assertRaises(ProviderUnavailable) as raised:
            self.client(stub, models=('first/model:free',)).complete('s', 'u', SCHEMA)
        message = str(raised.exception)
        self.assertIn('upstream error 502', message)
        self.assertIn('Service temporarily overloaded', message)

    def test_a_prose_reply_is_read_and_a_non_json_reply_fails_over(self):
        stub = Stub([reply('I think the plan is: {"ok": true}')])
        self.addCleanup(stub.close)
        data, _ = self.client(stub, models=('first/model:free',)).complete('s', 'u', SCHEMA)
        self.assertEqual(data, {'ok': True})
        stub2 = Stub([reply('sorry, no json here'), reply('still no json'), reply('nope')])
        self.addCleanup(stub2.close)
        with self.assertRaises(ProviderUnavailable) as raised:
            self.client(stub2, models=('first/model:free',)).complete('s', 'u', SCHEMA)
        self.assertIn('not JSON', str(raised.exception))

    def test_no_key_means_no_request(self):
        stub = Stub([reply()])
        self.addCleanup(stub.close)
        client = OpenRouterClient(key='', models=('first/model:free',), base=stub.base)
        available, reason = client.available()
        self.assertFalse(available)
        self.assertIn('key', reason)
        with self.assertRaises(ProviderUnavailable):
            client.complete('s', 'u', SCHEMA)
        self.assertEqual(stub.requests, [])


class RouterTests(unittest.TestCase):
    def test_the_model_plans_a_turn_by_default_and_the_policy_is_recorded(self):
        planned = json.dumps({'language': 'en',
                              'places': [{'name': 'Ahmedabad', 'state': 'Gujarat', 'district': '', 'kind': 'settlement'}],
                              'assumptions': [], 'clarification': '', 'explicit_times': False,
                              'tasks': [{'request_quote': 'Will it rain in Ahmedabad, Gujarat tomorrow morning?',
                                         'kind': 'forecast', 'operation': 'lookup', 'parameters': ['precipitation'],
                                         'years': [], 'period': 'annual', 'start_local': '2026-09-16T06:30:00+05:30',
                                         'end_local': '2026-09-16T12:30:00+05:30', 'place_indices': [0]}],
                              'context_action': 'new', 'changed_fields': []})
        stub = Stub([reply(planned)])
        self.addCleanup(stub.close)
        router = ModelRouter(clients=[OpenRouterClient(key='k', models=('first/model:free',), base=stub.base)],
                             policy='model', router=False)
        plan, meta = router.plan('Will it rain in Ahmedabad, Gujarat tomorrow morning?', NOW, [])
        self.assertEqual(meta['provider'], 'openrouter')
        self.assertEqual(meta['planner_policy'], 'model')
        self.assertTrue(stub.requests, 'the model plans the turn, so the provider is called')
        self.assertEqual(plan['intent'], 'forecast')
        self.assertEqual([task['kind'] for task in plan['tasks']], ['forecast'])

    def test_the_rules_plan_only_when_the_policy_asks_for_them(self):
        stub = Stub([reply()])
        self.addCleanup(stub.close)
        router = ModelRouter(clients=[OpenRouterClient(key='k', models=('first/model:free',), base=stub.base)],
                             policy='rules')
        plan, meta = router.plan('Will it rain in Ahmedabad, Gujarat tomorrow morning?', NOW, [])
        self.assertEqual(meta['provider'], 'deterministic_rules')
        self.assertEqual(meta['planner_policy'], 'rules')
        self.assertEqual(stub.requests, [], 'the rules policy must not call a provider')
        self.assertEqual(plan['intent'], 'forecast')
        self.assertEqual([task['kind'] for task in plan['tasks']], ['forecast'])
        self.assertEqual(plan['places'][0]['name'], 'Ahmedabad')

    def test_a_provider_outage_is_answered_from_the_rules_floor_and_says_so(self):
        """The floor catches the fall, and the turn declares which planner read the question.

        This asserted the opposite until 20 September: a provider outage refused outright, on the
        principle that the rules planner must not be a SILENT substitute for the model planner. That
        principle is right and the refusal was the wrong way to keep it - the objection is to the silence,
        not to the substitute. Measured against a corpus of fifty-one real questions, the largest single
        cause of an avoidable refusal was a cloud provider blinking during "will it rain in Ahmedabad
        tomorrow", the most ordinary shape this product has.

        So the floor answers, and `planner_policy` says it did. The companion test below keeps the other
        half: a question the rules cannot read still refuses, and names both failures.
        """
        stub = Stub([])
        self.addCleanup(stub.close)
        router = ModelRouter(clients=[OpenRouterClient(key='k', models=('first/model:free',), base=stub.base)],
                             policy='model', router=False)
        plan, meta = router.plan('Will it rain in Ahmedabad, Gujarat tomorrow morning?', NOW, [])

        self.assertEqual(plan['intent'], 'forecast')
        self.assertEqual(plan['places'][0]['name'], 'Ahmedabad')
        # Substituted, and never silently: the turn carries which planner read it and why.
        self.assertEqual(meta['planner_policy'], 'rules_fallback')
        self.assertEqual(meta['provider'], 'deterministic_rules')
        self.assertIn('unavailable', meta['fallback_reason'])
        self.assertTrue(meta['failover'], 'the provider failure that caused the fallback is recorded')


    def test_a_follow_up_falls_through_to_a_provider(self):
        stub = Stub([reply('{"language": "en", "places": [], "assumptions": [], "clarification": "", '
                           '"explicit_times": false, "tasks": [{"request_quote": "evening", "kind": "forecast", '
                           '"operation": "lookup", "parameters": ["precipitation"], "years": [], "period": "annual", '
                           '"start_local": "", "end_local": "", "place_indices": []}], '
                           '"context_action": "follow_up", "changed_fields": ["time"]}')])
        self.addCleanup(stub.close)
        router = ModelRouter(clients=[OpenRouterClient(key='k', models=('first/model:free',), base=stub.base)],
                             policy='model', router=False)
        plan, meta = router.plan('And what about the evening?', NOW, [])
        self.assertEqual(meta['provider'], 'openrouter')
        self.assertEqual(meta['planner_policy'], 'model')
        self.assertEqual(len(stub.requests), 1)
        self.assertEqual(plan['context_action'], 'follow_up')

    def test_every_provider_failing_is_named_when_rules_cannot_help(self):
        stub = Stub([(500, {'error': {'message': 'boom'}})] * 4)
        self.addCleanup(stub.close)
        router = ModelRouter(clients=[OpenRouterClient(key='k', models=('first/model:free',), base=stub.base)],
                             policy='model')
        with patch.object(providers, 'RETRY_BACKOFF_SECONDS', 0.01):
            with self.assertRaises(Exception) as raised:
                router.plan('And what about the evening?', NOW, [])
        self.assertIn('openrouter', str(raised.exception))

    def test_describe_reports_availability_without_exposing_the_key(self):
        router = ModelRouter(clients=[OpenRouterClient(key='', models=('a/b:free',)), OllamaClient()])
        rows = router.describe()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['provider'], 'openrouter')
        self.assertFalse(rows[0]['available'])
        self.assertIn('key', rows[0]['reason'])
        self.assertNotIn('key', json.dumps(rows[1]))


class DeepSeekTests(unittest.TestCase):
    """The paid endpoint: JSON-object mode, the schema in the prompt, and its refusals named."""

    def test_the_client_sends_json_object_mode_and_the_schema_in_the_prompt(self):
        stub = Stub([reply('{"ok": true}')])
        self.addCleanup(stub.close)
        client = DeepSeekClient(key='k', base=stub.base)
        data, meta = client.complete('System text.', 'User text.', SCHEMA, max_tokens=50)
        self.assertEqual(data, {'ok': True})
        self.assertEqual(meta['provider'], 'deepseek')
        self.assertEqual(meta['model'], 'deepseek-chat')
        request = stub.requests[0]
        self.assertEqual(request['path'], '/chat/completions')
        self.assertEqual(request['headers'].get('Authorization'), 'Bearer k')
        self.assertEqual(request['body']['response_format'], {'type': 'json_object'})
        self.assertIn('validates against this JSON schema', request['body']['messages'][0]['content'])
        self.assertIn('"ok"', request['body']['messages'][0]['content'])
        self.assertEqual(request['body']['messages'][1]['content'], 'User text.')

    def test_usage_is_recorded_so_a_paid_turn_can_be_accounted_for(self):
        stub = Stub([reply('{"ok": true}', usage={'prompt_tokens': 120, 'completion_tokens': 8,
                                                  'total_tokens': 128, 'prompt_cache_hit_tokens': 40})])
        self.addCleanup(stub.close)
        _data, meta = DeepSeekClient(key='k', base=stub.base).complete('s', 'u', SCHEMA)
        self.assertEqual(meta['input_tokens'], 120)
        self.assertEqual(meta['output_tokens'], 8)
        self.assertEqual(meta['cache_hit_tokens'], 40)

    def test_a_refused_key_disables_the_client_and_a_missing_balance_is_named(self):
        stub = Stub([(401, {'error': {'message': 'invalid key'}})])
        self.addCleanup(stub.close)
        client = DeepSeekClient(key='k', base=stub.base)
        with self.assertRaises(ProviderUnavailable) as raised:
            client.complete('s', 'u', SCHEMA)
        self.assertIn('refused', str(raised.exception))
        available, reason = client.available()
        self.assertFalse(available, 'a refused key is not retried for this process')
        self.assertIn('HTTP 401', reason)
        stub2 = Stub([(402, {'error': {'message': 'Insufficient Balance'}})])
        self.addCleanup(stub2.close)
        with self.assertRaises(ProviderUnavailable) as raised:
            DeepSeekClient(key='k', base=stub2.base).complete('s', 'u', SCHEMA)
        self.assertIn('balance', str(raised.exception))

    def test_a_rate_limit_is_retried_once_and_then_answered(self):
        stub = Stub([(429, {'error': {'message': 'rate limited'}}), reply('{"ok": true}')])
        self.addCleanup(stub.close)
        with patch.object(providers, 'RETRY_BACKOFF_SECONDS', 0.01):
            data, meta = DeepSeekClient(key='k', base=stub.base).complete('s', 'u', SCHEMA)
        self.assertEqual(data, {'ok': True})
        self.assertEqual(meta['attempts'], 2)

    def test_no_key_means_no_request(self):
        stub = Stub([reply()])
        self.addCleanup(stub.close)
        client = DeepSeekClient(key='', base=stub.base)
        available, reason = client.available()
        self.assertFalse(available)
        self.assertIn('key', reason)
        with self.assertRaises(ProviderUnavailable):
            client.complete('s', 'u', SCHEMA)
        self.assertEqual(stub.requests, [])


class OllamaTests(unittest.TestCase):
    def test_the_local_adapter_reads_its_own_reply_shape(self):
        stub = Stub([(200, {'message': {'content': '{"ok": true}'}, 'done_reason': 'stop',
                            'prompt_eval_count': 5, 'eval_count': 3})])
        self.addCleanup(stub.close)
        data, meta = OllamaClient(model='local:latest', base=stub.base, timeout=5).complete('s', 'u', SCHEMA)
        self.assertEqual(data, {'ok': True})
        self.assertEqual(meta['provider'], 'ollama')
        self.assertEqual(meta['model'], 'local:latest')
        self.assertEqual(meta['input_tokens'], 5)
        self.assertEqual(stub.requests[0]['path'], '/api/chat')
        self.assertEqual(stub.requests[0]['body']['format'], SCHEMA)
        self.assertEqual(stub.requests[0]['body']['options']['temperature'], 0)

    def test_a_truncated_local_reply_is_refused_rather_than_parsed(self):
        stub = Stub([(200, {'message': {'content': '{"ok":'}, 'done_reason': 'length'})])
        self.addCleanup(stub.close)
        with self.assertRaises(ProviderUnavailable):
            OllamaClient(model='local:latest', base=stub.base, timeout=5).complete('s', 'u', SCHEMA)


class RulePlannerTests(unittest.TestCase):
    def request_for(self, question):
        return rule_request(question, NOW)

    def test_the_problem_statement_shapes_are_recognised(self):
        expected = {
            'Will it rain in Ahmedabad, Gujarat tomorrow morning?': ('forecast', 'precipitation'),
            'What is the temperature in Imphal tomorrow?': ('forecast', 'temperature_2m'),
            'What is the chance of rain in Surat tomorrow evening?': ('forecast', 'precipitation_probability'),
            'Is there an official warning for Patna, Bihar tomorrow?': ('warning', 'official_warning'),
            'What was the rainfall in Ahmedabad in 1990?': ('history', 'rainfall'),
            'What are the wave conditions near Veraval, Gujarat tomorrow?': ('marine', 'wave_height'),
            'What is the river discharge near Patna, Bihar tomorrow?': ('river', 'river_discharge'),
            'What is the latest METAR for VOBL?': ('aviation', 'metar'),
            'What does the whole Gujarat state agromet advisory bulletin say overall?': ('document', 'published_document'),
        }
        for question, (kind, parameter) in expected.items():
            with self.subTest(question=question):
                request = self.request_for(question)
                self.assertIsNotNone(request, 'a core shape must plan without a model')
                self.assertEqual(request['tasks'][0]['kind'], kind)
                self.assertIn(parameter, request['tasks'][0]['parameters'])

    def test_a_time_window_is_local_to_ist_and_ordered(self):
        request = self.request_for('Will it rain in Ahmedabad tomorrow morning?')
        task = request['tasks'][0]
        self.assertTrue(task['start_local'].startswith('2026-09-16T09:30:00+05:30'))
        self.assertTrue(task['end_local'].startswith('2026-09-16T12:30:00+05:30'))
        self.assertFalse(request['explicit_times'])

    def test_a_devanagari_question_is_planned_because_rules_can_read_it(self):
        # Changed on 15 September 2026: the rules used to return None for any Indic-script
        # question, which left a perfectly readable question to a model. Understanding the
        # question's language is not a claim to be able to answer in it - the answer-language
        # gate decides that from the user's own selection.
        request = self.request_for('कल अहमदाबाद, गुजरात में सुबह बारिश होगी?')
        self.assertIsNotNone(request)
        self.assertEqual(request['language'], 'hi')
        self.assertEqual([place['name'] for place in request['places']], ['अहमदाबाद'])
        self.assertEqual(request['tasks'][0]['parameters'], ['precipitation'])

    def test_a_gujarati_question_is_planned_and_keeps_its_own_script(self):
        request = self.request_for('અમદાવાદમાં આવતીકાલે વરસાદ થશે?')
        self.assertIsNotNone(request)
        self.assertEqual(request['language'], 'gu')
        self.assertEqual([place['name'] for place in request['places']], ['અમદાવાદ'])
        self.assertEqual(request['tasks'][0]['parameters'], ['precipitation'])

    def test_a_question_rules_still_cannot_read_is_left_to_a_model(self):
        for question in ('And what about the evening?', 'Why are the leaves yellow?', ''):
            with self.subTest(question=question):
                self.assertIsNone(rule_request(question, NOW), 'rules must not guess: ' + question)

    def test_a_general_weather_question_plans_the_four_parameters_and_asks_for_a_place(self):
        # Measured 15 September 2026: "कल सुबह वडोदरा, गुजरात में मौसम कैसा रहेगा?" took 12.6 s
        # through a model and came back with a different morning window than the same question in
        # Gujarati. A general weather question is read here as the planner prompt already reads it
        # - four parameters - and the missing place is asked for rather than invented.
        request = rule_request('What is the weather like?', NOW)
        self.assertEqual(request['tasks'][0]['parameters'],
                         ['precipitation', 'temperature_2m', 'wind_speed_10m', 'relative_humidity_2m'])
        self.assertEqual(request['places'], [])

    def test_both_historical_measures_are_retained(self):
        for question in ["What was India's rainfall and mean temperature in 2024?",
                         'Show the temperature and rainfall for India in 2024.']:
            request = rule_request(question, NOW)
            self.assertEqual([set(t['parameters']) for t in request['tasks']], [{'rainfall', 'temperature'}])
            self.assertTrue(all(t['kind'] == 'history' and t['years'] == [2024] for t in request['tasks']))

    def test_a_past_day_level_date_becomes_a_daily_history_task(self):
        expected = {
            'Daily mean temperature in Ahmedabad from 1 through 3 July 2025.': 'temperature_2m_mean',
            'Relative humidity in Ahmedabad on 2024-07-01.': 'relative_humidity_2m_mean',
            'Soil moisture in Ahmedabad from 1 to 3 July 2025.': 'soil_moisture_0_to_7cm_mean',
            'Rainfall in Ahmedabad on 1 July 2024.': 'precipitation_sum',
        }
        for question, parameter in expected.items():
            with self.subTest(question=question):
                request = self.request_for(question)
                self.assertIsNotNone(request, 'a past day-level date must plan without a model')
                task = request['tasks'][0]
                self.assertEqual(task['kind'], 'history')
                self.assertEqual(task['operation'], 'daily')
                self.assertIn(parameter, task['parameters'])
        request = self.request_for('Rainfall in Ahmedabad from 1 through 3 July 2024.')
        self.assertEqual(request['tasks'][0]['start_local'], '2024-07-01T00:00:00+05:30')
        self.assertEqual(request['tasks'][0]['end_local'], '2024-07-04T00:00:00+05:30')

    def test_a_future_or_unresolvable_day_level_date_is_left_to_a_model(self):
        for question in ('Rainfall in Ahmedabad on 1 December 2026.',
                         'Rainfall in Ahmedabad July 1 to 3, 2024.'):
            with self.subTest(question=question):
                self.assertIsNone(rule_request(question, NOW),
                                  'a future or unshortened range is not a daily history task')

    def test_an_ensemble_spread_question_is_an_ensemble_task(self):
        for question in ('What is the ensemble spread for Ahmedabad tomorrow morning?',
                         'What is the spread of rainfall in Ahmedabad tomorrow?'):
            with self.subTest(question=question):
                task = self.request_for(question)['tasks'][0]
                self.assertEqual(task['kind'], 'ensemble')
                self.assertEqual(task['operation'], 'lookup')
                self.assertTrue(task['start_local'])
        self.assertIn('precipitation',
                      self.request_for('What is the spread of rainfall in Ahmedabad tomorrow?')['tasks'][0]['parameters'])

    def test_a_plain_forecast_is_not_an_ensemble_task(self):
        self.assertEqual(self.request_for('Will it rain in Ahmedabad tomorrow morning?')['tasks'][0]['kind'], 'forecast')

    def test_an_air_quality_question_is_an_air_quality_task(self):
        task = self.request_for('What is the air quality in Ahmedabad tomorrow?')['tasks'][0]
        self.assertEqual(task['kind'], 'air_quality')
        self.assertEqual(task['operation'], 'lookup')
        self.assertTrue(task['start_local'])
        for question, parameter in (('What is the PM2.5 in Delhi tomorrow?', 'pm2_5'),
                                    ('Show the US AQI for Mumbai tomorrow.', 'us_aqi'),
                                    ('Ozone in Ahmedabad tomorrow?', 'ozone')):
            with self.subTest(question=question):
                task = self.request_for(question)['tasks'][0]
                self.assertEqual(task['kind'], 'air_quality')
                self.assertIn(parameter, task['parameters'])

    def test_a_plain_forecast_is_not_air_quality(self):
        self.assertEqual(self.request_for('Will it rain in Ahmedabad tomorrow morning?')['tasks'][0]['kind'], 'forecast')

    def test_a_spread_word_without_a_measure_is_left_to_a_model(self):
        self.assertIsNone(rule_request('What is the spread here?', NOW))

    def test_a_month_with_only_a_year_stays_a_table_lookup(self):
        request = self.request_for('What was the rainfall in Ahmedabad in July 1990?')
        self.assertEqual(request['tasks'][0]['kind'], 'history')
        self.assertEqual(request['tasks'][0]['parameters'], ['rainfall'])

    def test_out_of_scope_questions_route_to_the_gap_answer_not_to_a_number(self):
        request = self.request_for('What is the groundwater level in Ahmedabad?')
        self.assertEqual(request['tasks'][0]['kind'], 'research')

    def test_a_named_district_is_read_without_a_preposition(self):
        request = self.request_for('What does the Ahmedabad district agromet bulletin say about cotton?')
        self.assertEqual([place['name'] for place in request['places']], ['Ahmedabad'])
        self.assertEqual(request['places'][0]['kind'], 'district')

    def test_a_crop_with_a_bulletin_is_an_advisory_task_not_a_generic_document(self):
        request = self.request_for('What does the Ahmedabad district agromet bulletin say about cotton?')
        task = request['tasks'][0]
        self.assertEqual(task['kind'], 'agriculture')
        self.assertEqual(task['parameters'], ['agricultural_advisory'])
        self.assertEqual(task['document_request']['crop'], 'cotton')
        self.assertEqual(task['document_request']['mode'], 'source_lookup')
        self.assertEqual(task['document_request']['topic'], 'general')

    def test_a_decision_question_asks_for_decision_support(self):
        request = self.request_for('Should I irrigate my cotton crop in Ahmedabad, Gujarat today?')
        task = request['tasks'][0]
        self.assertEqual(task['kind'], 'agriculture')
        self.assertEqual(task['document_request']['mode'], 'decision_support')
        self.assertEqual(task['document_request']['topic'], 'irrigation')

    def test_a_state_agromet_summary_keeps_state_scope_and_the_whole_edition_flag(self):
        request = self.request_for('What does the whole Gujarat state agromet advisory bulletin say overall?')
        task = request['tasks'][0]
        self.assertEqual(task['kind'], 'document')
        self.assertEqual(task['corpus_request']['family'], 'state_agromet')
        self.assertEqual(task['corpus_request']['scope'], 'state')
        self.assertTrue(task['corpus_request']['whole_document'])

    def test_a_district_bulletin_question_uses_district_scope(self):
        request = self.request_for('What does the Ahmedabad district agromet bulletin say?')
        task = request['tasks'][0]
        self.assertEqual(task['kind'], 'document')
        self.assertEqual(task['corpus_request']['family'], 'district_agromet')
        self.assertEqual(task['corpus_request']['scope'], 'district')

    def test_a_hinglish_place_after_the_name_is_read_without_the_day_word(self):
        request = self.request_for('Kal Ahmedabad me barish hogi kya?')
        self.assertIsNotNone(request)
        self.assertEqual([place['name'] for place in request['places']], ['Ahmedabad'])
        self.assertEqual(request['language'], 'hi-Latn')
        self.assertEqual(request['tasks'][0]['kind'], 'forecast')
        second = self.request_for('Aaj Delhi me garmi kitni hogi?')
        self.assertEqual([place['name'] for place in second['places']], ['Delhi'])

    def test_a_crop_agromet_advisory_is_agriculture_not_a_warning(self):
        # Measured need, 15 September 2026: "What does the Ahmedabad district agromet advisory
        # say for cotton?" read the district warning product, because "advisory" is also a
        # warning word. A crop with published farm advice is the agriculture shape.
        for question in ('What does the Ahmedabad district agromet advisory say for cotton?',
                         'Ahmedabad district agromet advisory kya kehta hai cotton ke liye?'):
            request = self.request_for(question)
            self.assertIsNotNone(request, question)
            self.assertEqual([task['kind'] for task in request['tasks']], ['agriculture'], question)

    def test_a_warning_for_farmers_keeps_the_warning_route(self):
        request = self.request_for('Is there any warning for cotton farmers in Ahmedabad?')
        self.assertEqual([task['kind'] for task in request['tasks']], ['warning'])
        plain = self.request_for('Any advisory for Ahmedabad?')
        self.assertEqual([task['kind'] for task in plain['tasks']], ['warning'])
    def test_a_request_to_compare_models_is_the_crosscheck_operation(self):
        # Measured on 15 September 2026: only the model planner recognised this shape, so a
        # rules-first turn that needed no model could not produce the comparison.
        for question in ('Compare the models for rainfall in Ahmedabad tomorrow.',
                         'Do the models agree on rain in Kochi tomorrow?',
                         'Rain in Patna tomorrow morning: check another model.',
                         'GFS vs best-match rainfall for Ahmedabad tomorrow.',
                         'Compare the GFS and best-match forecast for rain in Vadodara, Gujarat tomorrow afternoon.',
                         'Compare best match and GFS rain for Cuttack tomorrow morning.'):
            request = self.request_for(question)
            self.assertIsNotNone(request, question)
            self.assertEqual([(task['kind'], task['operation']) for task in request['tasks']],
                             [('forecast', 'crosscheck')], question)

    def test_a_plain_rain_question_is_not_a_crosscheck(self):
        request = self.request_for('Will it rain in Ahmedabad tomorrow morning?')
        self.assertEqual([(task['kind'], task['operation']) for task in request['tasks']],
                         [('forecast', 'lookup')])

    def test_a_crosscheck_with_no_measure_named_is_left_to_a_model(self):
        # "another model" of what? Refusing to guess is the honest floor.
        self.assertIsNone(self.request_for('Check another model for Patna tomorrow morning.'))
    def test_a_compound_question_is_planned_clause_by_clause(self):
        request = self.request_for('Will it rain in Patna, Bihar tomorrow, and is there any warning?')
        self.assertIsNotNone(request)
        self.assertEqual([task['kind'] for task in request['tasks']], ['forecast', 'warning'])
        self.assertEqual([place['name'] for place in request['places']], ['Patna'])
        for task in request['tasks']:
            self.assertEqual(task['place_indices'], [0],
                             'a clause that names no place is about the place the question named')
            self.assertTrue(task['request_quote'] in 'Will it rain in Patna, Bihar tomorrow, and is there any warning?')

    def test_a_two_place_question_is_left_to_a_model_rather_than_silently_shortened(self):
        self.assertIsNone(rule_request('Will it rain in Surat and Vadodara tomorrow?', NOW))

    def test_a_relative_span_becomes_a_bounded_upcoming_window(self):
        request = self.request_for('What is the river discharge near Patna, Bihar in the next three days?')
        task = request['tasks'][0]
        self.assertEqual(task['kind'], 'river')
        self.assertTrue(task['start_local'].startswith('2026-09-15T00:30:00+05:30'))
        self.assertTrue(task['end_local'].startswith('2026-09-17T23:30:00+05:30'))
        self.assertFalse(request['explicit_times'])
        week = self.request_for('Show the wave conditions near Veraval for the next week?')
        self.assertTrue(week['tasks'][0]['end_local'].startswith('2026-09-21T23:30:00+05:30'))

    def test_a_context_referencing_follow_up_is_left_to_a_model(self):
        history = [{'role': 'assistant', 'content': 'Structured conversation focus',
                    'context_state': {'accepted_places': {'Kochi': {'label': 'Kochi, Kerala'}}}}]
        self.assertIsNone(rule_request('Compare the rain amount for that same morning period with GFS too.',
                                       NOW, history))

    def test_a_self_contained_question_in_a_conversation_is_still_planned_by_rules(self):
        history = [{'role': 'assistant', 'content': 'Structured conversation focus',
                    'context_state': {'accepted_places': {'Kochi': {'label': 'Kochi, Kerala'}}}}]
        request = rule_request('Will it rain in Surat, Gujarat tomorrow evening?', NOW, history)
        self.assertIsNotNone(request)
        self.assertEqual(request['tasks'][0]['kind'], 'forecast')


if __name__ == '__main__':
    unittest.main()
