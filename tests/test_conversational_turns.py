"""Conversational turns: the model answers, the tools stay out of it, and nothing is invented.

Measured 16 September 2026: "hello" used to end the whole turn with a validation error, and a capability
question was answered from the model's memory of itself. These checks pin the replacement - the model
plans one chat task and writes the reply, no tool runs, and the engine checks the reply for numbers,
units, warning words, source identifiers, links and present-weather claims before a reader sees it. A
reply that states something this workspace has not read is repaired once with the violation named, and
withheld if it still does.
"""
import datetime
import json
import unittest

import test_answers as fixture
from test_conversation import Places
from test_ingestion import Response, payload
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.transport import SourceError
from weathergpt_data.workspace import Workspace

CLEAN = ('Hello! I can check the weather, the official district warnings, published documents and the '
         'published historical rainfall. Tell me a place and a day.')
LEAKING = 'Hello! It is raining in Surat right now, about 12 mm so far.'
REPAIRED = 'Hello! I can check the weather for a place and a day you name.'


def chat_request(reply, quote='hello', language='en'):
    return {'language': language, 'places': [], 'assumptions': [], 'clarification': '', 'explicit_times': False,
            'tasks': [{'request_quote': quote, 'kind': 'chat', 'operation': 'reply', 'parameters': [], 'years': [],
                       'period': 'annual', 'start_local': '', 'end_local': '', 'place_indices': [], 'reply': reply}],
            'context_action': 'new', 'changed_fields': []}


class ChatModel:
    """A planner that answers a conversational message, and a composer for the repair attempt."""

    def __init__(self, reply, repair=None, plan_error=None):
        self.reply = reply
        self.repair = repair
        self.plan_error = plan_error
        self.completions = []

    def plan(self, q, now, history):
        if self.plan_error:
            raise SourceError(self.plan_error)
        return chat_request(self.reply, quote=q[:40]), {'provider': 'stub', 'model': 'stub-1', 'planner_policy': 'model'}

    def complete(self, system, user, schema, **kwargs):
        self.completions.append({'system': system, 'user': user})
        return {'answer': self.repair if self.repair is not None else REPAIRED}, {'provider': 'stub'}


