"""A turn's progress and its result belong to the turn, not to the workspace.

Measured 20 September 2026: /api/chat/progress answered with whatever turn the workspace had
started last, so two pages waiting on two turns were each told the other one's stage; and a turn
whose connection dropped was lost, because no route traded the request id the client minted for the
packet the server had produced. These pin the per-turn read, the queued state, the result states,
and the two reader-made changes (place, window) a turn may carry.
"""
import json
import re
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import test_answers as fixture
from test_chat_queue import BlockingModel
from test_conversation import Model, Places
from test_ingestion import Response, payload
from weathergpt_data.conversation import BoundedGate, ConversationEngine
from weathergpt_data.transport import SourceError
from weathergpt_data.workspace import Workspace, make_server

QUESTION = 'Will it rain in Ahmedabad tomorrow morning?'
IST = ZoneInfo('Asia/Kolkata')


class EngineCase(unittest.TestCase):
    publish = fixture.AnswerTests.publish
    add_place = fixture.AnswerTests.add_place

    def setUp(self):
        fixture.AnswerTests.setUp(self)
        self.model = Model()
        self.places = Places()

        def open_(*args, **kwargs):
            return Response(json.dumps(payload()).encode())

        self.app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite',
                             clock=lambda: self.now, opener=open_)
        self.engine = ConversationEngine(self.app, self.model, self.places, self.root / 'conversation.sqlite',
                                         gate=BoundedGate(capacity=2, timeout=5))
        self.app.conversation = self.engine

    def ask(self, **kw):
        return self.engine.ask({'question': QUESTION, **kw})

    def block_inside_planning(self):
        """Swap in a model that stops inside planning, so a running turn can be observed."""
        self.model = BlockingModel()
        self.engine.model = self.model
        return self.model

    def turn_in_background(self, **kw):
        model = self.block_inside_planning()
        request_id = kw.pop('request_id', None) or str(uuid.uuid4())
        out = {}
        worker = threading.Thread(target=lambda: out.setdefault('result', self.engine.ask(
            {'question': QUESTION, 'request_id': request_id, **kw})))
        worker.start()
        self.assertTrue(model.started.wait(5), 'the fixture turn never started')
        return request_id, out, worker

    def ist_today(self):
        return self.now.astimezone(IST).date()


class PerTurnProgressTests(EngineCase):
    def test_progress_names_only_the_turn_it_was_asked_about(self):
        request_id, out, worker = self.turn_in_background()
        try:
            mine = self.engine.progress(request_id)
            self.assertEqual(mine['state'], 'running')
            self.assertEqual(mine['stage'], 'started')
            self.assertEqual(mine['request_id'], request_id)
            # A second page waiting on its own turn is not handed this one's stage. Before the
            # identifier existed this read answered with the workspace's newest turn.
            other = self.engine.progress(str(uuid.uuid4()))
            self.assertEqual(other['state'], 'not_running')
            self.assertIsNone(other['stage'])
            self.assertNotEqual(other['stage_note'], mine['stage_note'])
            self.assertIn('says nothing about it', other['stage_note'])
            self.assertTrue(other['stages_are_facts_not_progress'])
        finally:
            self.model.release.set()
            worker.join(10)
        self.assertEqual(out['result']['status'], 'answered')

    def test_an_accepted_turn_waiting_for_the_slot_is_queued_not_running(self):
        running_id, out, worker = self.turn_in_background()
        queued_id = str(uuid.uuid4())
        second = {}
        holder = threading.Thread(target=lambda: second.setdefault('result', self.engine.ask(
            {'question': 'Will it rain in Surat tomorrow?', 'request_id': queued_id})))
        holder.start()
        try:
            waiting = None
            for _ in range(60):
                waiting = self.engine.progress(queued_id)
                if waiting['state'] == 'queued':
                    break
                threading.Event().wait(0.05)
            self.assertEqual(waiting['state'], 'queued', 'a turn waiting for the answering slot is not running')
            self.assertEqual(waiting['request_id'], queued_id)
            self.assertIsNone(waiting['stage'])
            self.assertEqual(waiting['stages_seen'], [])
            self.assertIn('waiting for the workspace to start it', waiting['stage_note'])
            self.assertGreaterEqual(waiting['queue']['waiting'], 1)
        finally:
            self.model.release.set()
            worker.join(10)
            holder.join(10)
        self.assertEqual(out['result']['status'], 'answered')
        self.assertIn(second['result']['status'], {'answered', 'needs_clarification', 'partial'})

    def test_no_percentage_eta_or_confidence_anywhere_in_the_read(self):
        request_id, out, worker = self.turn_in_background()
        try:
            text = json.dumps(self.engine.progress(request_id))
            self.assertNotIn('%', text)
            self.assertNotIn('eta', text.lower())
            self.assertNotIn('confidence', text.lower())
        finally:
            self.model.release.set()
            worker.join(10)

    def test_an_identifier_that_is_not_a_uuid_is_refused(self):
        with self.assertRaises(SourceError):
            self.engine.progress('not-a-uuid')
        with self.assertRaises(SourceError):
            self.engine.result('not-a-uuid')


