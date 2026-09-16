"""The first reading of a question: rules only, no acquisition, never a turn.

A model-planned turn in this workspace has measured 21-38 s, so the front door shows the engine's
own first reading while the real turn works. These checks pin what that reading may be: the
deterministic rules plan it, nothing is acquired over the network, no model is called, no value or
citation appears, no conversation is bound, and no turn is saved. A question the rules cannot read
gets the context the conversation is already carrying, or nothing at all - never a guess.
"""
import copy
import json
import sqlite3
import threading
import unittest

import test_answers as fixture
from test_chat_queue import BlockingModel
from test_conversation import Model, Places
from test_ingestion import Response, payload
from weathergpt_data.conversation import BoundedGate, ConversationEngine
from weathergpt_data.transport import SourceError
from weathergpt_data.workspace import Workspace

QUESTION = 'Will it rain in Ahmedabad tomorrow morning?'
PACKET_KEYS = {'schema_version', 'question', 'provisional', 'reading', 'note',
               'reading_is_not_evidence', 'model_calls', 'checked_at_utc'}
READING_KEYS = {'intent', 'intent_label', 'places', 'window', 'measures', 'products', 'clarification',
                'context_action', 'line', 'basis'}


class NeverAskedModel:
    """A planner that fails the check if a first reading ever reaches for a model."""

    def plan(self, q, now, history):
        raise AssertionError('a first reading must not call the model planner')

    def complete(self, system, user, schema, **kwargs):
        raise AssertionError('a first reading must not call a model')


class PreviewTests(unittest.TestCase):
    publish = fixture.AnswerTests.publish
    add_place = fixture.AnswerTests.add_place

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.calls = []
        self.model = Model()

        def open_(*args, **kwargs):
            self.calls.append(args)
            return Response(json.dumps(payload()).encode())

        self.app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite',
                             clock=lambda: self.now, opener=open_)
        self.engine = ConversationEngine(self.app, self.model, Places(), self.root / 'conversation.sqlite')

    def preview(self, **body):
        return self.engine.preview({'question': QUESTION, **body})

    def conversations(self):
        with sqlite3.connect(self.root / 'conversation.sqlite') as db:
            return db.execute('SELECT COUNT(*) FROM conversations').fetchone()[0]

    def test_a_recognised_question_is_read_out_without_a_model_or_a_network_call(self):
        packet = self.preview()
        self.assertEqual(packet['schema_version'], 'chat-preview-v1')
        self.assertTrue(packet['provisional'])
        self.assertTrue(packet['reading_is_not_evidence'])
        self.assertEqual(packet['model_calls'], 0)
        self.assertIn('may revise it', packet['note'])
        self.assertEqual(self.calls, [])
        self.assertEqual(self.model.histories, [])
        reading = packet['reading']
        self.assertEqual(reading['basis'], 'rules')
        self.assertEqual(reading['places'], ['Ahmedabad'])
        self.assertIn('rain', reading['measures'])
        self.assertEqual([item['kind'] for item in reading['products']], ['forecast'])
        self.assertIn('Ahmedabad', reading['line'])
        self.assertIn('rain', reading['line'])

    def test_a_reading_carries_no_value_no_citation_and_no_status(self):
        packet = self.preview()
        self.assertEqual(set(packet), PACKET_KEYS)
        self.assertEqual(set(packet['reading']), READING_KEYS)
        text = json.dumps(packet['reading'])
        for forbidden in ['mm', 'celsius', 'km/h', '%', 'sha256', 'response_sha256', 'mm/hr']:
            self.assertNotIn(forbidden, text)
        self.assertNotIn('qualified_report', text)
        self.assertNotIn('mm/day', text)

    def test_a_preview_binds_no_conversation_and_saves_no_turn(self):
        first = self.engine.ask({'question': QUESTION})
        _cid, before = self.engine.state(first['conversation_id'])
        counted = self.conversations()
        self.preview()
        self.preview(conversation_id=first['conversation_id'])
        self.preview(question='and tomorrow?', conversation_id=first['conversation_id'])
        _cid, after = self.engine.state(first['conversation_id'])
        self.assertEqual(after, before)
        self.assertEqual(self.conversations(), counted)
        self.assertEqual([message['role'] for message in after['history']], ['user', 'assistant'])

    def test_a_bare_continuation_says_what_is_carried_instead_of_guessing(self):
        first = self.engine.ask({'question': QUESTION})
        packet = self.preview(question='and tomorrow afternoon?', conversation_id=first['conversation_id'])
        reading = packet['reading']
        self.assertIsNotNone(reading)
        self.assertEqual(reading['basis'], 'carried')
        self.assertIn('carrying from your last message', reading['line'])
        self.assertIn('Ahmedabad', reading['line'])
        self.assertIn('rain', reading['line'])
        self.assertFalse(reading['clarification'])

    def test_a_continuation_with_nothing_carried_gets_no_reading(self):
        empty = self.engine.preview({'question': 'and tomorrow?'})
        self.assertIsNone(empty['reading'])
        self.assertTrue(empty['provisional'])

    def test_only_a_question_is_accepted(self):
        for body in [{'question': QUESTION, 'output_language': 'hi'}, {'question': ''}, {'question': 3},
                     {'question': 'x' * 1501}, 'not a body']:
            with self.assertRaises(SourceError):
                self.engine.preview(body)

    def test_a_preview_does_not_wait_behind_a_running_turn(self):
        blocking = BlockingModel()
        engine = ConversationEngine(self.app, blocking, Places(), self.root / 'other.sqlite',
                                    gate=BoundedGate(capacity=2, timeout=5))
        worker = threading.Thread(target=lambda: engine.ask({'question': QUESTION}))
        worker.start()
        self.assertTrue(blocking.started.wait(5))
        seen = {}

        def read():
            seen['packet'] = engine.preview({'question': QUESTION})

        reader = threading.Thread(target=read)
        reader.start()
        reader.join(5)
        self.assertFalse(reader.is_alive(), 'a first reading must not queue behind the running turn')
        self.assertEqual(seen['packet']['reading']['places'], ['Ahmedabad'])
        blocking.release.set()
        worker.join(10)



class PreviewNeverCallsAModelTests(unittest.TestCase):
    """A first reading is planned by the rules; a model call here would defeat the whole point."""

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
        self.engine = ConversationEngine(self.app, NeverAskedModel(), Places(), self.root / 'conversation.sqlite')

    def test_a_reading_is_produced_without_a_model_and_without_a_network_read(self):
        packet = self.engine.preview({'question': QUESTION})
        self.assertEqual(packet['reading']['places'], ['Ahmedabad'])
        self.assertEqual(packet['model_calls'], 0)
        self.assertEqual(self.calls, [])
        self.assertIsNone(self.engine.preview({'question': 'and tomorrow?'})['reading'])
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
