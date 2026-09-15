"""OpenRouter free-model ranking, the free-only guard and the local key path.

Component checks over a temporary registry copy, a scripted catalogue fetch and a fake prompt.
They take no measurement of any provider or model: what they pin is that the shipped ranking is
ordered data whose ids are all free, that a paid id is refused by name instead of routed, that a
missing registry degrades to the ids this workspace has itself observed, and that entering a key
stores it at mode 0600 without printing it. Neither the suite nor the ranked order claims to have
measured availability: the registry's own availability block says so until --probe-free runs.
"""
import contextlib
import importlib.util
import io
import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from weathergpt_data import providers
from weathergpt_data.providers import ModelRouter, OpenRouterClient, ProviderUnavailable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'data' / 'registry' / 'openrouter-free-models.json'
TIER_ORDER = ('frontier', 'strong', 'capable', 'modest', 'reasoning_first')

SPEC = importlib.util.spec_from_file_location('models_script', ROOT / 'scripts/models.py')
models_script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(models_script)

PAID = 'openai/gpt-4o'
KEY = 'sk-or-v1-' + 'f' * 28


def registry_copy(directory, availability=None):
    """A disposable copy of the shipped ranking; a probe test never writes the tracked file."""
    data = json.loads(REGISTRY.read_text(encoding='utf-8'))
    if availability is not None:
        data['availability'] = availability
    path = Path(directory) / 'openrouter-free-models.json'
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return path


class RankingTests(unittest.TestCase):
    def test_the_registry_carries_a_schema_a_note_and_an_ordered_free_ranking(self):
        data = json.loads(REGISTRY.read_text(encoding='utf-8'))
        self.assertEqual(data['schema_version'], 'openrouter-free-models-v1')
        self.assertTrue(data['note'].strip())
        self.assertTrue(data['ranking_basis'].strip())
        entries = data['models']
        self.assertGreaterEqual(len(entries), len(providers.DEFAULT_FREE_MODELS))
        ids = [entry['model_id'] for entry in entries]
        self.assertEqual(len(ids), len(set(ids)), 'a model must appear once in the order')
        for entry in entries:
            self.assertTrue(entry['model_id'].endswith(':free'), entry['model_id'])
            self.assertTrue(entry['why'].strip(), entry['model_id'] + ' must state its reason')
            self.assertTrue(entry['checked_at_utc'].strip(), entry['model_id'] + ' must be dated')
        tiers = [TIER_ORDER.index(entry['tier']) for entry in entries]
        self.assertEqual(tiers, sorted(tiers), 'the registry files the most capable class first')

    def test_the_reason_marks_a_judgement_rather_than_a_benchmark(self):
        data = json.loads(REGISTRY.read_text(encoding='utf-8'))
        for entry in data['models']:
            self.assertTrue('judgement' in entry['why'].lower() or 'expectation' in entry['why'].lower(),
                            entry['model_id'] + ' must not read as a measured score')

    def test_the_routing_order_is_the_registry_order_and_is_stable(self):
        ids = tuple(entry['model_id'] for entry in json.loads(REGISTRY.read_text(encoding='utf-8'))['models'])
        with patch.dict('os.environ', {}, clear=True), patch.object(providers, 'local_config', return_value={}):
            first = providers.free_models()
            self.assertEqual(first, providers.free_models(), 'the routing order must not move between calls')
        self.assertEqual(first, ids)
        self.assertEqual(providers.free_model_ranking(), ids)
        self.assertTrue(all(model.endswith(':free') for model in first))

    def test_a_configured_paid_id_is_refused_with_a_reason_and_never_enters_the_order(self):
        with patch.dict('os.environ', {'WEATHERGPT_MODELS': 'extra/model:free, ' + PAID}, clear=True):
            choices = providers.free_model_choices()
            routing = providers.free_models()
        self.assertNotIn(PAID, routing)
        self.assertIn('extra/model:free', routing)
        self.assertEqual(routing[len(providers.free_model_ranking()):], ('extra/model:free',))
        self.assertEqual([row['model_id'] for row in choices['refused']], [PAID])
        self.assertIn(':free', choices['refused'][0]['reason'])
        self.assertEqual(choices['routing_order'], routing)


class FallbackTests(unittest.TestCase):
    def test_a_missing_registry_falls_back_to_the_ids_this_workspace_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'absent.json'
            with patch.object(providers, 'FREE_MODEL_REGISTRY', missing):
                self.assertEqual(providers.free_model_ranking(), providers.DEFAULT_FREE_MODELS)
                with patch.dict('os.environ', {}, clear=True), patch.object(providers, 'local_config', return_value={}):
                    self.assertEqual(providers.free_models(), providers.DEFAULT_FREE_MODELS)
        self.assertTrue(all(model.endswith(':free') for model in providers.DEFAULT_FREE_MODELS))

    def test_an_unparsable_registry_is_fallen_back_from_rather_than_shrunk(self):
        with tempfile.TemporaryDirectory() as directory:
            broken = Path(directory) / 'broken.json'
            broken.write_text('{not json', encoding='utf-8')
            with patch.object(providers, 'FREE_MODEL_REGISTRY', broken):
                self.assertEqual(providers.free_model_ranking(), providers.DEFAULT_FREE_MODELS)


