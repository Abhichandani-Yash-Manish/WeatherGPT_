"""The warm start: the slow layers are read once, in the background, and say what they did.

Measured on 15 September 2026: the first right-now ask took 146 s cold. With the startup warm and the
page warming its working place, the same ask answered in 2.0 s. These checks pin the honesty of the
mechanism rather than the timing: a layer that fails is recorded as failed with its reason, a partial
warm is not called done, and nothing is inferred from a warm-up."""
import unittest
from unittest.mock import patch

from weathergpt_data.transport import SourceError, utcnow
from weathergpt_data.workspace import Workspace


class WarmLayersTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()

    def test_a_warm_cycle_records_each_layer_with_its_own_seconds(self):
        calls = []

        def fake(name):
            def call(*args, **kwargs):
                calls.append(name)
                return {'data': {}}
            return call

        with patch('weathergpt_data.product_api.observations_bundle', fake('stations')), \
             patch('weathergpt_data.product_api.warnings_place', fake('warning')), \
             patch('weathergpt_data.product_api.forecast', fake('forecast')):
            state = self.workspace.warm_layers([{'latitude': 23.02, 'longitude': 72.58, 'label': 'Ahmedabad'}])
        self.assertEqual(state['state'], 'done')
        self.assertEqual([layer['layer'] for layer in state['layers']],
                         ['station layers', 'district warning layer', 'forecast product'])
        self.assertTrue(all(layer['state'] == 'warmed' for layer in state['layers']))
        self.assertEqual(len(calls), 3)

    def test_a_layer_that_fails_is_recorded_with_its_reason_and_the_state_is_not_done(self):
        def refuse(*args, **kwargs):
            raise SourceError('the warning layer refused the read')

        with patch('weathergpt_data.product_api.observations_bundle', lambda *a, **k: {'data': {}}), \
             patch('weathergpt_data.product_api.warnings_place', refuse), \
             patch('weathergpt_data.product_api.forecast', lambda *a, **k: {'data': {}}):
            state = self.workspace.warm_layers([{'latitude': 23.02, 'longitude': 72.58, 'label': 'Ahmedabad'}])
        self.assertEqual(state['state'], 'partial')
        failed = [layer for layer in state['layers'] if layer['state'] == 'failed']
        self.assertEqual(len(failed), 1)
        self.assertIn('refused the read', failed[0]['detail'])

    def test_the_route_needs_a_point_and_starts_a_background_read(self):
        with self.assertRaises(SourceError):
            self.workspace.warm({})
        with patch.object(Workspace, 'warm_layers', lambda self, places=None: {'state': 'done', 'layers': []}):
            answer = self.workspace.warm({'lat': 23.02, 'lon': 72.58, 'label': 'Ahmedabad'})
        self.assertEqual(answer['schema_version'], 'warm-v1')
        self.assertIn('Nothing is inferred from a warm-up', answer['note'])

    def test_a_fresh_workspace_starts_with_no_warm_record(self):
        self.assertIsNone(getattr(Workspace(), 'warm_state', None))


if __name__ == '__main__':
    unittest.main()