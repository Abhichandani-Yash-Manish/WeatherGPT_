"""The engine asking for what it already has, and printing filing where prose belongs (docs/142).

Each test here is one measured failure from the 22 September 2026 atlas run, held against
the repair. The failures were not a coverage gap: the corpus held district agromet passages
for 571 regions and not one of these was caused by a missing document.
"""
import unittest

from weathergpt_data.document_tools import directory_district, read_today
from weathergpt_data.transport import SourceError, parsed


class DirectoryDistrictTests(unittest.TestCase):
    """"...in Davangere" was answered by asking which district was meant."""

    def test_the_publishers_own_spelling_is_resolved_without_asking(self):
        # district_states is an exact dict lookup and the publisher spells it Davanagere, so
        # a question that named the district was answered "Which district and state should I
        # look up in the IMD agricultural bulletin?"
        state, spelled, why = directory_district(['Davangere'])
        self.assertEqual((state, spelled), ('Karnataka', 'Davanagere'))
        self.assertIn('Davanagere', why)

    def test_a_close_name_clearly_ahead_of_the_next_is_taken(self):
        state, spelled, why = directory_district(['Bathinda'])
        self.assertEqual((state, spelled), ('Punjab', 'Bhatinda'))
        self.assertIn('clearly ahead', why)

    def test_an_exact_name_is_taken_as_asked(self):
        self.assertEqual(directory_district(['Nashik'])[:2], ('Maharashtra', 'Nashik'))

    def test_a_name_the_publisher_does_not_list_is_refused_rather_than_guessed(self):
        state, spelled, why = directory_district(['Atlantis'])
        self.assertIsNone(state)
        self.assertIsNone(spelled)
        self.assertIn('close enough', why)

    def test_the_first_candidate_that_is_a_district_wins(self):
        # The resolver supplies several names for one place - the reader's, the catalogue's
        # admin2, the revenue division - and only some are districts.
        self.assertEqual(directory_district(['Not A Place At All', 'Ludhiana'])[1], 'Ludhiana')


class FreshnessWindowTests(unittest.TestCase):
    """A district read today is not fetched again; the window used to be one hour."""

    def head(self, checked_at, status='ok'):
        return {'checked_at': checked_at, 'status': status, 'sha': 'sha'}

    def test_an_edition_read_this_morning_counts_as_read(self):
        now = parsed('2026-09-22T18:00:00+05:30')
        self.assertTrue(read_today(self.head('2026-09-22T06:00:00+05:30'), now))

    def test_an_edition_read_yesterday_does_not(self):
        now = parsed('2026-09-22T09:00:00+05:30')
        self.assertFalse(read_today(self.head('2026-09-21T23:00:00+05:30'), now))

    def test_the_day_is_the_indian_day_not_the_utc_one(self):
        # 2026-09-21T20:00Z is 2026-09-22T01:30 IST: the same Indian morning the reader is in.
        now = parsed('2026-09-22T10:00:00+05:30')
        self.assertTrue(read_today(self.head('2026-09-21T20:00:00+00:00'), now))

    def test_a_failed_read_is_not_a_read(self):
        now = parsed('2026-09-22T18:00:00+05:30')
        self.assertFalse(read_today(self.head('2026-09-22T06:00:00+05:30', 'failed'), now))

    def test_nothing_held_is_not_a_read(self):
        self.assertFalse(read_today(None, parsed('2026-09-22T18:00:00+05:30')))


class BoundedRefreshTests(unittest.TestCase):
    """The reader waits a bounded time; the work is not thrown away when they stop waiting."""

    def test_work_that_finishes_inside_the_budget_is_returned(self):
        from weathergpt_data.document_tools import bounded
        self.assertEqual(bounded(lambda: 'fresh edition', 5), 'fresh edition')

    def test_work_that_outruns_the_budget_yields_none_rather_than_blocking(self):
        import threading
        from weathergpt_data.document_tools import bounded
        released, finished = threading.Event(), threading.Event()

        def slow():
            released.wait(10)
            finished.set()
            return 'late edition'

        self.assertIsNone(bounded(slow, 0.2))
        # The worker was not cancelled: it finishes and its result reaches the index for the
        # next question. A bounded wait, not bounded work.
        released.set()
        self.assertTrue(finished.wait(10))

    def test_an_error_inside_the_budget_still_reaches_the_caller(self):
        from weathergpt_data.document_tools import bounded

        def fails():
            raise SourceError('the publisher refused')

        with self.assertRaises(SourceError):
            bounded(fails, 5)