class ResultTests(EngineCase):
    def test_a_running_turn_is_pending_rather_than_an_empty_success(self):
        request_id, out, worker = self.turn_in_background()
        try:
            held = self.engine.result(request_id)
            self.assertEqual(held['state'], 'pending')
            self.assertIsNone(held['packet'])
            self.assertIn('has not finished', held['detail'])
        finally:
            self.model.release.set()
            worker.join(10)

    def test_a_finished_turn_hands_back_its_own_packet(self):
        request_id = str(uuid.uuid4())
        packet = self.engine.ask({'question': QUESTION, 'request_id': request_id})
        self.assertEqual(packet['status'], 'answered')
        kept = self.engine.result(request_id)
        self.assertEqual(kept['state'], 'ready')
        self.assertEqual(kept['packet']['question'], packet['question'])
        self.assertEqual(kept['packet']['facts'][0]['value'], packet['facts'][0]['value'])
        self.assertEqual(kept['request_id'], request_id)
        # The turn is over: progress for it says so rather than reporting the next turn.
        self.assertEqual(self.engine.progress(request_id)['state'], 'not_running')

    def test_a_stopped_turn_is_reported_as_cancelled_with_the_engines_own_packet(self):
        request_id, out, worker = self.turn_in_background()
        self.assertEqual(self.engine.cancel(request_id)['state'], 'cancel_requested')
        self.model.release.set()
        worker.join(10)
        kept = self.engine.result(request_id)
        self.assertEqual(kept['state'], 'cancelled')
        self.assertEqual(kept['packet']['status'], 'cancelled')
        self.assertIn('discarded', kept['packet']['answer'])

    def test_a_result_the_workspace_let_go_is_expired_and_one_it_never_had_is_unknown(self):
        request_id = str(uuid.uuid4())
        self.engine.ask({'question': QUESTION, 'request_id': request_id})
        self.assertEqual(self.engine.result(request_id)['state'], 'ready')
        self.engine.result_keep_seconds = 0
        expired = self.engine.result(request_id)
        self.assertEqual(expired['state'], 'expired', 'a held-and-let-go turn is not one never run here')
        self.assertIsNone(expired['packet'])
        self.assertIn('let its response go', expired['detail'])
        never = self.engine.result(str(uuid.uuid4()))
        self.assertEqual(never['state'], 'unknown')
        self.assertIn('no turn with this identifier', never['detail'].lower())

    def test_a_missing_identifier_is_refused_rather_than_answered_as_unknown(self):
        with self.assertRaises(SourceError):
            self.engine.result(None)
        with self.assertRaises(SourceError):
            self.engine.result('')

    def test_one_turns_packet_is_not_another_turns(self):
        first, second = str(uuid.uuid4()), str(uuid.uuid4())
        self.engine.ask({'question': QUESTION, 'request_id': first})
        self.engine.ask({'question': 'What is the capital of India?', 'request_id': second})
        self.assertNotEqual(self.engine.result(first)['packet']['question'],
                            self.engine.result(second)['packet']['question'])
        self.assertEqual(self.engine.result(second)['packet']['question'], 'What is the capital of India?')