class PaidModelGuardTests(unittest.TestCase):
    """A paid id must cost nothing: no request is made and no route holds it."""

    @staticmethod
    def refuse(*args, **kwargs):
        raise AssertionError('a paid model id must never reach the network')

    def test_the_client_refuses_a_paid_model_without_a_request(self):
        client = OpenRouterClient(key=KEY, models=(PAID,), opener=self.refuse)
        self.assertEqual(client.models, ())
        self.assertEqual([row['model_id'] for row in client.refused_models], [PAID])
        available, reason = client.available()
        self.assertFalse(available)
        self.assertIn(':free', reason)
        with self.assertRaises(ProviderUnavailable):
            client.complete('system', 'user', {'type': 'object'})

    def test_the_client_keeps_free_ids_and_names_the_paid_one_a_caller_passed(self):
        client = OpenRouterClient(key=KEY, models=(PAID, 'a/b:free'), opener=self.refuse)
        self.assertEqual(client.models, ('a/b:free',))
        self.assertEqual([row['model_id'] for row in client.refused_models], [PAID])

    def test_the_router_refuses_an_openrouter_client_holding_a_paid_model(self):
        class Duck:
            name = 'openrouter'
            models = (PAID,)

        with self.assertRaises(ValueError) as raised:
            ModelRouter(clients=[Duck()])
        self.assertIn(PAID, str(raised.exception))
        self.assertEqual(ModelRouter(clients=[OpenRouterClient(key=KEY, models=('a/b:free',))]).clients[0].models,
                         ('a/b:free',))


class SetKeyTests(unittest.TestCase):
    def test_the_key_is_stored_at_0600_and_never_printed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nested' / 'model-config.json'
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = models_script.set_key(reader=lambda prompt: KEY, path=path)
            printed = out.getvalue() + err.getvalue()
            self.assertEqual(code, 0)
            self.assertTrue(path.parent.is_dir(), 'the configuration directory is created')
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertTrue(path.read_text(encoding='utf-8').rstrip().endswith('}'))
            self.assertNotIn(KEY, printed)
            self.assertIn('0600', printed)
        self.assertNotIn(KEY, json.dumps(models_script.set_key.__doc__ or ''))

    def test_the_existing_file_mode_is_tightened_even_when_the_file_existed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model-config.json'
            path.write_text(json.dumps({'models': ['a/b:free']}), encoding='utf-8')
            path.chmod(0o644)
            with contextlib.redirect_stdout(io.StringIO()):
                code = models_script.set_key(reader=lambda prompt: KEY, path=path)
            self.assertEqual(code, 0)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),
                             {'models': ['a/b:free'], 'openrouter_api_key': KEY})

    def test_a_short_or_empty_entry_is_refused_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model-config.json'
            for typed in ('', '   ', 'sk-short'):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = models_script.set_key(reader=lambda prompt, typed=typed: typed, path=path)
                self.assertEqual(code, 2)
                self.assertFalse(path.exists(), 'a refused entry must leave no file behind')
                self.assertIn('refused', out.getvalue())

    def test_an_unreadable_existing_configuration_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model-config.json'
            path.write_text('{broken', encoding='utf-8')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = models_script.set_key(reader=lambda prompt: KEY, path=path)
            self.assertEqual(code, 2)
            self.assertIn('refused', out.getvalue())
            self.assertEqual(path.read_text(encoding='utf-8'), '{broken')


