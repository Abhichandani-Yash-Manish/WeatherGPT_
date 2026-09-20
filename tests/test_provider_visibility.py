"""Who answers: the provider policy, availability and the last failure, visible without a trace.

The reader could see which provider answered only inside a card's trace disclosure and the reason for a
refusal only in an error message. These checks pin the settings payload that the workspace serves and the
router state behind it: the policy in force, the planner policy, the first look, every provider with its
availability, and the last time they all failed.
"""
import json
import unittest
from unittest.mock import patch

import test_answers as fixture
from test_ingestion import Response, payload
from weathergpt_data import providers
from weathergpt_data.product_api import settings_view
from weathergpt_data.providers import DeepSeekClient, ModelRouter, OpenRouterClient, ProviderUnavailable
from weathergpt_data.workspace import Workspace


class SettingsProviderTests(unittest.TestCase):
    def test_the_settings_payload_states_the_policy_the_order_and_the_availability(self):
        provider = settings_view()['data']['provider']
        self.assertIn(provider['policy'], {'deepseek_first', 'deepseek', 'cloud_free', 'local'})
        self.assertIn(provider['planner_policy'], {'model', 'rules'})
        self.assertIn('chat_router', provider)
        self.assertTrue(provider['providers'], 'the order the workspace will try is listed')
        for row in provider['providers']:
            self.assertIn('provider', row)
            self.assertIn('available', row)
            self.assertIn('configured', row)
            self.assertIn(row['provider'], {'deepseek', 'openrouter', 'ollama'})
        self.assertTrue(provider['set_deepseek_key_command'].endswith('--set-key deepseek'))
        self.assertIn('never printed', provider['key_note'])

    def test_a_machine_with_no_keys_still_names_the_order_and_what_is_missing(self):
        """The settings panel is read when nothing is working, so it must speak then.

        Found by CI on 20 September 2026: this suite's settings test passed on a laptop that had
        keys and failed on a runner that had none, because describe() walked only the clients that
        were actually built. An empty list is the least useful thing to show a reader at the moment
        they are asking why the workspace will not answer.
        """
        with patch.dict('os.environ', {}, clear=True):
            with patch.object(providers, 'local_config', return_value={}):
                rows = settings_view()['data']['provider']['providers']

        self.assertEqual([row['provider'] for row in rows], ['deepseek', 'openrouter', 'ollama'],
                         'the order is named even when none of them can be reached')
        for row in rows:
            with self.subTest(provider=row['provider']):
                self.assertFalse(row['configured'])
                self.assertFalse(row['available'])
                # Not merely "unavailable": the row says what is missing, so it can be fixed.
                self.assertTrue(row['reason'], row['provider'] + ' says nothing about why')
        self.assertIn('DEEPSEEK_API_KEY', rows[0]['reason'])
        self.assertIn('OPENROUTER_API_KEY', rows[1]['reason'])

    def test_a_last_failure_is_reported_when_every_provider_refused(self):
        from test_providers import Stub
        stub = Stub([(429, {'error': {'message': 'free-models-per-day'}})] * 6)
        self.addCleanup(stub.close)
        router = ModelRouter(clients=[DeepSeekClient(key='k', base=stub.base)], policy='model', router=False)
        with patch.object(providers, 'RETRY_BACKOFF_SECONDS', 0.01):
            with self.assertRaises(ProviderUnavailable):
                router.complete('s', 'u', {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False})
        failure = router.state()['last_failure']
        self.assertEqual(failure['provider'], 'deepseek')
        self.assertIn('429', failure['reason'])
        self.assertTrue(failure['at_utc'])

    def test_the_planner_policy_and_the_first_look_are_read_from_the_environment(self):
        with patch.dict('os.environ', {'WEATHERGPT_PLANNER': 'rules', 'WEATHERGPT_ROUTER': 'off'}):
            state = ModelRouter(clients=[]).state()
        self.assertEqual(state['planner_policy'], 'rules')
        self.assertFalse(state['chat_router'])




class KeyCommandTests(unittest.TestCase):
    def test_set_key_writes_the_provider_field_without_printing_the_key(self):
        import importlib.util
        import sys
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('wg_models', root / 'scripts' / 'models.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules['wg_models'] = module
        spec.loader.exec_module(module)
        target = root / 'tmp' / 'models-key-test.json'
        if target.exists():
            target.unlink()
        answers = ['sk-' + 'a' * 32]
        code = module.set_key(reader=lambda prompt: answers.pop(0), path=target, provider='deepseek')
        self.assertEqual(code, 0)
        stored = json.loads(target.read_text())
        self.assertIn('deepseek_api_key', stored)
        self.assertNotIn('openrouter_api_key', stored)
        target.unlink()


if __name__ == '__main__':
    unittest.main()
