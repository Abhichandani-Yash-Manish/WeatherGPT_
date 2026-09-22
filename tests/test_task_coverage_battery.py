"""Every answered turn carries a consistent task-coverage record (F2d).

The criterion this closes: task coverage is not recorded for a turn here and there — it is asserted,
in this test, for every turn the battery produces and, through the shared helper, for the turns the
kind-specific suites already produce. The invariant is structural: the record must agree with the
plan and the task results of its own turn, and an answered turn may not quietly carry an incomplete
task (measured 15 September 2026: an answer could look complete while a requested measure had been
dropped; scorer v2 counts dropped tasks separately for the same reason).
"""
import json, unittest
import test_conversation as fixtures
from test_ingestion import Response
from test_product_stage_one import task


def assert_coverage_consistent(case, r):
    """The turn's coverage record agrees with its own plan and task results.

    Reused by the kind-specific suites (warning, specialist, document, air quality, ensemble,
    observation, verification) so the assertion is one implementation, not nine copies that can drift.
    """
    cov = r.get('task_coverage')
    case.assertIsInstance(cov, dict, 'the turn carries no task-coverage record: %r' % (r.get('status'),))
    tasks = (r.get('plan') or {}).get('tasks') or []
    # A CHAT TASK IS NOT A REQUESTED RETRIEVAL, so it is not counted here. This record answers "how much
    # of what you asked for did the tools get"; a greeting asks the tools for nothing, is answered in
    # words, and produces no task result. Counting it made a greeting report "0 of 1 requested task
    # completed in this turn." under the word "Hi!" - the machine announcing a failure at the one moment
    # nothing had been asked of it. The alternative, counting it as completed, would have broken the
    # stronger rule below that `completed` counts task RESULTS, of which a chat task has none.
    retrievable = [t for t in tasks if not (isinstance(t, dict) and t.get('kind') == 'chat')]
    case.assertEqual(cov.get('requested'), len(retrievable),
                     'requested must count the plan tasks that ask the tools for something')
    results = r.get('task_results') or []
    completed = sum(t.get('status') in {'answered', 'explanation'} for t in results)
    case.assertEqual(cov.get('completed'), completed,
                     'completed must count exactly the answered/explanation task results')
    incomplete = [t['id'] for t in results if t.get('status') not in {'answered', 'explanation'}]
    case.assertEqual(cov.get('incomplete_ids'), incomplete, 'incomplete_ids must name every unfinished task')
    if r.get('status') in {'answered', 'explanation'}:
        case.assertFalse(cov['incomplete_ids'], 'an answered turn may not carry an incomplete task')
        case.assertGreaterEqual(cov['completed'], 1, 'an answered turn completed at least one task')
    return cov


class CoverageBatteryTests(unittest.TestCase):
    """The battery across the turn shapes a conversation actually produces."""
    setUp = fixtures.ConversationTests.setUp
    publish = fixtures.ConversationTests.publish
    add_place = fixtures.ConversationTests.add_place
    ask = fixtures.ConversationTests.ask
    chat = fixtures.ConversationTests.chat

    def _point_task(self, parameters, operation='lookup'):
        from test_point_tasks import extended
        self.response = extended()
        def open_(*args, **kw):
            return Response(json.dumps(self.response).encode())
        self.app.opener = open_
        t = task(kind='forecast', operation=operation, parameters=parameters, years=[],
                 start_local='2026-09-13T06:30:00+05:30', end_local='2026-09-13T12:30:00+05:30')
        self.model.value['tasks'] = [t]
        return t

    def test_single_task_answered_turn(self):
        self._point_task(['precipitation_probability'])
        r = self.chat()
        self.assertEqual(r['status'], 'answered', r['answer'])
        cov = assert_coverage_consistent(self, r)
        self.assertEqual(cov, {'requested': 1, 'completed': 1, 'incomplete_ids': []})

    def test_multi_measure_answered_turn(self):
        self._point_task(['wind_gusts_10m', 'visibility', 'apparent_temperature'])
        r = self.chat()
        self.assertEqual(r['status'], 'answered', r['answer'])
        assert_coverage_consistent(self, r)

    def test_two_task_turn_one_unfinished_is_partial_and_named(self):
        first = self._point_task(['precipitation_probability'])
        second = dict(first, parameters=['not_a_parameter'])
        self.model.value['tasks'] = [first, second]
        r = self.chat()
        self.assertEqual(r['status'], 'partial')
        cov = assert_coverage_consistent(self, r)
        self.assertEqual(cov['requested'], 2)
        self.assertEqual(cov['completed'] + len(cov['incomplete_ids']), 2)

    def test_unavailable_turn_still_carries_the_record(self):
        self._point_task(['not_a_parameter'])
        r = self.chat()
        self.assertEqual(r['status'], 'unavailable')
        cov = assert_coverage_consistent(self, r)
        self.assertEqual(cov['completed'], 0)

    def test_needs_selection_turn_carries_the_record(self):
        self.places.ambiguous = True
        self._point_task(['precipitation_probability'])
        r = self.chat()
        self.assertEqual(r['status'], 'needs_selection')
        assert_coverage_consistent(self, r)

    def test_conversation_turn_carries_the_record(self):
        self.model.value = {'intent': 'chat', 'language': 'en', 'places': [], 'start_local': '',
                            'end_local': '', 'explicit_times': False, 'variables': [], 'year': 0,
                            'period': 'annual', 'history_parameter': '', 'unsupported_parameters': [],
                            'assumptions': [], 'clarification': '', 'requested_outcome': 'chat',
                            'tasks': [{'request_quote': 'hello', 'kind': 'chat', 'operation': 'chat',
                                       'parameters': [], 'years': [], 'period': '', 'start_local': '',
                                       'end_local': '', 'place_indices': [], 'reply': 'Hello!'}]}
        r = self.chat(question='hello')
        self.assertEqual(r['status'], 'conversation')
        assert_coverage_consistent(self, r)


if __name__ == '__main__':
    unittest.main()
