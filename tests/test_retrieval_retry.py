"""The one re-plan: asking differently after a retrieval came back with nothing (docs/145).

The engine plans once, before it has seen a single result. When that plan is slightly wrong - a
document family one notch too narrow, a district lookup for a question about a state - the tools
correctly report an absence and the turn ends there, telling the reader something is not held when
it was the asking that was wrong.

Most of what is pinned here is the opposite property. This product's most important claim is that an
honest "the publisher has not issued this" is a CORRECT answer, not a failure to work around, and a
retry loop is the obvious way to destroy it. So the tests below spend more assertions on when the
retry must NOT fire than on when it must.
"""
import copy
import types
import unittest

from weathergpt_data import task_dispatch

# The supporting quote on a task must be copied exactly from the question, so the fixture question
# and the fixture plan have to agree - the second plan goes through the SAME validation as the first.
QUESTION = 'What does the bulletin say about the synoptic situation?'


def engine():
    """A ConversationEngine with nothing wired: only the retry decision is under test."""
    from weathergpt_data.conversation import ConversationEngine
    return ConversationEngine.__new__(ConversationEngine)


def result(status='unavailable', **extra):
    base = {'status': status, 'answer': 'Nothing was retrieved for that request.',
            'plan': {'tasks': [{'kind': 'document', 'operation': 'lookup'}]},
            'facts': [], 'passages': [], 'notes': [], 'task_results': [], 'trace': {'tools': []}}
    base.update(extra)
    return base


class WhenItMustNotFireTests(unittest.TestCase):
    def test_a_turn_that_retrieved_facts_is_left_alone(self):
        self.assertFalse(engine().retrieval_came_back_empty(result(status='answered', facts=[{'id': 'f1'}])))

    def test_a_turn_that_retrieved_passages_is_left_alone(self):
        self.assertFalse(engine().retrieval_came_back_empty(result(passages=[{'id': 'p1'}])))

    def test_a_nowcast_turn_carries_evidence_that_is_neither(self):
        self.assertFalse(engine().retrieval_came_back_empty(result(nowcast_records=[{'district_label': 'PUNE'}])))

    def test_asking_the_reader_something_is_an_answer_not_an_empty_retrieval(self):
        """needs_clarification and needs_selection are outcomes. Re-planning around them talks over
        the reader, who has just been asked a question and is owed the chance to answer it."""
        for status in ('needs_clarification', 'needs_selection'):
            self.assertFalse(engine().retrieval_came_back_empty(result(status=status)), status)

    def test_partial_and_stale_carry_evidence_and_are_not_retried(self):
        for status in ('partial', 'stale', 'answered', 'conversation', 'explanation'):
            self.assertFalse(engine().retrieval_came_back_empty(result(status=status)), status)

    def test_a_turn_with_no_tasks_has_no_retrieval_to_repeat(self):
        self.assertFalse(engine().retrieval_came_back_empty(result(plan={'tasks': []})))

    def test_an_empty_unavailable_turn_is_the_one_case_that_qualifies(self):
        self.assertTrue(engine().retrieval_came_back_empty(result()))


class Model:
    """A planner whose second plan is whatever the test says it is."""

    def __init__(self, second=None):
        self.second = second
        self.calls = 0

    def complete(self, system, user, schema, **kwargs):
        self.calls += 1
        return self.second, {'provider': 'fixture'}


