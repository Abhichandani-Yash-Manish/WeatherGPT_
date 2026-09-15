"""Plan Watch in the conversation: infer the plan, ask only for what is really missing.

The engine here is a fake with a fixed clock (Tuesday 15 September 2026, 10:00 IST), a
place resolver over a two-entry table and a baseline stub, so these checks exercise only
the turn logic: which slots are set from the person's words, which single question is
asked, when the plan is saved, and how later phrases act on the saved plan.
"""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from weathergpt_data import plan_intake
from weathergpt_data.plans import PlanStore

NOW = datetime(2026, 9, 15, 4, 30, tzinfo=timezone.utc)
RAJKOT = {'name': 'Rajkot', 'label': 'Rajkot, Gujarat', 'coordinates': {'latitude': 22.3, 'longitude': 70.8},
          'district_key': 'RAJKOT', 'district': 'RAJKOT', 'state': 'GUJARAT'}
CHOICES = [{'selection_id': 'geonames:1', 'label': 'Aurangabad, Aurangabad, Maharashtra', 'coordinates': {'latitude': 19.9, 'longitude': 75.3}},
           {'selection_id': 'geonames:2', 'label': 'Aurangabad, Aurangabad, Bihar', 'coordinates': {'latitude': 24.8, 'longitude': 84.4}}]


class FakeEngine:
    def __init__(self, root):
        self.store = PlanStore(Path(root) / 'plans.sqlite')
        self.workspace = SimpleNamespace(clock=lambda: NOW)
        self.baselines = []

    def plan_store(self):
        return self.store

    def resolve_plan_place(self, request):
        if 'choice' in request:
            choice = request['choice']
            return {'status': 'resolved', 'place': {'name': 'Aurangabad', 'label': choice['label'], 'coordinates': choice['coordinates'],
                                                    'district_key': 'AURANGABAD', 'district': 'AURANGABAD'}}
        name = (request.get('name') or '').lower()
        if name == 'rajkot':
            return {'status': 'resolved', 'place': dict(RAJKOT)}
        if name == 'aurangabad':
            return {'status': 'ambiguous', 'choices': CHOICES}
        return {'status': 'not_found'}

    def plan_baseline(self, plan):
        self.baselines.append(plan['id'])
        return {'coverage': 'waiting', 'available_from': '2026-09-17', 'days': {}, 'edition': {}}


class IntakeBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = FakeEngine(self.tmp.name)
        self.state = {'history': [], 'choices': [], 'last_question': None, 'last_plan': None}

    def tearDown(self):
        self.tmp.cleanup()

    def say(self, question, **body):
        return plan_intake.take_turn(self.engine, self.state, dict(body, question=question), question,
                                     {'conversation_id': 'c1', 'question': question, 'notes': [], 'trace': {}})


