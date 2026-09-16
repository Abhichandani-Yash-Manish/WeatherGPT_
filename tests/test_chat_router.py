"""The cheap first look: a conversation is answered here, a task still goes to the full planner.

Measured 16 September 2026: a chat turn paid for the whole planner prompt and took 9-48 s on the free
provider. The router tier asks a short question first. These checks pin what it may do - answer only a
conversation, in one call, validate the plan it builds, and leave every task to the planner - and what it
may not: decide a value, cost a task turn a wrong plan, or fail a turn when it cannot answer.
"""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from test_providers import NOW, Stub, reply

from weathergpt_data import providers
from weathergpt_data.chat_router import chat_plan, route
from weathergpt_data.providers import ModelRouter, OpenRouterClient
from weathergpt_data.transport import SourceError

PLAN = json.dumps({'language': 'en',
                   'places': [{'name': 'Ahmedabad', 'state': 'Gujarat', 'district': '', 'kind': 'settlement'}],
                   'assumptions': [], 'clarification': '', 'explicit_times': False,
                   'tasks': [{'request_quote': 'Will it rain in Ahmedabad, Gujarat tomorrow morning?',
                              'kind': 'forecast', 'operation': 'lookup', 'parameters': ['precipitation'],
                              'years': [], 'period': 'annual', 'start_local': '2026-09-16T06:30:00+05:30',
                              'end_local': '2026-09-16T12:30:00+05:30', 'place_indices': [0]}],
                   'context_action': 'new', 'changed_fields': []})
QUESTION = 'Will it rain in Ahmedabad, Gujarat tomorrow morning?'


def router_with(stub):
    return ModelRouter(clients=[OpenRouterClient(key='k', models=('first/model:free',), base=stub.base)],
                       policy='model', router=True)


class ChatRouterTests(unittest.TestCase):
    def test_a_greeting_is_answered_in_one_call(self):
        stub = Stub([reply(json.dumps({'kind': 'greeting', 'reply': 'Hello! Ask me about a place and a day.'}))])
        self.addCleanup(stub.close)
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'cloud_free'}):
            plan, meta = router_with(stub).plan('hello', NOW, [])
        self.assertEqual(plan['intent'], 'chat')
        self.assertEqual(plan['tasks'][0]['kind'], 'chat')
        self.assertEqual(plan['tasks'][0]['operation'], 'reply')
        self.assertEqual(plan['tasks'][0]['reply'], 'Hello! Ask me about a place and a day.')
        self.assertEqual(meta['planner_tier'], 'router')
        self.assertEqual(meta['chat_kind'], 'greeting')
        self.assertEqual(meta['provider_policy'], 'cloud_free')
        self.assertEqual(len(stub.requests), 1, 'a conversation costs one call, not the full planner')

    def test_a_task_is_left_to_the_full_planner(self):
        stub = Stub([reply(json.dumps({'kind': 'task', 'reply': ''})), reply(PLAN)])
        self.addCleanup(stub.close)
        plan, meta = router_with(stub).plan(QUESTION, NOW, [])
        self.assertEqual(len(stub.requests), 2, 'the router asks first, and the planner still owns a task')
        self.assertIsNone(meta.get('planner_tier'))
        self.assertEqual(meta['provider'], 'openrouter')
        self.assertEqual(plan['intent'], 'forecast')

    def test_a_route_the_model_cannot_decide_is_a_task(self):
        for data in [{'kind': 'nonsense', 'reply': 'x'}, {'kind': 'greeting', 'reply': '  '}, {'reply': 'x'}]:
            stub = Stub([reply(json.dumps(data)), reply(PLAN)])
            self.addCleanup(stub.close)
            with self.subTest(data=data):
                plan, _meta = router_with(stub).plan(QUESTION, NOW, [])
                self.assertEqual(plan['intent'], 'forecast', 'an undecided route falls through to the planner')

    def test_a_router_failure_changes_nothing(self):
        stub = Stub([reply(PLAN)])
        self.addCleanup(stub.close)
        router = router_with(stub)
        with patch('weathergpt_data.chat_router.route', side_effect=SourceError('the first look failed')):
            plan, meta = router.plan(QUESTION, NOW, [])
        self.assertEqual(plan['intent'], 'forecast')
        self.assertEqual(meta['provider'], 'openrouter')

    def test_a_slow_first_look_falls_through_to_the_planner(self):
        stub = Stub([reply(PLAN)])
        self.addCleanup(stub.close)
        router = router_with(stub)
        with patch('weathergpt_data.chat_router.route', side_effect=TimeoutError('the first look timed out')):
            plan, meta = router.plan(QUESTION, NOW, [])
        self.assertEqual(plan['intent'], 'forecast')
        self.assertEqual(meta['provider'], 'openrouter')

    def test_a_router_reply_is_still_validated_as_a_plan(self):
        with self.assertRaises(SourceError):
            chat_plan('hello', 'greeting', '')
        plan = chat_plan('hello', 'greeting', 'Hello!')
        self.assertEqual(plan['intent'], 'chat')
        self.assertEqual(plan['tasks'][0]['reply'], 'Hello!')

    def test_route_returns_none_for_a_task_without_building_a_plan(self):
        class Model:
            def complete(self, *args, **kwargs):
                return {'kind': 'task', 'reply': ''}, {'provider': 'stub'}
        self.assertIsNone(route(Model(), QUESTION, NOW, []))


class ProviderPolicyTests(unittest.TestCase):
    def test_the_free_cloud_models_are_the_only_providers_by_default(self):
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'cloud_free'}), \
             patch.object(providers, 'openrouter_key', return_value='key'):
            self.assertEqual([client.name for client in providers.default_clients()], ['openrouter'])
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'cloud_free'}), \
             patch.object(providers, 'openrouter_key', return_value=''):
            self.assertEqual(providers.default_clients(), [],
                             'with no key there is no provider, and the planner reports that rather than routing around it')

    def test_the_local_provider_runs_only_when_the_policy_asks_for_it(self):
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'local'}):
            self.assertEqual([client.name for client in providers.default_clients()], ['ollama'])
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'something-else'}), \
             patch.object(providers, 'deepseek_key', return_value=''):
            self.assertEqual(providers.provider_policy(), 'cloud_free',
                             'an unknown policy with no paid key falls back to the free cloud models')
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'something-else'}), \
             patch.object(providers, 'deepseek_key', return_value='k'):
            self.assertEqual(providers.provider_policy(), 'deepseek_first',
                             'an unknown policy with a configured paid key falls back to the configured provider')

    def test_the_configured_order_puts_the_paid_endpoint_first_and_the_free_models_after_it(self):
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'deepseek_first'}), \
             patch.object(providers, 'deepseek_key', return_value='k'), \
             patch.object(providers, 'openrouter_key', return_value='k2'):
            self.assertEqual([client.name for client in providers.default_clients()], ['deepseek', 'openrouter'])
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'deepseek_first'}), \
             patch.object(providers, 'deepseek_key', return_value=''), \
             patch.object(providers, 'openrouter_key', return_value='k2'):
            self.assertEqual([client.name for client in providers.default_clients()], ['openrouter'],
                             'the free ids still carry the turn when no paid key is configured')
        with patch.dict('os.environ', {'WEATHERGPT_PROVIDERS': 'deepseek'}), \
             patch.object(providers, 'deepseek_key', return_value=''), \
             patch.object(providers, 'openrouter_key', return_value='k2'):
            self.assertEqual(providers.default_clients(), [],
                             'the deepseek-only policy with no key has no provider, and never falls back on its own')


if __name__ == '__main__':
    unittest.main()