class ReaderChangeTests(EngineCase):
    def test_a_place_the_reader_chose_is_read_instead_of_the_sentence(self):
        # The published fixture job is at 23., 72.5, so the reader's point is that one under their own
        # label: what this pins is whose reading is used, not a second retrieval.
        packet = self.ask(place={'label': 'Surat, Gujarat', 'latitude': 23.0, 'longitude': 72.5,
                                 'state': 'Gujarat'})
        self.assertEqual(packet['status'], 'answered')
        self.assertEqual(self.places.queries, [], 'the reader resolved this place; the engine must not re-search the name')
        point = list(packet['resolved_points'].values())[0]
        self.assertEqual(point['label'], 'Surat, Gujarat')
        self.assertEqual(point['coordinates'], {'latitude': 23.0, 'longitude': 72.5})
        self.assertIn('supplied by the reader', point['name_match_basis'])
        self.assertEqual(packet['facts'][0]['place'], 'Surat, Gujarat')
        changes = [change for change in packet['reader_changes'] if change['field'] == 'place']
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['named_in_question'], 'Ahmedabad')
        self.assertTrue([note for note in packet['notes'] if 'did not resolve the name' in note])

    def test_a_place_resolved_inside_a_task_still_reaches_the_turn(self):
        """The dispatcher resolves a point against its own task packet and merges named fields back.

        Measured 20 September 2026 against the running workspace: the note reached the packet and the
        structured record did not, because the point was resolved inside a task rather than on the
        turn's own packet. The record is held for the turn and merged here, so this pins the merge.
        """
        self.model.value['tasks'] = [{
            'kind': 'forecast', 'operation': 'lookup', 'parameters': ['precipitation'], 'years': [],
            'period': 'annual', 'place_indices': [0],
            'start_local': self.model.value['start_local'], 'end_local': self.model.value['end_local'],
            'request_quote': QUESTION,
        }]
        packet = self.ask(place={'label': 'Surat, Gujarat', 'latitude': 23.0, 'longitude': 72.5, 'state': 'Gujarat'})
        self.assertEqual(packet['status'], 'answered')
        self.assertEqual(len(packet['task_results']), 1, 'the dispatcher ran the task')
        self.assertEqual(packet['facts'][0]['place'], 'Surat, Gujarat')
        changes = [change for change in packet['reader_changes'] if change['field'] == 'place']
        self.assertEqual(len(changes), 1, 'the record survives the merge back from the task')

    def test_a_question_naming_two_places_refuses_to_choose_one(self):
        self.model.value['places'] = [dict(self.model.value['places'][0]),
                                      {**self.model.value['places'][0], 'name': 'Surat'}]
        packet = self.ask(place={'label': 'Pune', 'latitude': 18.5204, 'longitude': 73.8567})
        self.assertEqual(packet['status'], 'needs_clarification')
        self.assertIn('more than one place', packet['answer'])
        self.assertFalse(packet['facts'])

    def test_a_place_without_a_usable_point_is_refused_before_any_work(self):
        for bad in ({'label': 'Surat', 'latitude': 'north', 'longitude': 72.8},
                    {'label': '', 'latitude': 21.1, 'longitude': 72.8},
                    {'label': 'Surat', 'latitude': 21.1, 'longitude': 72.8, 'question': 'sneak'}):
            with self.subTest(place=bad), self.assertRaises(SourceError):
                self.ask(place=bad)

    def test_a_window_the_reader_chose_replaces_the_questions_window(self):
        # The question asks about tomorrow morning. The reader asks for today evening instead, and
        # the facts read are the ones that window covers: this is a change of window, not of question.
        packet = self.ask(window='today evening')
        self.assertEqual(packet['status'], 'answered')
        change = [item for item in packet['reader_changes'] if item['field'] == 'window'][0]
        self.assertTrue(change['applied'], change)
        self.assertIn('day tables', change['basis'])
        expected = self.ist_today().isoformat() + 'T18:30:00+05:30'
        self.assertEqual(packet['plan']['start_local'], expected)
        self.assertEqual(change['label'], '12 Sep 2026 18:30-22:30 IST')
        self.assertEqual(packet['facts'][0]['start'], expected,
                         'the facts read are the ones the changed window covers')

    def test_a_window_that_cannot_be_resolved_is_reported_not_silently_kept(self):
        original = self.ask()['plan']['start_local']
        packet = self.ask(window='whenever it suits')
        self.assertEqual(packet['status'], 'answered')
        change = [item for item in packet['reader_changes'] if item['field'] == 'window'][0]
        self.assertFalse(change['applied'])
        self.assertEqual(packet['plan']['start_local'], original,
                         'the unresolved change leaves the question\'s own window in place')
        self.assertTrue([note for note in packet['notes'] if 'was not applied' in note])

    def test_the_engines_own_two_word_day_phrase_does_not_resolve_yet(self):
        """`day after tomorrow` is in the day table and the shared compiler declines it.

        The phrase contains the shorter word `tomorrow`, so the compiler finds two possible days and
        refuses to guess — which is right, and is left as it is rather than widened here. The change
        is therefore reported as not applied. Recorded so the gap is a fact rather than a surprise.
        """
        packet = self.ask(window='day after tomorrow')
        change = [item for item in packet['reader_changes'] if item['field'] == 'window'][0]
        self.assertFalse(change['applied'])
        self.assertIn('does not name a day', change['detail'])

    def test_a_window_phrase_that_is_not_a_string_is_refused(self):
        with self.assertRaises(SourceError):
            self.ask(window={'start': 'tomorrow'})
        with self.assertRaises(SourceError):
            self.ask(window='x' * 61)


