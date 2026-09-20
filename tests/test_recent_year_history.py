"""A year the published series cannot reach is read from the reanalysis, not refused.

Measured 20 September 2026 against the scenario atlas: "How much rain did Pune get in 2019?"
answered

    Pune, rainfall, 2019: The stored Pune, Maharashtra series covers 1901-2010, with 110 published
    years. It cannot supply 2019.

Every word true about that table, and the wrong product: ERA5 runs from 1940 to within days of now,
and since a daily task may cover a whole calendar year the question was answerable and merely
unroutable. It is the same defect that made "rain in August 2026" unanswerable, one scale up.

The reroute is deliberately narrow, and these tests pin the edges rather than the happy path alone:
mixing a published district record with a modelled reanalysis inside one series or trend is exactly
what this product does not do silently.
"""
import unittest

from weathergpt_data.task_dispatch import recent_year_for_reanalysis


class Clock:
    def __init__(self, year=2026):
        self.year = year

    def clock(self):
        from datetime import datetime, timezone
        return datetime(self.year, 9, 20, tzinfo=timezone.utc)


class Engine:
    def __init__(self, year=2026):
        self.workspace = Clock(year)


def plan(kind='settlement', name='Pune'):
    return {'places': [{'name': name, 'state': 'Maharashtra', 'district': '', 'kind': kind}]}


def task(year, operation='lookup', kind='history'):
    return {'kind': kind, 'operation': operation, 'years': [year], 'place_indices': [0]}


class RecentYearRoutingTests(unittest.TestCase):
    def series(self, last_year):
        def fake(_plan):
            return {'first_year': 1901, 'last_year': last_year}
        return fake

    def route(self, plan_value, task_value, last_year=2010, year=2026):
        import weathergpt_data.research_answers as research
        original = research.series_range
        research.series_range = self.series(last_year)
        try:
            return recent_year_for_reanalysis(plan_value, task_value, Engine(year))
        finally:
            research.series_range = original

    def test_a_year_after_the_series_ends_is_rerouted(self):
        self.assertEqual(self.route(plan(), task(2019)), 2019)

    def test_a_year_the_series_covers_is_left_to_the_published_record(self):
        self.assertIsNone(self.route(plan(), task(1995)))

    def test_a_year_before_the_reanalysis_exists_is_not_rerouted(self):
        """ERA5 starts in 1940. An 1899 question has no product and must keep its honest refusal."""
        self.assertIsNone(self.route(plan(), task(1899)))

    def test_the_current_year_is_left_to_the_month_and_day_paths(self):
        """An incomplete year is not a calendar year, and those paths already trim and disclose."""
        self.assertIsNone(self.route(plan(), task(2026), year=2026))

    def test_a_national_or_state_measure_is_never_a_grid_cell(self):
        """The India series is not a point, and ERA5 at one cell is not a national average.

        Rerouting these turned three answered national questions into "which place?".
        """
        for kind in ('country', 'state', 'relative'):
            with self.subTest(kind=kind):
                self.assertIsNone(self.route(plan(kind=kind), task(2019)))

    def test_only_a_single_year_lookup_is_rerouted(self):
        """A series or trend spanning both products would mix a published record with a model."""
        self.assertIsNone(self.route(plan(), {'kind': 'history', 'operation': 'lookup',
                                              'years': [2019, 2020], 'place_indices': [0]}))
        for operation in ('series', 'trend', 'compare'):
            with self.subTest(operation=operation):
                self.assertIsNone(self.route(plan(), task(2019, operation=operation)))

    def test_no_series_information_is_not_evidence_of_anything(self):
        """Without a known series end there is no reason to believe the table cannot answer."""
        import weathergpt_data.research_answers as research
        original = research.series_range
        research.series_range = lambda _plan: None
        try:
            self.assertIsNone(recent_year_for_reanalysis(plan(), task(2019), Engine()))
        finally:
            research.series_range = original

    def test_a_forecast_task_is_not_touched(self):
        self.assertIsNone(self.route(plan(), task(2019, kind='forecast')))


if __name__ == '__main__':
    unittest.main()