class CreateTests(IntakeBase):
    def test_a_day_without_a_time_asks_only_for_the_time_and_saves_nothing(self):
        packet = self.say("I'm going to spray fertiliser on my cotton in Rajkot on Monday, let me know if anything changes.")
        self.assertEqual(packet['status'], 'needs_clarification')
        self.assertIn('What time on Monday', packet['answer'])
        self.assertEqual([reply['label'] for reply in packet['quick_replies']], ['Morning', 'Afternoon', 'Evening', 'All day'])
        self.assertEqual(self.engine.store.list(), [])

        saved = self.say('Morning')
        self.assertEqual(saved['status'], 'answered')
        plans = self.engine.store.list()
        self.assertEqual(len(plans), 1)
        plan = plans[0]
        self.assertEqual((plan['activity'], plan['label'], plan['kind']), ('spraying', 'cotton', 'once'))
        self.assertEqual(plan['hazard_codes'], [2, 4, 8, 16, 17])
        self.assertTrue(plan['check_in'])
        self.assertEqual((plan['window_start'], plan['window_end']), ('2026-09-21T09:30:00+05:30', '2026-09-21T12:30:00+05:30'))
        self.assertEqual(plan['place']['district_key'], 'RAJKOT')
        self.assertIn('Monday 21 Sep', saved['answer'])
        self.assertIn('become available on 17 Sep', saved['answer'])
        self.assertIn('evening before', saved['answer'])
        self.assertEqual(saved['plan_watch']['action'], 'saved')
        self.assertEqual(saved['plan_watch']['plan']['id'], plan['id'])
        self.assertEqual(self.engine.baselines, [plan['id']])
        self.assertNotIn('plan_draft', self.state)

    def test_a_fully_described_plan_is_saved_without_a_question(self):
        packet = self.say('Remind me about my wedding in Rajkot on 24 Sep evening')
        self.assertEqual(packet['status'], 'answered')
        self.assertEqual(packet.get('quick_replies') or [], [])
        plan = self.engine.store.list()[0]
        self.assertEqual((plan['activity'], plan['label'], plan['date_local'], plan['part_label']),
                         ('outdoor_event', 'wedding', '2026-09-24', 'evening'))
        self.assertIn(9, plan['hazard_codes'])

    def test_a_missing_place_is_the_first_question_and_the_reply_fills_it(self):
        packet = self.say('Let me know if anything changes for my harvest on Friday morning')
        self.assertIn('Which place', packet['answer'])
        self.assertEqual(self.engine.store.list(), [])
        saved = self.say('rajkot')
        self.assertEqual(saved['status'], 'answered')
        self.assertEqual(self.engine.store.list()[0]['date_local'], '2026-09-18')

    def test_an_ambiguous_place_offers_every_candidate_and_a_selection_completes(self):
        packet = self.say('Notify me about my irrigation in Aurangabad tomorrow morning')
        self.assertEqual(packet['status'], 'needs_selection')
        self.assertEqual(len(packet['choices']), 2)
        saved = self.say('Notify me about my irrigation in Aurangabad tomorrow morning', selection_id='geonames:2')
        self.assertEqual(saved['status'], 'answered')
        self.assertEqual(self.engine.store.list()[0]['place']['label'], 'Aurangabad, Aurangabad, Bihar')

    def test_a_hazard_watch_without_an_activity_or_day_is_a_standing_plan(self):
        packet = self.say('Notify me if a heavy rain warning is issued for Rajkot')
        self.assertEqual(packet['status'], 'answered')
        plan = self.engine.store.list()[0]
        self.assertEqual((plan['kind'], plan['hazard_codes']), ('always', [2, 16, 17]))
        self.assertIn('every day', packet['answer'])
        self.assertIn('your heavy rain watch', packet['answer'])
        self.assertEqual(packet['plan_watch']['plan']['title'], 'Heavy rain watch · Rajkot, Gujarat · every day')

    def test_a_flood_request_is_recorded_as_not_connected(self):
        packet = self.say('Notify me if a flood warning is issued for Rajkot')
        plan = self.engine.store.list()[0]
        self.assertEqual(plan['state'], 'not_connected')
        self.assertIn('flood', packet['answer'])
        self.assertIn('not mapped onto', packet['answer'])
        self.assertEqual(self.engine.baselines, [])

    def test_ordinary_questions_are_left_to_the_engine(self):
        self.assertIsNone(self.say('Will it rain in Rajkot on Monday?'))
        self.assertIsNone(self.say('Tell me if it will rain in Surat tomorrow?'))

    def test_a_new_question_while_a_question_is_open_drops_the_draft(self):
        self.say("I'm going to spray fertiliser on my cotton in Rajkot on Monday, let me know if anything changes.")
        self.assertIn('plan_draft', self.state)
        self.assertIsNone(self.say('What is the temperature in Delhi right now?'))
        self.assertNotIn('plan_draft', self.state)
        self.assertEqual(self.engine.store.list(), [])