class TheOneRetryTests(unittest.TestCase):
    def engine(self, second=None):
        eng = engine()
        eng.model = Model(second)
        eng.workspace = types.SimpleNamespace(clock=lambda: __import__('weathergpt_data.transport',
                                                                      fromlist=['utcnow']).utcnow())
        eng._checkpoint = lambda *a, **k: None
        return eng

    def plan(self):
        return {'tasks': [{'kind': 'document', 'operation': 'lookup'}], 'places': [], 'language': 'en'}

    def second_plan(self):
        return {'language': 'en', 'places': [], 'assumptions': [], 'clarification': '',
                'explicit_times': False, 'context_action': 'new', 'changed_fields': [],
                'tasks': [{'request_quote': 'the synoptic situation', 'kind': 'document',
                           'operation': 'lookup', 'parameters': ['published_document'],
                           'years': [], 'period': 'annual', 'start_local': '', 'end_local': '',
                           'place_indices': [],
                           'corpus_request': {'query': 'synoptic situation', 'family': '',
                                              'scope': '', 'whole_document': False}}]}

    def test_the_model_saying_the_absence_is_real_ends_the_turn(self):
        """The judgement that matters. An empty task list means "this genuinely is not held", and
        the first answer stands untouched - no second refusal worded differently."""
        first = result()
        eng = self.engine(second={'tasks': []})
        out = eng.retry_retrieval_once(first, self.plan(), QUESTION, [], {}, {})
        self.assertEqual(out['answer'], 'Nothing was retrieved for that request.')
        self.assertFalse(out['trace']['retrieval_retry']['attempted'])
        self.assertEqual(out['trace']['retrieval_retry']['judged_by'], 'model')

    def test_a_second_retrieval_that_also_finds_nothing_keeps_the_first_answer(self):
        """Two honest absences are still one absence."""
        eng = self.engine(second=self.second_plan())
        original = task_dispatch.execute_plan
        task_dispatch.execute_plan = lambda *a, **k: result()
        self.addCleanup(lambda: setattr(task_dispatch, 'execute_plan', original))
        out = eng.retry_retrieval_once(result(), self.plan(), QUESTION, [], {}, {})
        self.assertEqual(out['answer'], 'Nothing was retrieved for that request.')
        self.assertEqual(out['trace']['retrieval_retry']['kept'], 'first')

    def test_a_second_retrieval_that_finds_something_is_adopted_and_disclosed(self):
        eng = self.engine(second=self.second_plan())
        found = result(status='answered', answer='The synoptic situation is a trough over the north-west.',
                       passages=[{'id': 'p1', 'text': 'A trough runs over the north-west.'}])
        original = task_dispatch.execute_plan
        task_dispatch.execute_plan = lambda *a, **k: found
        self.addCleanup(lambda: setattr(task_dispatch, 'execute_plan', original))
        out = eng.retry_retrieval_once(result(), self.plan(), QUESTION, [], {}, {})
        self.assertEqual(out['status'], 'answered')
        self.assertTrue(out['passages'])
        self.assertEqual(out['trace']['retrieval_retry']['kept'], 'second')
        # The reader is told the workspace looked twice, and that only the looking changed.
        self.assertTrue(any('asked again a different way' in note for note in out['notes']),
                        'a second retrieval must be disclosed: %r' % (out['notes'],))
        self.assertTrue(any('place and the subject are unchanged' in note for note in out['notes']))

    def test_a_second_retrieval_that_raises_keeps_the_first_answer(self):
        eng = self.engine(second=self.second_plan())
        def boom(*a, **k):
            raise OSError('the network went away')
        original = task_dispatch.execute_plan
        task_dispatch.execute_plan = boom
        self.addCleanup(lambda: setattr(task_dispatch, 'execute_plan', original))
        out = eng.retry_retrieval_once(result(), self.plan(), QUESTION, [], {}, {})
        self.assertEqual(out['answer'], 'Nothing was retrieved for that request.')
        self.assertEqual(out['trace']['retrieval_retry']['kept'], 'first')

    def test_it_is_exactly_one_retry(self):
        """The bound. A loop that retries until something comes back would trade this product's
        honest refusals for the appearance of coverage."""
        eng = self.engine(second=self.second_plan())
        found = result(status='answered', passages=[{'id': 'p1', 'text': 'x'}])
        original = task_dispatch.execute_plan
        task_dispatch.execute_plan = lambda *a, **k: found
        self.addCleanup(lambda: setattr(task_dispatch, 'execute_plan', original))
        eng.retry_retrieval_once(result(), self.plan(), QUESTION, [], {}, {})
        self.assertEqual(eng.model.calls, 1, 'the planner is asked once, never in a loop')

    def test_a_reader_choosing_a_place_is_never_re_planned_around(self):
        """A selection turn is the reader answering a question this engine asked."""
        eng = self.engine(second=self.second_plan())
        out = eng.retry_retrieval_once(result(), self.plan(), QUESTION, [], {}, {'selection_id': 'place:Pune'})
        self.assertEqual(eng.model.calls, 0)
        self.assertNotIn('retrieval_retry', out.get('trace', {}))

    def test_a_planner_failure_leaves_the_first_answer_standing(self):
        from weathergpt_data.transport import SourceError
        eng = self.engine()
        eng.model.complete = lambda *a, **k: (_ for _ in ()).throw(SourceError('no provider'))
        out = eng.retry_retrieval_once(result(), self.plan(), QUESTION, [], {}, {})
        self.assertEqual(out['answer'], 'Nothing was retrieved for that request.')
        self.assertFalse(out['trace']['retrieval_retry']['attempted'])


if __name__ == '__main__':
    unittest.main()