class InlineChoiceTests(EngineCase):
    def test_a_place_choice_resolved_inline_does_not_ask_the_question_twice(self):
        """The client resends the question the choice belongs to, so the engine must not record it again.

        The choice is bound to that question: the engine refuses the choice's own label as a question
        ("This place choice belongs to another question"). What this pins is the other half — the
        conversation's history keeps one user turn, because the reader chose rather than asked.
        """
        self.places.ambiguous = True
        first = self.ask()
        self.assertEqual(first['status'], 'needs_selection')
        with self.assertRaises(SourceError):
            self.ask(conversation_id=first['conversation_id'], selection_id=first['choices'][0]['selection_id'],
                     question=str(first['choices'][0].get('label')))
        second = self.ask(conversation_id=first['conversation_id'],
                          selection_id=first['choices'][0]['selection_id'])
        self.assertEqual(second['status'], 'answered')
        _cid, state = self.engine.state(first['conversation_id'])
        users = [turn for turn in state['history'] if turn['role'] == 'user']
        self.assertEqual(len(users), 1, 'the choice belongs to the question already asked')


class RouteTests(EngineCase):
    def setUp(self):
        super().setUp()
        server = make_server(self.app, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join()))
        self.base = 'http://127.0.0.1:' + str(server.server_port)
        html = urllib.request.urlopen(self.base).read().decode()
        self.token = re.search(r'name="workspace-token" content="([^"]+)"', html)[1]

    def get(self, path):
        request = urllib.request.Request(self.base + path, headers={'X-WeatherGPT-Token': self.token})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
            return json.load(response)

    def status(self, path):
        try:
            self.get(path)
        except urllib.error.HTTPError as error:
            return error.code
        return 200

    def test_the_result_route_answers_the_state_of_the_turn_it_names(self):
        request_id = str(uuid.uuid4())
        packet = self.engine.ask({'question': QUESTION, 'request_id': request_id})
        self.assertEqual(packet['status'], 'answered')
        held = self.get('/api/chat/result?request_id=' + request_id)
        self.assertEqual(held['state'], 'ready')
        self.assertEqual(held['packet']['question'], packet['question'])
        self.assertEqual(self.get('/api/chat/result?request_id=' + str(uuid.uuid4()))['state'], 'unknown')

    def test_the_result_route_refuses_a_missing_or_invalid_identifier_in_words(self):
        self.assertEqual(self.status('/api/chat/result'), 400)
        self.assertEqual(self.status('/api/chat/result?request_id=nope'), 400)
        with self.assertRaises(urllib.error.HTTPError) as unauthed:
            urllib.request.urlopen(self.base + '/api/chat/result?request_id=' + str(uuid.uuid4()))
        self.assertEqual(unauthed.exception.code, 403)

    def test_the_progress_route_echoes_the_turn_it_read_and_does_not_borrow_another(self):
        request_id, out, worker = self.turn_in_background()
        try:
            mine = self.get('/api/chat/progress?request_id=' + request_id)
            self.assertEqual(mine['request_id'], request_id)
            self.assertEqual(mine['state'], 'running')
            other = self.get('/api/chat/progress?request_id=' + str(uuid.uuid4()))
            self.assertEqual(other['state'], 'not_running')
            self.assertIsNone(other['stage'])
            self.assertNotIn('%', json.dumps(other))
            self.assertTrue(other['stages_are_facts_not_progress'])
        finally:
            self.model.release.set()
            worker.join(10)
        self.assertEqual(out['result']['status'], 'answered')

    def test_the_progress_route_without_an_identifier_keeps_its_old_reading(self):
        packet = self.get('/api/chat/progress')
        self.assertEqual(packet['state'], 'idle')
        self.assertIsNone(packet['request_id'])

    def test_the_new_get_route_is_written_the_way_the_route_inventory_enumerates_it(self):
        """The inventory reads `path=='…'` out of workspace.py, so a route written any other way is invisible.

        This route is held the same way /api/chat/progress is, which is what lets the inventory count it.
        """
        from weathergpt_data.workspace import ROOT
        server = (ROOT / 'weathergpt_data' / 'workspace.py').read_text(encoding='utf-8')
        paths = set(re.findall(r"path=='(/api/[a-z0-9/_-]+)'", server))
        self.assertIn('/api/chat/result', paths)
        self.assertIn('/api/chat/progress', paths)


