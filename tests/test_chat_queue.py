"""A bounded wait queue and cancellation that stops server work between stages.

The page stop control used to abort only the browser request while the server kept
working, and a second question was rejected instantly. These checks pin the replacement:
a bounded queue that says when it is full, a cancellation endpoint that reports exactly
what happened, and checkpoints that discard a stopped turn's partial evidence.
"""
import json
import threading
import unittest
import uuid

import test_answers as fixture
from test_conversation import Model, Places
from test_ingestion import Response, payload
from weathergpt_data.conversation import BoundedGate, ConversationEngine
from weathergpt_data.transport import SourceError
from weathergpt_data.workspace import Workspace


class GateTests(unittest.TestCase):
    def test_waiting_beyond_capacity_is_refused_immediately(self):
        gate = BoundedGate(capacity=1, timeout=2)
        gate.acquire()
        waiting = []

        def hold():
            try:
                gate.acquire()
                waiting.append('acquired')
            except SourceError as error:
                waiting.append(str(error))

        first = threading.Thread(target=hold)
        first.start()
        threading.Event().wait(0.1)
        with self.assertRaises(SourceError) as raised:
            gate.acquire()
        self.assertIn('maximum number of waiting questions', str(raised.exception))
        gate.release()
        first.join(5)
        self.assertEqual(waiting, ['acquired'])
        gate.release()

    def test_a_wait_past_the_timeout_is_refused_rather_than_queued_forever(self):
        gate = BoundedGate(capacity=2, timeout=0.1)
        gate.acquire()
        with self.assertRaises(SourceError) as raised:
            gate.acquire()
        self.assertIn('busy longer than the queue allows', str(raised.exception))
        gate.release()


class BlockingModel(Model):
    def __init__(self):
        super().__init__()
        self.started = threading.Event()
        self.release = threading.Event()

    def plan(self, q, now, history):
        self.started.set()
        self.release.wait(5)
        return super().plan(q, now, history)


class CancellationTests(unittest.TestCase):
    publish = fixture.AnswerTests.publish
    add_place = fixture.AnswerTests.add_place

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.model = BlockingModel()

        def open_(*args, **kwargs):
            return Response(json.dumps(payload()).encode())

        self.app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite',
                             clock=lambda: self.now, opener=open_)
        self.engine = ConversationEngine(self.app, self.model, Places(), self.root / 'conversation.sqlite',
                                         gate=BoundedGate(capacity=2, timeout=5))

    def test_a_running_turn_stops_at_the_next_boundary_and_discards_partial_work(self):
        request_id = str(uuid.uuid4())
        out = {}
        worker = threading.Thread(target=lambda: out.setdefault('result', self.engine.ask(
            {'question': 'Will it rain in Ahmedabad tomorrow morning?', 'request_id': request_id})))
        worker.start()
        self.assertTrue(self.model.started.wait(5))
        reported = self.engine.cancel(request_id)
        self.assertEqual(reported['state'], 'cancel_requested')
        self.assertEqual(reported['stage'], 'started')
        self.model.release.set()
        worker.join(10)
        result = out['result']
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse(result['facts'])
        self.assertIn('discarded', result['answer'])
        self.assertEqual(result['trace']['cancelled']['request_id'], request_id)

    def test_stopping_after_the_turn_finished_is_reported_as_not_running(self):
        request_id = str(uuid.uuid4())
        self.model.release.set()
        result = self.engine.ask({'question': 'Will it rain in Ahmedabad tomorrow morning?', 'request_id': request_id})
        self.assertIn(result['status'], {'answered', 'partial', 'needs_clarification'})
        self.assertEqual(self.engine.cancel(request_id)['state'], 'not_running')

    def test_an_invalid_request_identifier_is_refused(self):
        with self.assertRaises(SourceError):
            self.engine.cancel('not-a-uuid')
        with self.assertRaises(SourceError):
            self.engine.ask({'question': 'Will it rain?', 'request_id': 'not-a-uuid'})


