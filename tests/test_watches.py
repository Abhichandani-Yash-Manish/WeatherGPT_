"""Local watch requests: registered explicitly, checked on demand, never faked.

A request to be notified must be answered as a request, not silently turned into a
one-off lookup. These offline checks pin the boundaries: a connected hazard can match a
current official district day; an unconnected hazard (flood) is recorded as not
connected and never mapped onto a similar-sounding product; and a quiet day is not a
match or an all-clear.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from weathergpt_data.watches import WatchStore, check_watch, connected, evaluate, hazard_of, watch_intent


def fact(codes, quiet=False, fact_id='t1-f1', label='Day 1 · Thunderstorm'):
    return {'id': fact_id, 'parameter': 'official_district_warning', 'label': label, 'value': 'yellow',
            'unit': 'IMD district warning colour', 'hazard_codes': codes, 'quiet': quiet,
            'start': '2026-09-15T00:00:00+05:30', 'end': '2026-09-16T00:00:00+05:30', 'source_id': 'S15'}


class IntentTests(unittest.TestCase):
    def test_a_notification_request_is_recognised(self):
        self.assertTrue(watch_intent('Notify me if an official flood warning is issued for Patna tonight'))
        self.assertTrue(watch_intent('Alert me when a heavy rain warning is issued for Ahmedabad'))
        self.assertFalse(watch_intent('Is there an official flood warning for Patna right now?'))

    def test_hazards_are_read_from_the_question(self):
        self.assertEqual(hazard_of('notify me about a flood warning'), 'flood')
        self.assertEqual(hazard_of('tell me if a heavy rain warning is issued'), 'heavy_rain')
        self.assertEqual(hazard_of('notify me if a warning is issued'), 'any_official_warning')
        self.assertFalse(connected('flood'))
        self.assertTrue(connected('heavy_rain'))


class EvaluationTests(unittest.TestCase):
    def test_a_connected_hazard_matches_a_current_official_day(self):
        outcome = evaluate({'facts': [fact([16])]}, 'heavy_rain')
        self.assertTrue(outcome['matched'])
        self.assertEqual(outcome['facts'][0]['fact_id'], 't1-f1')

    def test_an_unconnected_hazard_is_recorded_not_connected(self):
        outcome = evaluate({'facts': [fact([16])]}, 'flood')
        self.assertFalse(outcome['matched'])
        self.assertEqual(outcome['reason'], 'hazard_not_connected')
        self.assertIn('cannot be satisfied', outcome['detail'])

    def test_a_quiet_day_is_not_a_match_and_unmapped_codes_are_reported(self):
        quiet = evaluate({'facts': [fact([1], quiet=True)]}, 'heavy_rain')
        self.assertFalse(quiet['matched'])
        self.assertEqual(quiet['reason'], 'no_matching_current_official_day')
        other = evaluate({'facts': [fact([99])]}, 'heavy_rain')
        self.assertFalse(other['matched'])
        self.assertEqual(other['unmapped_hazard_codes'], [99])


class WatchPlanTests(unittest.TestCase):
    def test_the_fallback_plan_extracts_the_written_place_without_the_model(self):
        from weathergpt_data.conversation import ConversationEngine
        engine = ConversationEngine.__new__(ConversationEngine)
        plan = engine._watch_plan('Notify me if an official flood warning is issued for Guwahati, Assam tonight')
        self.assertEqual([t['kind'] for t in plan['tasks']], ['warning'])
        self.assertEqual(plan['tasks'][0]['request_quote'], 'Notify me if an official flood warning is issued for Guwahati, Assam tonight')
        self.assertEqual(plan['places'][0]['name'], 'Guwahati')
        self.assertEqual(plan['places'][0]['state'], 'Assam')
        self.assertEqual(plan['tasks'][0]['place_indices'], [0])
        self.assertTrue(plan.get('_watch_fallback'))

    def test_a_watch_without_a_place_asks_for_one_and_invents_nothing(self):
        from weathergpt_data.conversation import ConversationEngine
        engine = ConversationEngine.__new__(ConversationEngine)
        plan = engine._watch_plan('Notify me if a warning is issued')
        self.assertEqual(plan['places'], [])
        self.assertIn('Which place should I watch?', plan['clarification'])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = WatchStore(Path(self.tmp.name) / 'watches.sqlite')

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_watch_round_trips_with_its_limits(self):
        watch = self.store.create('Notify me if a heavy rain warning is issued for Ahmedabad tomorrow',
                                  {'name': 'Ahmedabad, Gujarat', 'coordinates': {'latitude': 23.0, 'longitude': 72.5}},
                                  'heavy_rain', window_start='2026-09-16T00:00:00+05:30', window_end='2026-09-17T00:00:00+05:30')
        self.assertEqual(watch['state'], 'registered_check_on_request')
        self.assertEqual(watch['delivery'], 'local_inbox_only_no_push')
        rows = self.store.list()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['place']['name'], 'Ahmedabad, Gujarat')
        self.store.mark(watch['id'], 'checked_no_match', '2026-09-15T10:00:00+00:00', {'reason': 'no_matching_current_official_day'})
        self.assertEqual(self.store.get(watch['id'])['state'], 'checked_no_match')

    def test_check_watch_records_a_match_from_the_warning_tool(self):
        watch = self.store.create('Notify me if a thunderstorm warning is issued for Ahmedabad tomorrow',
                                  {'name': 'Ahmedabad, Gujarat', 'coordinates': {'latitude': 23.0, 'longitude': 72.5}},
                                  'thunderstorm', window_start='2026-09-16T00:00:00+05:30', window_end='2026-09-17T00:00:00+05:30')
        with patch('weathergpt_data.warning_tools.execute_warning',
                   side_effect=lambda engine, packet, plan, task, **kw: {**packet, 'facts': [fact([4])], 'status': 'answered'}):
            outcome = check_watch(self.store, object(), watch, now=__import__('datetime').datetime(2026, 9, 15, tzinfo=__import__('datetime').timezone.utc))
        self.assertTrue(outcome['matched'])
        self.assertEqual(outcome['state'], 'matched')
        self.assertEqual(self.store.get(watch['id'])['state'], 'matched')

    def test_an_expired_window_is_not_checked_against_current_days(self):
        watch = self.store.create('Notify me about a heavy rain warning for Ahmedabad',
                                  {'name': 'Ahmedabad'}, 'heavy_rain', window_start='2026-09-10T00:00:00+05:30', window_end='2026-09-11T00:00:00+05:30')
        from datetime import datetime, timezone
        outcome = check_watch(self.store, object(), watch, now=datetime(2026, 9, 15, tzinfo=timezone.utc))
        self.assertEqual(outcome['state'], 'expired')
        self.assertFalse(outcome['matched'])


if __name__ == '__main__':
    unittest.main()
