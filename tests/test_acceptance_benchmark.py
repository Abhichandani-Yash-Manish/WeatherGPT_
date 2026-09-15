"""The declared acceptance benchmark: registry shape and turn scoring, offline.

The runner's scored fields are the contract reviewed in docs/21 A07: requested,
planned, executed and answered are counted separately, abstention is not completion,
and a prohibited-claim hit is a critical failure. These checks do not run the engine.
"""
import json
import unittest
from pathlib import Path

from scripts.benchmark_acceptance import score_turn
from weathergpt_data.tasks import KINDS

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = json.loads((ROOT / 'data/registry/acceptance-benchmark.json').read_text())


def result(tasks, records, status='answered', answer=''):
    return {'status': status, 'answer': answer, 'notes': [],
            'plan': {'tasks': [{'kind': kind, 'operation': operation} for kind, operation in tasks]},
            'task_results': [{'request': {'kind': kind, 'operation': operation}, 'status': record}
                             for (kind, operation), record in zip(tasks, records)]}


class ScoringTests(unittest.TestCase):
    def test_completed_planned_and_missing_are_counted_separately(self):
        turn = {'question': 'q', 'declared_tasks': [{'kind': 'forecast', 'operation': 'lookup'},
                                                    {'kind': 'warning', 'operation': 'lookup'}],
                'allowed_statuses': ['answered']}
        scored = score_turn(turn, result([('forecast', 'lookup')], ['answered']))
        self.assertEqual([t['outcome'] for t in scored['tasks']], ['completed', 'missing'])
        self.assertFalse(scored['task_shape_matches'])

    def test_an_incomplete_execution_is_not_completion(self):
        turn = {'question': 'q', 'declared_tasks': [{'kind': 'document', 'operation': 'lookup'}], 'allowed_statuses': ['partial']}
        scored = score_turn(turn, result([('document', 'lookup')], ['unavailable'], status='partial'))
        self.assertEqual(scored['tasks'][0]['outcome'], 'incomplete')
        self.assertTrue(scored['status_allowed'])

    def test_abstention_is_recorded_separately_from_completion(self):
        turn = {'question': 'q', 'declared_tasks': [], 'allowed_statuses': ['needs_clarification']}
        scored = score_turn(turn, result([], [], status='needs_clarification', answer='Which district?'))
        self.assertTrue(scored['abstained'])
        self.assertEqual(scored['tasks'], [])

    def test_a_prohibited_claim_is_a_critical_hit(self):
        turn = {'question': 'q', 'declared_tasks': [], 'allowed_statuses': ['answered'],
                'prohibited': ['warning is in force', '9999']}
        scored = score_turn(turn, result([], [], status='answered', answer='A warning is in force and 9999 mm will fall.'))
        self.assertEqual(sorted(scored['prohibited_hits']), ['9999', 'warning is in force'])


class RegistryTests(unittest.TestCase):
    def test_every_case_id_is_unique_and_every_kind_is_declared_by_the_schema(self):
        seen = set()
        for name, cases in REGISTRY['sets'].items():
            self.assertTrue(cases, name)
            for case in cases:
                self.assertNotIn(case['id'], seen, case['id'])
                seen.add(case['id'])
                self.assertTrue(case['turns'], case['id'])
                for turn in case['turns']:
                    self.assertTrue(turn['question'])
                    for task in turn.get('declared_tasks', []):
                        self.assertIn(task['kind'], KINDS, case['id'])
                        self.assertTrue(task['operation'])

    def test_the_holdout_is_nonempty_and_declares_its_limitations(self):
        self.assertGreaterEqual(len(REGISTRY['sets']['holdout']), 4)
        self.assertTrue(any('holdout' in note for note in REGISTRY['limitations']))


if __name__ == '__main__':
    unittest.main()
