"""Continuity journeys pinned in the suite: a continuation keeps the place, a correction replaces it.

The live journeys are recorded in research/reviews/chat-overhaul-20260916/continuity.json and run against a
model. What can be pinned here is the engine half: given a continuation plan that names no place, the accepted
identity and the source stay; given a correction that names one, the place is replaced and the window stays.
"""
import unittest

import test_answers as fixture
from test_conversation import Model, Places, plan
from test_ingestion import Response, payload
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.workspace import Workspace


class ContinuityJourneyTests(unittest.TestCase):
    publish = fixture.AnswerTests.publish
    add_place = fixture.AnswerTests.add_place

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.model = Model()

        def open_(*args, **kwargs):
            return Response(json.dumps(payload()).encode())

        self.app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite',
                             clock=lambda: self.now, opener=open_)
        self.engine = ConversationEngine(self.app, self.model, Places(), self.root / 'conversation.sqlite')

    def chat(self, **kwargs):
        return self.engine.ask({'question': 'Will it rain in Ahmedabad tomorrow morning?', **kwargs})

    def test_a_continuation_that_names_no_place_keeps_the_place_and_changes_the_window(self):
        first = self.chat()
        self.assertEqual(first['status'], 'answered')
        self.model.value = {**plan(), 'places': [], 'start_local': '2026-09-13T12:30:00+05:30',
                            'end_local': '2026-09-13T18:30:00+05:30', 'context_action': 'follow_up',
                            'changed_fields': ['time']}
        second = self.chat(conversation_id=first['conversation_id'], question='and tomorrow afternoon?')
        self.assertEqual(second['status'], 'answered')
        self.assertEqual(second['plan']['context_action'], 'follow_up')
        self.assertEqual(second['facts'][0]['place'], first['facts'][0]['place'], 'the place is carried')
        self.assertEqual(second['facts'][0]['source_id'], first['facts'][0]['source_id'], 'the source is continuous')
        self.assertNotEqual(second['facts'][0]['start'], first['facts'][0]['start'], 'the window moved')
        self.assertEqual(second['facts'][0]['start'][11:16], '12:30', 'the new part of day is the one asked for')

    def test_a_correction_replaces_the_place_and_keeps_the_window(self):
        first = self.chat()
        self.model.value = {**plan(), 'places': [{'name': 'Vadodara', 'state': 'Gujarat', 'district': '', 'kind': 'settlement'}],
                            'context_action': 'correction', 'changed_fields': ['places']}
        second = self.chat(conversation_id=first['conversation_id'], question='no, I meant Vadodara')
        self.assertEqual(second['status'], 'answered')
        self.assertEqual(second['plan']['context_action'], 'correction')
        self.assertNotEqual(second['facts'][0]['place'], first['facts'][0]['place'])
        self.assertIn('Vadodara', second['facts'][0]['place'])
        self.assertEqual(second['facts'][0]['start'], first['facts'][0]['start'], 'the window is kept')
        self.assertEqual(second['facts'][0]['end'], first['facts'][0]['end'])

    def test_a_mixed_greeting_and_request_still_retrieves_for_the_established_place(self):
        first = self.chat()
        self.model.value = {**plan(), 'places': [], 'context_action': 'follow_up', 'changed_fields': ['time'],
                            'start_local': '2026-09-14T06:30:00+05:30', 'end_local': '2026-09-14T12:30:00+05:30'}
        second = self.chat(conversation_id=first['conversation_id'], question='thanks! and the day after?')
        self.assertEqual(second['status'], 'answered')
        self.assertTrue(second['facts'], 'a greeting attached to a request does not swallow the request')
        self.assertEqual(second['facts'][0]['place'], first['facts'][0]['place'])


if __name__ == '__main__':
    unittest.main()
