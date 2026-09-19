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


def test_evidence_for_a_window_already_underway_is_not_born_stale():
    """A window that has already begun must not expire in the past.

    The serving horizon clamped to the moment the requested window begins, whether or not it had begun.
    "What is the air quality in Delhi today?" therefore retrieved two hundred facts and threw every one of
    them away as stale, because "today" starts at midnight and midnight had happened. The same question
    about tomorrow answered. Two independent copies of the rule had it wrong, so it lives in one place.
    """
    from datetime import datetime, timedelta, timezone
    from weathergpt_data.answers import MAX_AGE_SECONDS, serving_horizon

    retrieved = datetime(2026, 9, 20, 6, 0, tzinfo=timezone.utc)
    ceiling = retrieved + timedelta(seconds=MAX_AGE_SECONDS)

    # A window already underway: its start is in the past and must not drag the horizon back with it.
    begun = datetime(2026, 9, 19, 18, 30, tzinfo=timezone.utc)
    assert serving_horizon(retrieved, begun) == ceiling
    assert serving_horizon(retrieved, begun) > retrieved

    # A window that has not begun still closes the horizon: a forecast stops being one once it starts.
    later = retrieved + timedelta(minutes=20)
    assert serving_horizon(retrieved, later) == later

    # Any other limit the caller supplies is honoured, and None limits are ignored.
    sooner = retrieved + timedelta(minutes=5)
    assert serving_horizon(retrieved, later, sooner) == sooner
    assert serving_horizon(retrieved, None, None) == ceiling


def test_a_question_of_only_spaces_is_not_a_question():
    """The length check measured the raw string, so "   " passed it and was answered as a greeting.

    The composer trims before it sends, so this was only ever reachable through the API - which is exactly
    why it should be checked there. A greeting invented for a reader who typed nothing is a sentence this
    product did not have a reason to say.
    """
    import pytest
    from weathergpt_data.transport import SourceError
    from weathergpt_data.conversation import ConversationEngine

    # Unbound on purpose: the guard is the first thing ask() does, before it touches any state, and this
    # checks the guard rather than a whole engine.
    for blank in ("   ", "\t", "\n  \n", ""):
        with pytest.raises(SourceError):
            ConversationEngine.ask(object.__new__(ConversationEngine), {"question": blank})
    # A real question of one character still passes the length guard.
    with pytest.raises(Exception) as raised:
        ConversationEngine.ask(object.__new__(ConversationEngine), {"question": "x"})
    assert "1-1500" not in str(raised.value) and "1\u20131500" not in str(raised.value)


def test_a_journey_question_is_a_travel_question():
    """Endpoint weather is not route weather, and the kind is what says so.

    The planner answers these correctly - both endpoints, the right window - and emits kind='forecast',
    so the travel limitation never attached: "I do not have verified road closures, bridge conditions or
    live transport status." A reader asking what the weather is on the way got two forecasts and nothing
    saying they were not a judgement about the journey.

    Narrow on purpose. travel and forecast dispatch through the same branch, so this changes what is said
    about the answer rather than how it is retrieved - but it must not fire on an ordinary two-place
    question, which is why the wording is required as well as the places.
    """
    from weathergpt_data.dialogue import mark_journeys

    def plan(kind="forecast", places=2):
        return {"places": [{"name": "A"}, {"name": "B"}][:places], "tasks": [{"kind": kind}]}

    journeys = ["I am driving from Surat to Vadodara tomorrow morning, what is the weather on the way?",
                "what is the weather en route from Surat to Vadodara",
                "road trip Surat to Vadodara tomorrow",
                "I am travelling from Surat to Vadodara"]
    for question in journeys:
        assert mark_journeys(plan(), question)["tasks"][0]["kind"] == "travel", question

    # Two places without journey wording is a comparison, not a journey.
    assert mark_journeys(plan(), "Compare the forecast for Surat and Vadodara tomorrow")["tasks"][0]["kind"] == "forecast"
    # Journey wording about one place is not a journey either.
    assert mark_journeys(plan(places=1), "I am driving to Surat tomorrow")["tasks"][0]["kind"] == "forecast"
    # Nothing but a forecast task is touched: a warning stays a warning.
    assert mark_journeys(plan(kind="warning"), journeys[0])["tasks"][0]["kind"] == "warning"