class ColdWorkspaceTests(unittest.TestCase):
    """A workspace on which no turn has ever run: it never had the turn, and says so."""

    def cold(self):
        workspace = Workspace.__new__(Workspace)
        workspace.conversation = None
        return workspace

    def test_a_named_turn_on_a_workspace_with_no_engine_is_not_running_not_idle(self):
        packet = Workspace.chat_progress(self.cold(), {'request_id': [str(uuid.uuid4())]})
        self.assertEqual(packet['state'], 'not_running')
        self.assertIsNone(packet['stage'])
        self.assertIn('says nothing about it', packet['stage_note'])
        self.assertTrue(packet['stages_are_facts_not_progress'])
        # Without an identifier the old reading stands: nothing is running, and it says that.
        idle = Workspace.chat_progress(self.cold())
        self.assertEqual(idle['state'], 'idle')
        self.assertIsNone(idle['request_id'])

    def test_a_result_on_a_workspace_with_no_engine_is_unknown_rather_than_an_error(self):
        held = Workspace.chat_result(self.cold(), {'request_id': [str(uuid.uuid4())]})
        self.assertEqual(held['state'], 'unknown')
        self.assertIsNone(held['packet'])
        self.assertIn('no turn has ever run', held['detail'])
        with self.assertRaises(ValueError):
            Workspace.chat_result(self.cold(), {})
        with self.assertRaises(ValueError):
            Workspace.chat_result(self.cold(), {'request_id': ['nope']})


if __name__ == '__main__':
    unittest.main()