class ProbeTests(unittest.TestCase):
    def test_no_key_reports_not_configured_and_invents_no_availability(self):
        with tempfile.TemporaryDirectory() as directory:
            path = registry_copy(directory)
            out = io.StringIO()
            with patch.dict('os.environ', {}, clear=True), patch.object(providers, 'local_config', return_value={}):
                with contextlib.redirect_stdout(out):
                    code = models_script.probe_free(path=path, fetch=self.fail_if_called)
            recorded = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(code, 0, 'no key is a state, not a crash')
            self.assertEqual(recorded['availability']['status'], 'not_configured')
            self.assertIn('not configured', out.getvalue())
            self.assertEqual(recorded['availability']['ranked_ids_found'], [])
            self.assertEqual(recorded['availability']['ranked_ids_missing'], [])
            self.assertEqual(recorded['availability']['unranked_free_ids_published'], [])
            self.assertNotEqual(recorded['availability']['status'], 'measured')
            self.assertEqual(recorded['models'], json.loads(REGISTRY.read_text())['models'],
                             'an unconfigured run must not touch the curated order')

    def test_a_no_key_probe_keeps_the_earlier_measurement_as_history(self):
        measured = {'status': 'measured', 'checked_at_utc': '2026-09-14T00:00:00+00:00', 'key_source': 'x',
                    'ranked_ids_found': ['deepseek/deepseek-chat-v3.1:free'], 'ranked_ids_missing': [],
                    'unranked_free_ids_published': [], 'reason': ''}
        with tempfile.TemporaryDirectory() as directory:
            path = registry_copy(directory, availability=measured)
            with patch.dict('os.environ', {}, clear=True), patch.object(providers, 'local_config', return_value={}):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = models_script.probe_free(path=path, fetch=self.fail_if_called)
            recorded = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(code, 0)
            self.assertEqual(recorded['availability']['status'], 'not_configured')
            self.assertEqual(recorded['availability_history'][0]['status'], 'measured')

    def test_a_probe_records_what_the_catalogue_published_and_keeps_the_ranking(self):
        ranked = [entry['model_id'] for entry in json.loads(REGISTRY.read_text(encoding='utf-8'))['models']]
        published = [ranked[0], 'new/free-model:free', PAID]
        with tempfile.TemporaryDirectory() as directory:
            path = registry_copy(directory)
            with patch.dict('os.environ', {'OPENROUTER_API_KEY': KEY}, clear=True):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = models_script.probe_free(path=path, fetch=lambda: published)
            recorded = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(code, 0)
            self.assertEqual(recorded['availability']['status'], 'measured')
            self.assertEqual(recorded['availability']['ranked_ids_found'], [ranked[0]])
            self.assertEqual(recorded['availability']['ranked_ids_missing'], ranked[1:])
            self.assertEqual(recorded['availability']['unranked_free_ids_published'], ['new/free-model:free'])
            self.assertEqual([entry['model_id'] for entry in recorded['models']], ranked)
            self.assertNotIn(KEY, path.read_text(encoding='utf-8'), 'the key never lands in a registry')

    def test_a_failed_probe_is_recorded_and_reports_a_failure(self):
        def broken():
            raise OSError('catalogue unreachable')

        with tempfile.TemporaryDirectory() as directory:
            path = registry_copy(directory)
            with patch.dict('os.environ', {'OPENROUTER_API_KEY': KEY}, clear=True):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = models_script.probe_free(path=path, fetch=broken)
            recorded = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(code, 1)
            self.assertEqual(recorded['availability']['status'], 'probe_failed')
            self.assertIn('OSError', recorded['availability']['reason'])
            self.assertEqual(recorded['availability']['ranked_ids_found'], [])
            self.assertNotIn(KEY, path.read_text(encoding='utf-8'))

    def test_a_missing_ranking_is_reported_rather_than_recreated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'absent.json'
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = models_script.probe_free(path=path, fetch=self.fail_if_called)
            self.assertEqual(code, 1)
            self.assertFalse(path.exists())
            self.assertIn('nothing to intersect', out.getvalue())

    def test_the_live_catalogue_read_sends_the_configured_key(self):
        captured = {}

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *arguments):
                return False

        def opener(request, timeout=None):
            captured['headers'] = dict(request.headers)
            return Response(json.dumps({'data': [{'id': 'a/b:free'}]}).encode())

        client = OpenRouterClient(key=KEY, models=('a/b:free',), opener=opener, base='https://openrouter.test/v1')
        self.assertEqual([row['id'] for row in client.catalogue(with_key=True)], ['a/b:free'])
        self.assertEqual(captured['headers'].get('Authorization'), 'Bearer ' + KEY)
        client.catalogue()
        self.assertIsNone(captured['headers'].get('Authorization'), 'the public listing needs no key')

    def test_the_probe_defaults_to_the_keyed_catalogue_read(self):
        calls = {}

        class FakeClient:
            def __init__(self, key=None, timeout=None):
                calls['key'] = key
                calls['timeout'] = timeout

            def catalogue(self, with_key=False):
                calls['with_key'] = with_key
                return [{'id': 'a/b:free'}]

        with patch.dict('os.environ', {'OPENROUTER_API_KEY': KEY}, clear=True):
            with patch.object(models_script, 'OpenRouterClient', FakeClient):
                self.assertEqual(models_script.fetch_catalogue(), ['a/b:free'])
        self.assertTrue(calls['with_key'])
        self.assertEqual(calls['key'], KEY)

    @staticmethod
    def fail_if_called():
        raise AssertionError('this run must not read the live catalogue')


if __name__ == '__main__':
    unittest.main()