class ConversationalTurnTests(unittest.TestCase):
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

    def ask(self, model, question='hello', name='chat'):
        engine = ConversationEngine(self.app, model, Places(), self.root / (name + '.sqlite'))
        return engine, engine.ask({'question': question})

    def test_a_greeting_is_answered_without_reading_anything(self):
        model = ChatModel(CLEAN)
        engine, packet = self.ask(model)
        self.assertEqual(packet['status'], 'conversation')
        self.assertEqual(packet['answer_basis'], 'conversation')
        self.assertEqual(packet['answer'], CLEAN)
        self.assertEqual(packet['facts'], [])
        self.assertEqual(packet['citations'], [])
        self.assertEqual(self.calls, [], 'a conversational turn must not acquire anything')
        self.assertEqual(model.completions, [], 'the reply came from the plan, so no second call was needed')
        self.assertTrue(any('not retrieved evidence' in note for note in packet['notes']))
        generation = packet['trace']['generation']
        self.assertEqual(generation['status'], 'composed')
        self.assertEqual(generation['planner_policy'], 'model')
        self.assertEqual(packet['trace']['tools'], [{'name': 'conversation', 'status': 'composed', 'model_calls': 1}])
        self.assertEqual(packet['plan']['intent'], 'chat')
        self.assertFalse(packet['operational_eligible'])

    def test_a_reply_that_states_a_number_is_repaired_with_the_violation_named(self):
        model = ChatModel(LEAKING, repair=REPAIRED)
        _engine, packet = self.ask(model)
        self.assertEqual(packet['answer'], REPAIRED)
        self.assertNotIn('12 mm', packet['answer'])
        self.assertEqual(len(model.completions), 1, 'exactly one repair attempt is made')
        self.assertIn('stated a measurement unit', model.completions[0]['system'])
        self.assertEqual(packet['trace']['generation']['repair']['reason'], 'stated a measurement unit')
        self.assertEqual(packet['trace']['generation']['status'], 'composed')

    def test_a_reply_that_still_leaks_is_withheld_rather_than_shown(self):
        model = ChatModel(LEAKING, repair=LEAKING)
        _engine, packet = self.ask(model)
        self.assertEqual(packet['trace']['generation']['status'], 'withheld')
        self.assertNotIn('12 mm', packet['answer'])
        self.assertNotIn('raining in Surat', packet['answer'])
        self.assertIn('could not write a conversational reply', packet['answer'])
        self.assertTrue(any('withheld' in note for note in packet['notes']))
        self.assertEqual(packet['trace']['generation']['reason'], 'stated a measurement unit')
        self.assertEqual(packet['status'], 'conversation')

    def test_every_leak_class_is_caught(self):
        _engine, _packet = self.ask(ChatModel(CLEAN))
        engine = ConversationEngine(self.app, ChatModel(CLEAN), Places(), self.root / 'leaks.sqlite')
        for text, expected in [('Currently 24 degrees.', 'stated a number'),
                               ('Rainfall of 12 mm is expected.', 'stated a measurement unit'),
                               ('Expect about 20 millimetres of rain.', 'stated a measurement unit'),
                               ('It will rain tomorrow at 18:30.', 'stated a date or a time'),
                               ('There is a red alert for the district.', 'used warning language'),
                               ('A warning is in force for the coast.', 'used warning language'),
                               ('Warning: heavy rain.', 'used warning language'),
                               ('सूरत में लाल चेतावनी जारी है।', 'used warning language'),
                               ('See https://example.com for more.', 'named a source or a link'),
                               ('It is raining in Surat.', 'described the weather at a place'),
                               ('', 'was empty')]:
            with self.subTest(text=text):
                self.assertIn(expected, engine.chat_reply_problem(text) or '')
        # Naming a capability is not a claim: a reader may be told the tool reads warnings.
        for clean in ['Hello! Ask me about a place and a day.',
                      'I can read the official district warnings, published documents and historical rainfall.',
                      'मैं मौसम, चेतावनी और प्रकाशित दस्तावेज़ देख सकता हूँ।',
                      '17 times 3 is 51.',
                      'That follows from the numbers you gave.']:
            with self.subTest(text=clean):
                self.assertIsNone(engine.chat_reply_problem(clean))

    def test_a_conversational_turn_is_remembered_but_is_not_evidence(self):
        model = ChatModel(CLEAN)
        engine, packet = self.ask(model)
        _cid, state = engine.state(packet['conversation_id'])
        self.assertEqual([message['role'] for message in state['history']], ['user', 'assistant'])
        self.assertEqual(state['dialogue_state']['status'], 'conversation')
        self.assertNotIn('last_evidence', state, 'a conversational reply must never become retrievable evidence')

    def test_a_hindi_greeting_is_written_in_the_requested_script_and_says_so(self):
        hindi = 'नमस्ते! मैं मौसम, चेतावनी और प्रकाशित दस्तावेज़ देख सकता हूँ।'
        model = ChatModel(hindi)
        engine = ConversationEngine(self.app, model, Places(), self.root / 'hindi.sqlite')
        packet = engine.ask({'question': 'नमस्ते'})
        self.assertEqual(packet['status'], 'conversation')
        self.assertEqual(packet['answer'], hindi)
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'written_in_requested_script')
        self.assertEqual(packet['trace']['generation']['language_selection'], 'inferred_from_question')
        self.assertEqual(self.calls, [])

    def test_a_provider_outage_degrades_the_turn_instead_of_raising(self):
        model = ChatModel(CLEAN, plan_error='No model provider could answer: openrouter: no key')
        engine, packet = self.ask(model)
        self.assertEqual(packet['status'], 'unavailable')
        self.assertIn('No model provider could answer this turn', packet['answer'])
        self.assertIn('planning_error', packet['trace'])
        _cid, state = engine.state(packet['conversation_id'])
        self.assertEqual(len(state['history']), 2, 'the turn is still remembered, so the reader can carry on')

    def test_an_uninterpretable_question_degrades_the_turn_instead_of_raising(self):
        model = ChatModel(CLEAN, plan_error='Question interpretation did not preserve the requested tasks')
        engine, packet = self.ask(model, question='hello')
        self.assertEqual(packet['status'], 'needs_clarification')
        self.assertIn('could not interpret that', packet['answer'])
        self.assertTrue(any('not interpreted' in note for note in packet['notes']))
        self.assertEqual(packet['facts'], [])

    def test_a_conversational_turn_offers_no_next_weather_question_chips(self):
        _engine, packet = self.ask(ChatModel(CLEAN))
        self.assertFalse([reply for reply in (packet.get('quick_replies') or [])])


if __name__ == '__main__':
    unittest.main()
