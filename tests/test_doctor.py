"""The environment doctor: it reports what it found, and never readiness.

These are component checks over synthetic and patched inputs. They take no measurement
of this machine; the recorded live run is what docs/47 quotes.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('doctor', ROOT / 'scripts/doctor.py')
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


class DoctorTests(unittest.TestCase):
    def test_summary_counts_and_exit_code_are_separate(self):
        checks = [{'id': 'a', 'state': 'ok', 'detail': '', 'next_action': ''},
                  {'id': 'b', 'state': 'warn', 'detail': 'optional', 'next_action': 'install it'}]
        self.assertEqual(doctor.summarise(checks), {'ok': 1, 'warn': 1, 'fail': 0})
        self.assertEqual(doctor.exit_code(checks), 0, 'A warning does not fail the run')
        checks.append({'id': 'c', 'state': 'fail', 'detail': 'needed', 'next_action': 'install it'})
        self.assertEqual(doctor.exit_code(checks), 1, 'A failure fails the run')

    def test_the_report_never_claims_operational_readiness(self):
        payload = doctor.report([])
        self.assertEqual(payload['schema_version'], 'doctor-report-v1')
        self.assertFalse(payload['operational_ready'])
        self.assertIn('not operational acceptance', payload['note'])

    def test_the_model_endpoint_must_be_loopback(self):
        with patch.dict('os.environ', {'WEATHERGPT_OLLAMA_URL': 'http://example.com:11434'}):
            check = doctor.check_model()
        self.assertEqual(check['state'], 'fail')
        self.assertIn('not loopback', check['detail'])
        self.assertTrue(check['next_action'])

    def test_a_missing_registry_is_named_with_its_next_action(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(doctor, 'ROOT', Path(directory)):
                check = doctor.check_registries()
        self.assertEqual(check['state'], 'fail')
        self.assertIn('sources.json', check['detail'])
        self.assertTrue(check['next_action'])

    def test_every_non_ok_check_in_a_report_names_a_next_action(self):
        checks = [{'id': 'a', 'state': 'ok', 'detail': '', 'next_action': ''},
                  {'id': 'b', 'state': 'warn', 'detail': 'x', 'next_action': 'do y'},
                  {'id': 'c', 'state': 'fail', 'detail': 'z', 'next_action': 'do w'}]
        payload = json.loads(json.dumps(doctor.report(checks)))
        for check in payload['checks']:
            if check['state'] != 'ok':
                self.assertTrue(check['next_action'], check['id'] + ' must name the next action')
        self.assertEqual(payload['counts'], {'ok': 1, 'warn': 1, 'fail': 1})


if __name__ == '__main__':
    unittest.main()