class ProgressTests(unittest.TestCase):
    publish = fixture.AnswerTests.publish
    add_place = fixture.AnswerTests.add_place

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.model = BlockingModel()

        def open_(*args, **kwargs):
            return Response(json.dumps(payload()).encode())

        self.app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite',
                             clock=lambda: self.now, opener=open_)
        self.engine = ConversationEngine(self.app, self.model, Places(), self.root / 'conversation.sqlite',
                                         gate=BoundedGate(capacity=2, timeout=5))

    def test_progress_is_idle_before_a_turn_and_names_the_stage_while_one_runs(self):
        idle = self.engine.progress()
        self.assertEqual(idle['state'], 'idle')
        self.assertIsNone(idle['stage'])
        self.assertEqual(idle['stages_seen'], [])
        self.assertTrue(idle['stages_are_facts_not_progress'])

        out = {}
        worker = threading.Thread(target=lambda: out.setdefault('result', self.engine.ask(
            {'question': 'Will it rain in Ahmedabad tomorrow morning?', 'request_id': str(uuid.uuid4())})))
        worker.start()
        self.assertTrue(self.model.started.wait(5))
        running = self.engine.progress()
        self.assertEqual(running['state'], 'running')
        self.assertEqual(running['stage'], 'started')
        self.assertEqual(running['stage_label'], 'Reading the question')
        self.assertIn('Reading the question', running['stages_seen'])
        self.assertEqual(running['queue']['capacity'], 2)
        # Facts, not an estimate: no percentage, fraction or ETA anywhere in the packet.
        self.assertNotIn('%', json.dumps(running))
        self.assertNotIn('eta', json.dumps(running).lower())
        self.model.release.set()
        worker.join(10)
        self.assertEqual(self.engine.progress()['state'], 'idle')

    def test_the_queue_position_is_the_gates_own_counter(self):
        held = threading.Event()
        out = {}

        def hold():
            worker = threading.Thread(target=lambda: out.setdefault('result', self.engine.ask(
                {'question': 'Will it rain in Ahmedabad tomorrow morning?', 'request_id': str(uuid.uuid4())})))
            worker.start()
            held.set()
            worker.join(20)

        first = threading.Thread(target=hold)
        first.start()
        self.assertTrue(self.model.started.wait(5))
        second = threading.Thread(target=lambda: out.setdefault('second', self.engine.ask(
            {'question': 'Will it rain in Ahmedabad tomorrow morning?'})))
        second.start()
        deadline = threading.Event()
        deadline.wait(0.3)
        waiting = self.engine.progress()
        self.assertGreaterEqual(waiting['queue']['waiting'], 1)
        self.assertEqual(waiting['queue']['active'], 1)
        self.model.release.set()
        first.join(25)
        second.join(25)

    def test_the_stage_sequence_is_pinned_in_order(self):
        seen = []
        original = self.engine._checkpoint

        def record(request_id, stage):
            seen.append(stage)
            return original(request_id, stage)

        self.engine._checkpoint = record
        self.model.release.set()
        result = self.engine.ask({'question': 'Will it rain in Ahmedabad tomorrow morning?'})
        self.assertIn(result['status'], {'answered', 'partial', 'needs_clarification'})
        self.assertEqual(seen[0], 'started')
        self.assertEqual(seen[-1], 'finalising')
        self.assertIn('planned', seen)
        self.assertIn('retrieving', seen)
        self.assertIn('assembling', seen)
        from weathergpt_data.conversation import STAGE_LABELS
        self.assertTrue(set(seen) <= set(STAGE_LABELS), seen)


class WorkspaceCancelTests(unittest.TestCase):
    def test_no_running_turn_is_reported_truthfully(self):
        workspace = Workspace.__new__(Workspace)
        workspace.conversation = None
        packet = Workspace.cancel_chat(workspace, {'request_id': str(uuid.uuid4())})
        self.assertEqual(packet['state'], 'not_running')

    def test_progress_without_a_turn_is_idle_and_reads_as_facts(self):
        workspace = Workspace.__new__(Workspace)
        workspace.conversation = None
        packet = Workspace.chat_progress(workspace)
        self.assertEqual(packet['state'], 'idle')
        self.assertIsNone(packet['stage'])
        self.assertEqual(packet['queue']['waiting'], 0)
        self.assertTrue(packet['stages_are_facts_not_progress'])

    def test_an_invalid_identifier_or_extra_field_is_refused(self):
        workspace = Workspace.__new__(Workspace)
        workspace.conversation = None
        with self.assertRaises(ValueError):
            Workspace.cancel_chat(workspace, {'request_id': 'nope'})
        with self.assertRaises(ValueError):
            Workspace.cancel_chat(workspace, {'request_id': str(uuid.uuid4()), 'question': 'sneak'})


if __name__ == '__main__':
    unittest.main()
