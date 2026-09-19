"""Deterministic context-edit matrix: a clause that supplies a new value wins.

These are offline checks over fixed plan fixtures. They cover the shapes docs/21 A01
named after the reproduced failure: a continuation that changes the time band, the
year, or the asked measure without the model declaring changed_fields.
"""
import unittest

from weathergpt_data.dialogue import negated_measures,reconcile


def forecast_plan(parameters=('precipitation',),start='2026-09-16T06:30:00+05:30',end='2026-09-16T12:30:00+05:30',quote='Will it rain tomorrow morning?'):
    task={'request_quote':quote,'kind':'forecast','operation':'lookup','parameters':list(parameters),'years':[],
          'period':'annual','start_local':start,'end_local':end,'place_indices':[0]}
    return {'language':'en','places':[{'name':'Kochi','state':'Kerala','district':'Ernakulam','kind':'settlement'}],
            'assumptions':[],'clarification':'','explicit_times':False,'tasks':[task]}


def history_plan(years,quote='India rainfall in 2024'):
    task={'request_quote':quote,'kind':'history','operation':'lookup','parameters':['rainfall'],'years':list(years),
          'period':'annual','start_local':'','end_local':'','place_indices':[0]}
    return {'language':'en','places':[{'name':'India','state':'','district':'','kind':'country'}],
            'assumptions':[],'clarification':'','explicit_times':False,'tasks':[task]}


def context(plan):
    return {'last_plan':plan}


class TimeEditTests(unittest.TestCase):
    def test_a_named_evening_band_replaces_the_inherited_morning(self):
        prior=forecast_plan(quote='Will it rain in Kochi tomorrow morning?')
        current=forecast_plan(start='2026-09-16T18:30:00+05:30',end='2026-09-16T22:30:00+05:30',quote='aur shaam ko?')
        current.update(context_action='follow_up',changed_fields=[])
        result=reconcile(current,context(prior),'aur shaam ko?')
        self.assertEqual(result['tasks'][0]['start_local'],'2026-09-16T18:30:00+05:30')
        self.assertIn('time',result['_context_resolution']['changed_fields'])

    def test_the_same_window_is_still_inherited(self):
        prior=forecast_plan(quote='Will it rain in Kochi tomorrow morning?')
        current=forecast_plan(quote='and what about that same morning?')
        current.update(context_action='follow_up',changed_fields=[])
        result=reconcile(current,context(prior),'and what about that same morning?')
        self.assertEqual(result['tasks'][0]['start_local'],prior['tasks'][0]['start_local'])
        self.assertNotIn('time',result['_context_resolution']['changed_fields'])

    def test_a_named_year_replaces_the_inherited_year(self):
        prior=history_plan([2024])
        current=history_plan([2023],quote='and for 2023?')
        current.update(context_action='follow_up',changed_fields=[])
        result=reconcile(current,context(prior),'and for 2023?')
        self.assertEqual(result['tasks'][0]['years'],[2023])
        self.assertIn('time',result['_context_resolution']['changed_fields'])

    def test_an_unnamed_next_year_is_not_invented_over_the_retained_one(self):
        prior=history_plan([2024])
        current=history_plan([2025],quote='and the next one?')
        current.update(context_action='follow_up',changed_fields=[])
        result=reconcile(current,context(prior),'and the next one?')
        self.assertEqual(result['tasks'][0]['years'],[2024])


class MeasureEditTests(unittest.TestCase):
    def test_a_named_new_measure_survives_inherited_parameters(self):
        prior=forecast_plan(parameters=('precipitation_probability','wind_gusts_10m','apparent_temperature'))
        current=forecast_plan(parameters=('precipitation',),quote='compare the rain amount for that same morning with GFS too')
        current.update(context_action='follow_up',changed_fields=['operation'])
        current['tasks'][0]['operation']='crosscheck'
        result=reconcile(current,context(prior),'compare the rain amount for that same morning with GFS too')
        self.assertIn('precipitation',result['tasks'][0]['parameters'])
        self.assertEqual(result['tasks'][0]['operation'],'crosscheck')

    def test_a_correction_that_rules_a_measure_out_drops_it(self):
        prior=forecast_plan(parameters=('precipitation',))
        current=forecast_plan(parameters=('precipitation','temperature_2m'),quote='no, temperature instead of rain')
        current.update(context_action='correction',changed_fields=[])
        result=reconcile(current,context(prior),'no, temperature instead of rain')
        self.assertEqual(result['tasks'][0]['parameters'],['temperature_2m'])

    def test_a_question_that_merely_says_no_rain_does_not_drop_the_task(self):
        plan=forecast_plan(parameters=('precipitation',),quote='Will there be no rain tomorrow?')
        plan.update(context_action='new',changed_fields=[])
        result=reconcile(plan,{},'Will there be no rain tomorrow?')
        self.assertIn('precipitation',result['tasks'][0]['parameters'])
        self.assertEqual(negated_measures('Will there be no rain tomorrow?'),{'precipitation'})
        self.assertEqual(negated_measures('temperature instead of rain'),{'precipitation'})


if __name__=='__main__':
    unittest.main()


def test_a_future_follow_up_does_not_inherit_an_observation():
    """"and tomorrow?" after "what is it like right now" must not read the station layer.

    An observation cannot cover a window that has not happened yet. Inheriting the operation made the
    follow-up read the station layer for a future window, which answers with the latest PAST reading — the
    previous turn's own numbers, returned as the answer to a question about tomorrow, with nothing saying
    they were not. The window resolved correctly all along; only the product read was wrong.

    The switch is recorded in changed_fields rather than made quietly, because the card's
    "carried / changed here" line is how a reader sees that this turn asked a different product.
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from weathergpt_data.dialogue import _window_moved_past

    now = datetime(2026, 9, 20, 11, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    right_now = {"kind": "observation", "start_local": "", "end_local": ""}
    tomorrow = {"start_local": "2026-09-21T00:30:00+05:30", "end_local": "2026-09-22T00:30:00+05:30"}
    yesterday = {"start_local": "2026-09-19T00:30:00+05:30", "end_local": "2026-09-20T00:30:00+05:30"}

    # A "right now" task carries no window, so the clock decides.
    assert _window_moved_past(tomorrow, right_now, now) is True
    assert _window_moved_past(yesterday, right_now, now) is False

    # Where the prior task named a window, the two are compared and no clock is needed.
    monday = {"start_local": "2026-09-20T00:00:00+05:30", "end_local": "2026-09-20T12:00:00+05:30"}
    assert _window_moved_past(tomorrow, monday) is True
    assert _window_moved_past(yesterday, monday) is False

    # Without a clock and without a prior window it inherits as before rather than guessing.
    assert _window_moved_past(tomorrow, right_now, None) is False
    # A window that cannot be parsed is not a reason to switch products.
    assert _window_moved_past({"start_local": "not a date"}, right_now, now) is False
