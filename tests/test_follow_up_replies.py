"""The engine's own next questions: chips the deterministic rules can read before they are offered.

Measured 16 September 2026 in this workspace: the rules floor reads a forecast question when it names
a day AND a part of day ("... the day after tomorrow morning?") and refuses one that names only the
day; the local model planner was not reachable while this batch ran, so a chip must not depend on it.
Every candidate reply is therefore planned by the same rules at offer time and a shape they refuse is
dropped rather than handed to the reader as a promise. A chip names a place and a day only: never a
value, a probability, a warning or a source this turn did not read.
"""
import datetime
import json
import unittest

import test_answers as fixture
from test_conversation import Model, Places
from test_ingestion import Response, payload
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.providers import ModelRouter
from weathergpt_data.workspace import Workspace

QUESTION = 'Will it rain in Ahmedabad tomorrow morning?'


class FollowUpReplyTests(unittest.TestCase):
    publish = fixture.AnswerTests.publish
    add_place = fixture.AnswerTests.add_place

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.calls = []

        def open_(*args, **kwargs):
            self.calls.append(args)
            return Response(json.dumps(payload()).encode())

        self.app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite',
                             clock=lambda: self.now, opener=open_)
        self.engine = ConversationEngine(self.app, Model(), Places(), self.root / 'conversation.sqlite')

    def answer(self, question=QUESTION, **extra):
        return self.engine.ask({'question': question, **extra})

    def test_a_forecast_answer_offers_next_questions_the_rules_can_read(self):
        packet = self.answer()
        self.assertEqual(packet['status'], 'answered')
        replies = packet['quick_replies']
        self.assertTrue(1 <= len(replies) <= 3, 'a forecast answer offers a bounded set of next questions')
        for reply in replies:
            with self.subTest(reply=reply['reply']):
                self.assertEqual(reply['basis'], 'deterministic_rules')
                reading = self.engine.preview({'question': reply['reply']})['reading']
                self.assertIsNotNone(reading, 'a chip must be a question the rules read before it is offered')
                self.assertEqual(reading['basis'], 'rules')
                self.assertIn('Ahmedabad', ' '.join(reading['places']))
        labels = ' | '.join(reply['label'] for reply in replies)
        self.assertIn('the day after tomorrow', labels, 'the day is named in the plan own vocabulary')

    def test_a_chip_repeats_no_value_and_no_probability(self):
        packet = self.answer()
        text = json.dumps(packet['quick_replies'])
        for token in ['mm', '%', 'celsius', 'km/h', 'mm/day', 'sha256']:
            self.assertNotIn(token, text)

    def test_a_tapped_chip_is_planned_by_the_rules_with_no_model(self):
        packet = self.answer()
        rules_only = ConversationEngine(self.app, ModelRouter(clients=[], rules=True, policy='rules'), Places(),
                                        self.root / 'rules-only.sqlite')
        for reply in packet['quick_replies']:
            with self.subTest(reply=reply['reply']):
                tapped = rules_only.ask({'question': reply['reply']})
                self.assertEqual(tapped['trace']['planning']['provider'], 'deterministic_rules')
                self.assertNotEqual(tapped['status'], 'needs_clarification')

    def test_a_turn_that_still_needs_a_choice_offers_no_next_question(self):
        self.engine.gazetteer.ambiguous = True
        packet = self.answer()
        self.assertEqual(packet['status'], 'needs_selection')
        self.assertFalse([reply for reply in (packet.get('quick_replies') or []) if reply.get('basis') == 'deterministic_rules'])

    def test_a_non_forecast_turn_offers_no_next_question_chips(self):
        result = {'status': 'answered', 'facts': [{'place': 'Ahmedabad'}]}
        self.assertEqual(self.engine.follow_up_replies(result, {'intent': 'history'}), [])
        self.assertEqual([reply['label'] for reply in self.engine.follow_up_replies(result, {'intent': 'forecast'})],
                         ['Any warnings for Ahmedabad?'], 'a plan with no window offers no day-based chip')

    def test_a_day_the_rules_cannot_phrase_keeps_only_the_warnings_chip(self):
        far = (self.now.astimezone(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).date()
               + datetime.timedelta(days=6)).isoformat()
        plan = {'intent': 'forecast', 'start_local': far + 'T06:30:00+05:30', 'variables': ['precipitation']}
        result = {'status': 'answered', 'facts': [{'place': 'Ahmedabad'}]}
        replies = self.engine.follow_up_replies(result, plan)
        self.assertEqual([reply['label'] for reply in replies], ['Any warnings for Ahmedabad?'])

    def test_the_part_of_day_is_read_from_the_plan_own_window(self):
        self.assertEqual(self.engine.part_of_day('2026-09-13T06:30:00+05:30'), 'morning')
        self.assertEqual(self.engine.part_of_day('2026-09-13T12:30:00+05:30'), 'afternoon')
        self.assertEqual(self.engine.part_of_day('2026-09-13T18:30:00+05:30'), 'evening')
        self.assertEqual(self.engine.part_of_day('2026-09-13T23:30:00+05:30'), '')
        self.assertEqual(self.engine.part_of_day(''), '')
        self.assertEqual(self.engine.part_of_day('not a time'), '')


if __name__ == '__main__':
    unittest.main()