class NeverHeldDistrictTests(unittest.TestCase):
    """A district with no held edition is bounded too, and told apart from a failure."""

    def sync(self, budget, head=None, refresh=None):
        import types
        from weathergpt_data import document_tools

        index = types.SimpleNamespace(head=lambda s, d: head,
                                      document=lambda sha: {'sha256': sha},
                                      path=__import__('pathlib').Path('/nonexistent/index.sqlite'))
        workspace = types.SimpleNamespace(clock=lambda: parsed('2026-09-22T18:00:00+05:30'))
        original = document_tools._refresh
        document_tools._refresh = refresh or (lambda *a, **k: None)
        try:
            return document_tools.sync(workspace, 'Arunachal Pradesh', 'Lepa Rada', index, budget=budget)
        finally:
            document_tools._refresh = original

    def test_a_first_fetch_that_outruns_the_budget_says_so_rather_than_waiting(self):
        """Measured: this path was unbounded and took 39s to reach a refusal.

        The selection catalogue and the document are separate 25-second requests, so the
        ceiling was near a minute. The reasoning for leaving it unbounded - that a refusal
        after fifteen seconds is worse than an answer after twenty - only held if the extra
        wait bought an answer, and here it bought nothing.
        """
        import threading
        from weathergpt_data.document_tools import STILL_FETCHING
        release = threading.Event()
        self.addCleanup(release.set)
        with self.assertRaises(SourceError) as caught:
            self.sync(0.2, head=None, refresh=lambda *a, **k: release.wait(30))
        self.assertIn(STILL_FETCHING, str(caught.exception))

    def test_a_held_edition_is_named_as_the_fallback_instead(self):
        import threading
        from weathergpt_data.document_tools import STILL_FETCHING
        release = threading.Event()
        self.addCleanup(release.set)
        held = {'sha': 'sha', 'status': 'ok', 'checked_at': '2026-09-19T06:00:00+05:30'}
        with self.assertRaises(SourceError) as caught:
            self.sync(0.2, head=held, refresh=lambda *a, **k: release.wait(30))
        self.assertNotIn(STILL_FETCHING, str(caught.exception))
        self.assertIn('already', str(caught.exception))

    def test_an_edition_read_today_is_served_without_any_fetch(self):
        def must_not_run(*a, **k):
            raise AssertionError('a district read today must not be fetched again')

        head = {'sha': 'today', 'status': 'ok', 'checked_at': '2026-09-22T06:00:00+05:30'}
        self.assertEqual(self.sync(5, head=head, refresh=must_not_run), {'sha256': 'today'})


class WarningWordTests(unittest.TestCase):
    """"Is there any pest warning for cotton in the Bathinda agromet bulletin?" planned nothing."""

    def plan(self, **kwargs):
        base = {'places': [{'name': 'Bathinda', 'state': '', 'district': 'Bathinda', 'kind': 'district'}],
                'language': 'en', 'start_local': None, 'end_local': None, 'tasks': []}
        base.update(kwargs)
        return base

    def agriculture_task(self):
        return {'kind': 'agriculture', 'operation': 'lookup', 'parameters': ['agricultural_advisory'],
                'document_request': {'query': 'pest warning for cotton', 'crop': 'cotton',
                                     'growth_stage': '', 'topic': 'pest', 'mode': 'source_lookup'}}

    def check(self, question, tasks):
        from weathergpt_data.language import validate_request_coverage
        return validate_request_coverage(self.plan(tasks=tasks), question)

    def test_a_pest_warning_in_a_named_bulletin_is_an_agromet_question(self):
        # The validator demanded a warning task because the question contains "warning", so
        # the turn reached the reader with no plan at all and asked which pest was meant. The
        # question named the document, the crop and the district.
        self.check('Is there any pest warning for cotton in the Bathinda agromet bulletin?',
                   [self.agriculture_task()])

    def test_an_advisory_is_the_same_case(self):
        self.check('Any disease warning for cotton in the Bathinda advisory?', [self.agriculture_task()])

    def test_a_bare_warning_question_still_needs_the_warning_tool(self):
        # The carve-out is not a licence to answer an official-warning question out of a
        # bulletin. Nothing here names a published document.
        with self.assertRaises(SourceError):
            self.check('Is there a heat warning for Bathinda?', [self.agriculture_task()])

    def test_a_warning_question_with_a_forecast_task_is_still_refused(self):
        forecast = {'kind': 'forecast', 'operation': 'lookup', 'parameters': ['precipitation']}
        with self.assertRaises(SourceError):
            self.check('Are there warnings for the Bathinda agromet bulletin area?',
                       [self.agriculture_task(), forecast])


if __name__ == '__main__':
    unittest.main()