class ManageTests(IntakeBase):
    def saved(self):
        self.say('Remind me about spraying my cotton in Rajkot on Monday morning')
        return self.engine.store.list()[0]

    def test_make_it_tuesday_moves_the_plan_just_saved(self):
        plan = self.saved()
        packet = self.say('make it Tuesday')
        self.assertEqual(packet['plan_watch']['action'], 'changed')
        moved = self.engine.store.get(plan['id'])
        self.assertEqual(moved['date_local'], '2026-09-22')
        self.assertEqual(moved['part_label'], 'morning')
        self.assertIn('Tuesday 22 Sep', packet['answer'])

    def test_cancel_the_spraying_reminder_deletes_it(self):
        plan = self.saved()
        self.state.pop('plan_focus', None)
        packet = self.say('cancel the spraying reminder')
        self.assertEqual(packet['plan_watch']['action'], 'deleted')
        self.assertEqual(self.engine.store.list(), [])
        self.assertIn(plan['label'], packet['answer'].lower())

    def test_undo_right_after_saving_deletes_the_plan(self):
        self.saved()
        packet = self.say('undo')
        self.assertEqual(packet['plan_watch']['action'], 'deleted')
        self.assertEqual(self.engine.store.list(), [])

    def test_listing_names_each_plan_and_its_state(self):
        self.saved()
        packet = self.say('what plans do I have?')
        self.assertEqual(packet['plan_watch']['action'], 'listed')
        self.assertIn('Rajkot', packet['answer'])
        self.assertIn('Monday 21 Sep', packet['answer'])

    def test_pause_and_resume(self):
        plan = self.saved()
        self.say('pause my spraying plan')
        self.assertEqual(self.engine.store.get(plan['id'])['state'], 'paused')
        self.say('resume my spraying plan')
        self.assertNotEqual(self.engine.store.get(plan['id'])['state'], 'paused')

    def test_an_ambiguous_cancel_asks_which_plan(self):
        self.saved()
        self.say('Remind me about spraying my cotton in Rajkot on Friday morning')
        self.state.pop('plan_focus', None)
        packet = self.say('cancel my spraying plan')
        self.assertEqual(packet['status'], 'needs_clarification')
        self.assertEqual(len(packet['quick_replies']), 2)
        self.say(packet['quick_replies'][0]['reply'])
        self.assertEqual(len(self.engine.store.list()), 1)


class CandidateTests(IntakeBase):
    def test_watch_this_plan_saves_the_plan_from_the_previous_question(self):
        self.state['plan_candidate'] = 'Will it rain during my spraying in Rajkot on Monday morning?'
        packet = self.say('Watch this plan')
        self.assertEqual(packet['status'], 'answered')
        self.assertEqual(self.engine.store.list()[0]['activity'], 'spraying')

    def test_an_answer_about_the_plan_place_and_day_names_the_plan(self):
        self.say('Remind me about spraying my cotton in Rajkot on Monday morning')
        result = {'resolved_points': {'Rajkot': {'name': 'Rajkot', 'label': 'Rajkot, Rajkot, Gujarat'}},
                  'facts': [{'start': '2026-09-21T09:30:00+05:30', 'end': '2026-09-21T12:30:00+05:30'}]}
        sentences = plan_intake.related_plans(self.engine.store, result)
        self.assertEqual(sentences, ['Monday 21 Sep morning is your cotton spraying plan; I am watching IMD district warnings for it.'])
        result['facts'] = [{'start': '2026-09-23T09:30:00+05:30', 'end': '2026-09-23T12:30:00+05:30'}]
        self.assertEqual(plan_intake.related_plans(self.engine.store, result), [])

    def test_a_plan_like_question_is_offered_a_watch_chip(self):
        self.assertTrue(plan_intake.plan_candidate('Will it rain during my spraying in Rajkot on Monday morning?'))
        self.assertFalse(plan_intake.plan_candidate('Will it rain in Rajkot on Monday?'))


if __name__ == '__main__':
    unittest.main()
