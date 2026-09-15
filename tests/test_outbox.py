"""Outbox change detection: fingerprints, state machine, ledger, enqueue-on-change.

A watch check fingerprints the official state it observed. The first check
stores a baseline and notifies nothing; a changed state enqueues exactly one
notification; an identical state enqueues nothing. Every state move is written
to the ledger, retries are bounded, and terminal states never re-dispatch.
"""
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from weathergpt_data.outbox import (ACK_RESPONSES, FeedbackStore, OutboxStore, acknowledge,
                                    build_notification_payload, check_transition,
                                    dispatch_outbox, escalate_unacked, retry_delay, MAX_RETRIES)
from weathergpt_data.transport import SourceError
from weathergpt_data.watches import WatchStore, check_due, check_watch, compute_fingerprint

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def fact(codes, quiet=False, fact_id='o1-f1', label='Day 1'):
    return {'id': fact_id, 'parameter': 'official_district_warning', 'label': label, 'value': 'yellow',
            'unit': 'IMD district warning colour', 'hazard_codes': codes, 'quiet': quiet,
            'start': '2026-09-16T00:00:00+05:30', 'end': '2026-09-17T00:00:00+05:30', 'source_id': 'S15'}


def other_fact():
    return {'id': 'x', 'parameter': 'model_forecast', 'label': 'rain', 'value': 3.0}


def make_watch(store, hazard='thunderstorm'):
    return store.create('Notify me if a thunderstorm warning is issued for Ahmedabad tomorrow',
                        {'name': 'Ahmedabad, Gujarat', 'coordinates': {'latitude': 23.0, 'longitude': 72.5}},
                        hazard, window_start='2026-09-16T00:00:00+05:30', window_end='2026-09-18T00:00:00+05:30')


def run_check(store, watch, facts, status='answered'):
    with patch('weathergpt_data.warning_tools.execute_warning',
               side_effect=lambda engine, packet, plan, task, **kw: {**packet, 'facts': facts, 'status': status}):
        return check_watch(store, object(), watch, now=NOW)


class MigrationTests(unittest.TestCase):
    def test_an_old_ten_column_store_migrates_without_data_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            db = sqlite3.connect(path)
            try:
                db.execute('CREATE TABLE watches (id TEXT PRIMARY KEY,created_at TEXT,question TEXT,place TEXT,'
                           'hazard TEXT,window_start TEXT,window_end TEXT,state TEXT,last_checked_at TEXT,result TEXT)')
                db.execute('INSERT INTO watches VALUES (?,?,?,?,?,?,?,?,?,?)',
                           ('w-old', '2026-09-15T10:00:00+00:00', 'q', '{"name":"Patna"}', 'heavy_rain',
                            None, None, 'registered_check_on_request', None, None))
                db.commit()
            finally:
                db.close()
            store = WatchStore(path)
            probe = sqlite3.connect(path)
            try:
                cols = {row[1] for row in probe.execute('PRAGMA table_info(watches)').fetchall()}
            finally:
                probe.close()
            self.assertIn('fingerprint_sha256', cols)
            self.assertIn('channels', cols)
            self.assertIn('consent_record', cols)
            rows = store.list(now=NOW)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['id'], 'w-old')
            self.assertEqual(rows[0]['channels'], ['local_inbox'])
            self.assertEqual(rows[0]['consent_record'], {})
            self.assertIsNone(rows[0]['fingerprint_sha256'])

    def test_create_records_channels_and_consent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WatchStore(Path(tmp) / 'watches.sqlite')
            watch = make_watch(store)
            self.assertEqual(watch['channels'], ['local_inbox'])
            self.assertIn('local_inbox', watch['consent_record'])
            self.assertEqual(watch['consent_record']['local_inbox']['source'], 'explicit_chat_request')
            fetched = store.get(watch['id'])
            self.assertEqual(fetched['channels'], ['local_inbox'])


class FingerprintTests(unittest.TestCase):
    def test_same_inputs_reproduce_the_same_fingerprint(self):
        facts = [fact([4])]
        first = compute_fingerprint('w1', 'thunderstorm', 'Ahmedabad', facts, 'current_official_district_hazard_matches', 'answered')
        second = compute_fingerprint('w1', 'thunderstorm', 'Ahmedabad', [fact([4])], 'current_official_district_hazard_matches', 'answered')
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_a_changed_colour_code_changes_the_fingerprint(self):
        before = compute_fingerprint('w1', 'thunderstorm', 'Ahmedabad', [fact([4])], 'r', 'answered')
        after = compute_fingerprint('w1', 'thunderstorm', 'Ahmedabad', [fact([16])], 'r', 'answered')
        self.assertNotEqual(before, after)

    def test_a_changed_reason_changes_the_fingerprint(self):
        before = compute_fingerprint('w1', 'heavy_rain', 'Ahmedabad', [fact([1], quiet=True)], 'no_matching_current_official_day', 'answered')
        after = compute_fingerprint('w1', 'heavy_rain', 'Ahmedabad', [fact([16])], 'current_official_district_hazard_matches', 'answered')
        self.assertNotEqual(before, after)

    def test_non_warning_facts_do_not_affect_the_fingerprint(self):
        plain = compute_fingerprint('w1', 'heavy_rain', 'Ahmedabad', [fact([1], quiet=True)], 'r', 'answered')
        with_extra = compute_fingerprint('w1', 'heavy_rain', 'Ahmedabad', [fact([1], quiet=True), other_fact()], 'r', 'answered')
        self.assertEqual(plain, with_extra)

    def test_fact_order_does_not_affect_the_fingerprint(self):
        first = compute_fingerprint('w1', 'h', 'P', [fact([4], fact_id='a'), fact([16], fact_id='b')], 'r', 's')
        second = compute_fingerprint('w1', 'h', 'P', [fact([16], fact_id='b'), fact([4], fact_id='a')], 'r', 's')
        self.assertEqual(first, second)


class StateMachineTests(unittest.TestCase):
    def test_valid_transitions_pass_and_invalid_ones_raise(self):
        for old, new in [('created', 'queued'), ('queued', 'sent'), ('sent', 'acked'),
                         ('queued', 'failed'), ('failed', 'queued'), ('failed', 'failed'),
                         ('sent', 'dead'), ('failed', 'dead')]:
            self.assertEqual(check_transition(old, new), new)
        for old, new in [('created', 'sent'), ('queued', 'acked'), ('sent', 'queued'),
                         ('dead', 'queued'), ('acked', 'sent'), ('failed', 'sent')]:
            with self.assertRaises(SourceError):
                check_transition(old, new)

    def test_retry_backoff_is_bounded(self):
        self.assertEqual(retry_delay(1), 60)
        self.assertEqual(retry_delay(2), 300)
        self.assertEqual(retry_delay(3), 900)
        self.assertEqual(retry_delay(99), 900)


class OutboxStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = OutboxStore(Path(self.tmp.name) / 'watches.sqlite')

    def tearDown(self):
        self.tmp.cleanup()

    def test_enqueue_records_queued_and_a_ledger_event(self):
        entry = self.store.enqueue('w1', 'corr-1', 'fp1', 'local_inbox', {'a': 1}, now=NOW)
        self.assertEqual(entry['state'], 'queued')
        self.assertEqual(entry['retry_count'], 0)
        self.assertEqual(entry['max_retries'], MAX_RETRIES)
        fetched = self.store.get(entry['id'])
        self.assertEqual(fetched['payload'], {'a': 1})
        events = self.store.ledger(entry['id'])
        self.assertEqual([event['event'] for event in events], ['queued'])

    def test_set_state_moves_and_records_every_move(self):
        entry = self.store.enqueue('w1', 'corr-1', 'fp1', 'local_inbox', {}, now=NOW)
        self.store.set_state(entry['id'], 'sent', now=NOW)
        self.store.set_state(entry['id'], 'acked', {'response': 'safe'}, now=NOW)
        self.assertEqual(self.store.get(entry['id'])['state'], 'acked')
        events = self.store.ledger(entry['id'])
        self.assertEqual([event['event'] for event in events], ['queued', 'sent', 'acked'])

    def test_failure_increments_retry_and_dead_is_terminal(self):
        entry = self.store.enqueue('w1', 'corr-1', 'fp1', 'local_inbox', {}, now=NOW)
        self.store.set_state(entry['id'], 'failed', 'push refused', now=NOW)
        row = self.store.get(entry['id'])
        self.assertEqual(row['retry_count'], 1)
        self.assertEqual(row['last_error'], 'push refused')
        self.store.set_state(entry['id'], 'dead', 'retries exhausted', now=NOW)
        with self.assertRaises(SourceError):
            self.store.set_state(entry['id'], 'queued', now=NOW)

    def test_unknown_identifiers_raise(self):
        with self.assertRaises(SourceError):
            self.store.get('no-such-id')
        with self.assertRaises(SourceError):
            self.store.set_state('no-such-id', 'sent', now=NOW)

    def test_count_pending_counts_only_dispatchable_rows(self):
        first = self.store.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
        self.store.enqueue('w1', 'c2', 'fp2', 'local_inbox', {}, now=NOW)
        self.assertEqual(self.store.count_pending('w1'), 2)
        self.store.set_state(first['id'], 'sent', now=NOW)
        self.assertEqual(self.store.count_pending('w1'), 1)


class EnqueueOnChangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.store = WatchStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def outbox_rows(self):
        return OutboxStore(self.path).list()

    def test_first_check_is_a_baseline_and_enqueues_nothing(self):
        watch = make_watch(self.store)
        result = run_check(self.store, watch, [fact([4])])
        self.assertEqual(result['fingerprint_basis'], 'baseline')
        self.assertIsNone(result['notification'])
        self.assertEqual(self.outbox_rows(), [])
        self.assertIsNotNone(self.store.get(watch['id'])['fingerprint_sha256'])

    def test_changed_state_enqueues_exactly_one_notification(self):
        watch = make_watch(self.store)
        run_check(self.store, watch, [fact([4])])
        watch = self.store.get(watch['id'])
        result = run_check(self.store, watch, [fact([16])])
        self.assertEqual(result['fingerprint_basis'], 'changed')
        self.assertIsNotNone(result['notification'])
        rows = self.outbox_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['id'], result['notification'])
        self.assertEqual(rows[0]['state'], 'queued')
        self.assertEqual(rows[0]['channel'], 'local_inbox')
        self.assertEqual(rows[0]['fingerprint_sha256'], result['fingerprint_sha256'])
        self.assertTrue(rows[0]['correlation_id'])
        payload = rows[0]['payload']
        self.assertEqual(payload['watch_id'], watch['id'])
        self.assertEqual(payload['hazard'], 'thunderstorm')
        self.assertEqual(payload['place']['name'], 'Ahmedabad, Gujarat')
        self.assertIn('limitations', payload)

    def test_identical_state_enqueues_nothing(self):
        watch = make_watch(self.store)
        run_check(self.store, watch, [fact([4])])
        watch = self.store.get(watch['id'])
        run_check(self.store, watch, [fact([16])])
        watch = self.store.get(watch['id'])
        result = run_check(self.store, watch, [fact([16])])
        self.assertEqual(result['fingerprint_basis'], 'unchanged')
        self.assertIsNone(result['notification'])
        self.assertEqual(len(self.outbox_rows()), 1)

    def test_an_expired_window_touches_no_fingerprint_or_outbox(self):
        watch = self.store.create('Notify me about a heavy rain warning for Ahmedabad',
                                  {'name': 'Ahmedabad'}, 'heavy_rain',
                                  window_start='2026-09-10T00:00:00+05:30', window_end='2026-09-11T00:00:00+05:30')
        result = run_check(self.store, watch, [fact([16])])
        self.assertEqual(result['state'], 'expired')
        self.assertNotIn('fingerprint_sha256', result)
        self.assertEqual(self.outbox_rows(), [])


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.store = WatchStore(self.path)
        self.box = OutboxStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_local_inbox_rows_dispatch_to_sent(self):
        entry = self.box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
        results = dispatch_outbox(self.path, now=NOW)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['to'], 'sent')
        self.assertEqual(self.box.get(entry['id'])['state'], 'sent')

    def test_unknown_channels_fail_closed_then_die_bounded(self):
        entry = self.box.enqueue('w1', 'c1', 'fp1', 'sms', {}, now=NOW)
        first = dispatch_outbox(self.path, now=NOW)
        self.assertEqual(first[0]['to'], 'failed')
        row = self.box.get(entry['id'])
        self.assertEqual(row['retry_count'], 1)
        self.assertIsNotNone(row['next_retry_at'])
        # A row whose retry time has not arrived is not re-dispatched.
        self.assertEqual(dispatch_outbox(self.path, now=NOW), [])
        # Failures keep retrying with backoff until the retry budget is spent.
        from datetime import timedelta
        later = NOW + timedelta(seconds=3600)
        for _ in range(MAX_RETRIES - 1):
            dispatch_outbox(self.path, now=later)
            later = later + timedelta(seconds=3600)
        final = self.box.get(entry['id'])
        self.assertEqual(final['state'], 'dead')
        # Three failed attempts: two recorded retries, then the terminal move.
        self.assertEqual(final['retry_count'], MAX_RETRIES - 1)
        # Terminal rows are never dispatched again.
        self.assertEqual(dispatch_outbox(self.path, now=later), [])

    def test_a_raising_sender_never_breaks_the_loop(self):
        def bad_sender(entry):
            raise RuntimeError('boom')
        first = self.box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
        second = self.box.enqueue('w2', 'c2', 'fp2', 'local_inbox', {}, now=NOW)
        results = dispatch_outbox(self.path, now=NOW, send=bad_sender)
        self.assertEqual(len(results), 2)
        self.assertEqual(self.box.get(first['id'])['state'], 'failed')
        self.assertEqual(self.box.get(second['id'])['state'], 'failed')

    def test_due_skips_rows_with_a_future_retry_time(self):
        entry = self.box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
        self.box.set_state(entry['id'], 'failed', 'try later', now=NOW,
                           next_retry_at='2026-09-17T00:00:00+00:00')
        self.assertEqual(self.box.due(now=NOW), [])
        from datetime import timedelta
        self.assertEqual(len(self.box.due(now=NOW + timedelta(days=2))), 1)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.store = WatchStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_archive_retires_the_watch_and_cancels_pending_rows(self):
        watch = make_watch(self.store)
        run_check(self.store, watch, [fact([4])])
        watch = self.store.get(watch['id'])
        run_check(self.store, watch, [fact([16])])
        box = OutboxStore(self.path)
        self.assertEqual(len(box.list(state='queued', watch_id=watch['id'])), 1)
        result = self.store.archive(watch['id'], now=NOW)
        self.assertEqual(result['state'], 'expired')
        self.assertEqual(result['cancelled_notifications'], 1)
        self.assertEqual(self.store.get(watch['id'])['state'], 'expired')
        self.assertEqual(box.list(state='queued', watch_id=watch['id']), [])
        row = box.list(watch_id=watch['id'])[0]
        self.assertEqual(row['state'], 'dead')

    def test_archive_of_an_unknown_watch_raises(self):
        with self.assertRaises(SourceError):
            self.store.archive('no-such-watch', now=NOW)


class WorkspaceRouteTests(unittest.TestCase):
    def setUp(self):
        import types
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.store = WatchStore(self.path)
        service = types.SimpleNamespace(ingestion_database=self.path.parent / 'ingestion.sqlite')
        self.stub = types.SimpleNamespace(watch_store=lambda: WatchStore(self.path),
                                          clock=lambda: NOW, service=service)
        from weathergpt_data.workspace import Workspace
        self.stub.watches = lambda: Workspace.watches(self.stub)

    def tearDown(self):
        self.tmp.cleanup()

    def test_outbox_route_lists_and_filters(self):
        from weathergpt_data.workspace import Workspace
        watch = make_watch(self.store)
        run_check(self.store, watch, [fact([4])])
        watch = self.store.get(watch['id'])
        run_check(self.store, watch, [fact([16])])
        packet = Workspace.outbox(self.stub, {})
        self.assertEqual(packet['schema_version'], 'outbox-v1')
        self.assertEqual(len(packet['notifications']), 1)
        self.assertEqual(packet['notifications'][0]['payload']['facts'][0]['source_id'], 'S15')
        self.assertTrue(packet['notifications'][0]['payload']['limitations'])
        filtered = Workspace.outbox(self.stub, {'state': 'sent'})
        self.assertEqual(filtered['notifications'], [])
        with self.assertRaises(SourceError):
            Workspace.outbox(self.stub, {'state': 'bogus'})

    def test_watches_route_reports_pending_counts(self):
        from weathergpt_data.workspace import Workspace
        watch = make_watch(self.store)
        run_check(self.store, watch, [fact([4])])
        watch = self.store.get(watch['id'])
        run_check(self.store, watch, [fact([16])])
        packet = Workspace.watches(self.stub)
        rows = [row for row in packet['watches'] if row['id'] == watch['id']]
        self.assertEqual(rows[0]['outbox_pending'], 1)

    def test_delete_watch_route_archives_and_cancels(self):
        from weathergpt_data.workspace import Workspace
        watch = make_watch(self.store)
        result = Workspace.delete_watch(self.stub, {'id': watch['id']})
        self.assertEqual(result['state'], 'expired')
        with self.assertRaises(SourceError):
            Workspace.delete_watch(self.stub, {})
        with self.assertRaises(SourceError):
            Workspace.delete_watch(self.stub, {'id': 'no-such-watch'})


class AckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.box = OutboxStore(self.path)
        self.entry = self.box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {'watch_id': 'w1'}, now=NOW)
        self.box.set_state(self.entry['id'], 'sent', 'delivered', now=NOW)

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_response_acknowledges_and_records_feedback(self):
        for response in ACK_RESPONSES:
            entry = self.box.enqueue('w1', 'c-' + response, 'fp-' + response, 'local_inbox', {}, now=NOW)
            self.box.set_state(entry['id'], 'sent', 'delivered', now=NOW)
            result = acknowledge(self.path, entry['id'], response, now=NOW)
            self.assertEqual(result['state'], 'acked')
            self.assertEqual(result['response'], response)
        feedback = FeedbackStore(self.path).list(watch_id='w1')
        self.assertEqual(sorted(row['response'] for row in feedback), sorted(ACK_RESPONSES))

    def test_unknown_responses_and_wrong_states_raise(self):
        with self.assertRaises(SourceError):
            acknowledge(self.path, self.entry['id'], 'panicking', now=NOW)
        queued = self.box.enqueue('w1', 'c2', 'fp2', 'local_inbox', {}, now=NOW)
        with self.assertRaises(SourceError):
            acknowledge(self.path, queued['id'], 'safe', now=NOW)
        with self.assertRaises(SourceError):
            acknowledge(self.path, 'no-such-id', 'safe', now=NOW)
        # A second acknowledgement of the same row raises: acked is terminal.
        acknowledge(self.path, self.entry['id'], 'seen', now=NOW)
        with self.assertRaises(SourceError):
            acknowledge(self.path, self.entry['id'], 'seen', now=NOW)


class EscalationTests(unittest.TestCase):
    def setUp(self):
        from datetime import timedelta
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.box = OutboxStore(self.path)
        self.timedelta = timedelta

    def tearDown(self):
        self.tmp.cleanup()

    def test_unacked_sent_rows_escalate_after_the_timeout(self):
        entry = self.box.enqueue('w1', 'c1', 'fp1', 'web_push', {'watch_id': 'w1'}, now=NOW)
        self.box.set_state(entry['id'], 'sent', 'pushed', now=NOW)
        self.assertEqual(escalate_unacked(self.path, now=NOW), [])
        created = escalate_unacked(self.path, now=NOW + self.timedelta(seconds=3600))
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]['of'], entry['id'])
        self.assertEqual(created[0]['depth'], 1)
        followup = self.box.get(created[0]['id'])
        self.assertEqual(followup['channel'], 'local_inbox')
        self.assertEqual(followup['state'], 'queued')
        self.assertEqual(followup['payload']['escalation']['depth'], 1)
        self.assertIn('sms', followup['payload']['escalation']['deferred_channels'])

    def test_acked_rows_never_escalate_and_depth_is_bounded(self):
        entry = self.box.enqueue('w1', 'c1', 'fp1', 'web_push', {'watch_id': 'w1'}, now=NOW)
        self.box.set_state(entry['id'], 'sent', 'pushed', now=NOW)
        acknowledge(self.path, entry['id'], 'safe', now=NOW)
        late = NOW + self.timedelta(seconds=7200)
        self.assertEqual(escalate_unacked(self.path, now=late), [])
        # Depth bound: an escalation of an escalation stops at max depth.
        other = self.box.enqueue('w2', 'c2', 'fp2', 'web_push', {'watch_id': 'w2'}, now=NOW)
        self.box.set_state(other['id'], 'sent', 'pushed', now=NOW)
        first = escalate_unacked(self.path, now=late, max_depth=1)
        self.assertEqual(len(first), 1)
        followup = self.box.get(first[0]['id'])
        self.box.set_state(followup['id'], 'sent', 'shown', now=late)
        self.assertEqual(escalate_unacked(self.path, now=late + self.timedelta(seconds=7200), max_depth=1), [])


class DMATests(unittest.TestCase):
    def test_dma_counts_watches_notifications_and_responses(self):
        import types
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            watch = make_watch(store)
            run_check(store, watch, [fact([4])])
            watch = store.get(watch['id'])
            run_check(store, watch, [fact([16])])
            dispatch_outbox(path, now=NOW)
            box = OutboxStore(path)
            sent = box.list(state='sent', watch_id=watch['id'])
            self.assertEqual(len(sent), 1)
            acknowledge(path, sent[0]['id'], 'need_help', now=NOW)
            stub = types.SimpleNamespace(watch_store=lambda: WatchStore(path), clock=lambda: NOW)
            from weathergpt_data.workspace import Workspace
            packet = Workspace.watch_dma(stub, {})
            self.assertEqual(packet['schema_version'], 'watch-dma-v2')
            self.assertEqual(len(packet['places']), 1)
            place = packet['places'][0]
            self.assertEqual(place['place'], 'Ahmedabad, Gujarat')
            self.assertEqual(place['watches'], 1)
            self.assertEqual(place['notifications'], 1)
            self.assertEqual(place['acked'], 1)
            self.assertEqual(place['need_help'], 1)
            self.assertEqual(place['unacked'], 0)
            self.assertEqual(place['sources']['S15']['notifications'], 1)
            self.assertEqual(place['sources']['S15']['acked'], 1)


class ChannelValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.store = WatchStore(self.path)
        self.watch = make_watch(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_unknown_channels_and_removed_inbox_raise(self):
        with self.assertRaises(SourceError):
            self.store.set_channels(self.watch['id'], ['local_inbox', 'sms'], now=NOW)
        with self.assertRaises(SourceError):
            self.store.set_channels(self.watch['id'], ['web_push'], now=NOW)
        with self.assertRaises(SourceError):
            self.store.set_channels(self.watch['id'], [], now=NOW)
        with self.assertRaises(SourceError):
            self.store.set_channels(self.watch['id'], ['local_inbox', 'web_push'],
                                    consent_source='imagined_grant', now=NOW)
        with self.assertRaises(SourceError):
            self.store.set_channels('no-such-watch', ['local_inbox'], now=NOW)

    def test_add_and_remove_round_trip_consent(self):
        updated = self.store.set_channels(self.watch['id'], ['local_inbox', 'web_push'],
                                          consent_source='browser_push_grant', now=NOW)
        self.assertEqual(updated['channels'], ['local_inbox', 'web_push'])
        self.assertEqual(updated['consent_record']['web_push']['source'], 'browser_push_grant')
        self.assertIn('local_inbox', updated['consent_record'])
        removed = self.store.set_channels(self.watch['id'], ['local_inbox'], now=NOW)
        self.assertEqual(removed['channels'], ['local_inbox'])
        self.assertNotIn('web_push', removed['consent_record'])


class PerChannelEnqueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.store = WatchStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_change_enqueues_one_row_per_deliverable_channel(self):
        from weathergpt_data.push import PushStore
        watch = make_watch(self.store)
        run_check(self.store, watch, [fact([4])])
        PushStore(self.path).subscribe('https://push.example.org/e', 'AAA', 'BBB',
                                       watch_id=watch['id'], now=NOW)
        watch = self.store.get(watch['id'])
        result = run_check(self.store, watch, [fact([16])])
        self.assertEqual(result['channels_notified'], ['local_inbox', 'web_push'])
        self.assertEqual(result['channels_skipped'], [])
        self.assertEqual(len(result['notifications']), 2)
        rows = OutboxStore(self.path).list()
        self.assertEqual(sorted(row['channel'] for row in rows), ['local_inbox', 'web_push'])
        self.assertEqual(rows[0]['correlation_id'], rows[1]['correlation_id'])

    def test_undeliverable_channels_skip_without_blocking(self):
        watch = make_watch(self.store)
        run_check(self.store, watch, [fact([4])])
        self.store.set_channels(watch['id'], ['local_inbox', 'web_push'],
                                consent_source='browser_push_grant', now=NOW)
        watch = self.store.get(watch['id'])
        result = run_check(self.store, watch, [fact([16])])
        self.assertEqual(result['channels_notified'], ['local_inbox'])
        self.assertEqual(result['channels_skipped'][0]['reason'], 'no active push subscription')
        self.assertEqual(len(OutboxStore(self.path).list()), 1)


class ChannelRouteTests(unittest.TestCase):
    def test_set_channels_route_validates_and_applies(self):
        import types
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            watch = make_watch(store)
            stub = types.SimpleNamespace(watch_store=lambda: WatchStore(path), clock=lambda: NOW)
            from weathergpt_data.workspace import Workspace
            with self.assertRaises(SourceError):
                Workspace.set_watch_channels(stub, {'id': watch['id'], 'channels': ['local_inbox', 'web_push']})
            with self.assertRaises(SourceError):
                Workspace.set_watch_channels(stub, {'id': watch['id'], 'channels': ['local_inbox', 'sms']})
            with self.assertRaises(SourceError):
                Workspace.set_watch_channels(stub, {'id': 'no-such-watch', 'channels': ['local_inbox']})
            with self.assertRaises(SourceError):
                Workspace.set_watch_channels(stub, {'id': watch['id']})
            from weathergpt_data.push import PushStore
            PushStore(path).subscribe('https://push.example.org/e', 'AAA', 'BBB',
                                      watch_id=watch['id'], now=NOW)
            result = Workspace.set_watch_channels(
                stub, {'id': watch['id'], 'channels': ['local_inbox', 'web_push']})
            self.assertEqual(result['schema_version'], 'watch-channels-v1')
            self.assertIn('web_push', result['channels'])


class GoneStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.store = WatchStore(self.path)
        self.box = OutboxStore(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_gone_is_terminal_and_reachable_from_open_states(self):
        for old in ['created', 'queued', 'sent', 'failed']:
            self.assertEqual(check_transition(old, 'gone'), 'gone')
        entry = self.box.enqueue('w1', 'c', 'fp', 'local_inbox', {}, now=NOW)
        self.box.set_state(entry['id'], 'sent', 'delivered', now=NOW)
        failed = self.box.enqueue('w1', 'c2', 'fp2', 'local_inbox', {}, now=NOW)
        self.box.set_state(failed['id'], 'failed', 'x', now=NOW,
                           next_retry_at='2026-09-17T00:00:00+00:00')
        for row_id in (entry['id'], failed['id']):
            self.box.set_state(row_id, 'gone', 'superseded', now=NOW)
            self.assertEqual(self.box.get(row_id)['state'], 'gone')
            with self.assertRaises(SourceError):
                self.box.set_state(row_id, 'queued', now=NOW)
        self.assertEqual(dispatch_outbox(self.path, now=NOW), [])

    def test_lapsed_window_marks_queued_gone_instead_of_sending(self):
        watch = self.store.create('Notify me about a heavy rain warning for Ahmedabad',
                                  {'name': 'Ahmedabad'}, 'heavy_rain',
                                  window_start='2026-09-16T00:00:00+05:30',
                                  window_end='2026-09-16T01:00:00+05:30')
        entry = self.box.enqueue(watch['id'], 'c1', 'fp1', 'local_inbox', {}, now=NOW)
        results = dispatch_outbox(self.path, now=NOW + __import__('datetime').timedelta(hours=5))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['to'], 'gone')
        self.assertEqual(self.box.get(entry['id'])['state'], 'gone')


class ArchiveSentTests(unittest.TestCase):
    def test_archive_cancels_sent_rows_and_blocks_escalation(self):
        from datetime import timedelta
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            box = OutboxStore(path)
            watch = make_watch(store)
            run_check(store, watch, [fact([4])])
            watch = store.get(watch['id'])
            run_check(store, watch, [fact([16])])
            dispatch_outbox(path, now=NOW)
            self.assertEqual(len(box.list(state='sent')), 1)
            result = store.archive(watch['id'], now=NOW)
            self.assertEqual(result['cancelled_notifications'], 1)
            self.assertEqual(box.list(state='sent'), [])
            late = NOW + timedelta(hours=3)
            self.assertEqual(escalate_unacked(path, now=late), [])


class CrashAtomicityTests(unittest.TestCase):
    def test_failed_enqueue_leaves_no_row_and_no_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            box = OutboxStore(path)
            watch = make_watch(store)
            run_check(store, watch, [fact([4])])
            watch = store.get(watch['id'])
            before = watch['fingerprint_sha256']
            with patch.object(OutboxStore, '_record', side_effect=RuntimeError('crash')):
                with self.assertRaises(RuntimeError):
                    box.enqueue_changed(watch['id'], 'corr', 'fp-new', ['local_inbox'], {}, now=NOW)
            self.assertEqual(box.list(), [])
            self.assertEqual(store.get(watch['id'])['fingerprint_sha256'], before)


class UnconnectedHeldTests(unittest.TestCase):
    def test_flood_watch_advances_fingerprint_but_never_enqueues(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            watch = store.create('Notify me if an official flood warning is issued for Patna tonight',
                                 {'name': 'Patna, Bihar'}, 'flood')
            first = run_check(store, watch, [fact([1], quiet=True)])
            self.assertEqual(first['fingerprint_basis'], 'baseline')
            watch = store.get(watch['id'])
            second = run_check(store, watch, [fact([16])])
            self.assertEqual(second['fingerprint_basis'], 'not_connected_held')
            self.assertIsNone(second['notification'])
            self.assertEqual(OutboxStore(path).list(), [])
            self.assertNotEqual(store.get(watch['id'])['fingerprint_sha256'],
                                first['fingerprint_sha256'])


class HoldUnavailableTests(unittest.TestCase):
    def test_unavailable_holds_fingerprint_and_enqueues_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            watch = make_watch(store)
            result = run_check(store, watch, [fact([4])], status='unavailable')
            self.assertEqual(result['fingerprint_basis'], 'held_unavailable')
            self.assertIsNone(store.get(watch['id'])['fingerprint_sha256'])
            self.assertEqual(OutboxStore(path).list(), [])
            baseline = run_check(store, store.get(watch['id']), [fact([4])])
            self.assertEqual(baseline['fingerprint_basis'], 'baseline')
            self.assertEqual(OutboxStore(path).list(), [])


class CapHashTests(unittest.TestCase):
    def test_cap_counts_move_the_fingerprint(self):
        before = compute_fingerprint('w1', 'heavy_rain', 'P', [fact([16])], 'r', 'answered', 2, 5)
        same = compute_fingerprint('w1', 'heavy_rain', 'P', [fact([16])], 'r', 'answered', 2, 5)
        after = compute_fingerprint('w1', 'heavy_rain', 'P', [fact([16])], 'r', 'answered', 1, 5)
        self.assertEqual(before, same)
        self.assertNotEqual(before, after)
        legacy = compute_fingerprint('w1', 'heavy_rain', 'P', [fact([16])], 'r', 'answered')
        self.assertEqual(len(legacy), 64)

    def test_cap_cancel_drives_exactly_one_notification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            watch = make_watch(store)
            trace = [{'name': 'official_district_warning', 'cap_lifecycle_eligible': 2, 'cap_messages': 5}]

            def fake(engine, packet, plan, task, **kw):
                return {**packet, 'facts': [fact([16])], 'status': 'answered',
                        'trace': {'tools': list(trace), 'generation': None}}

            with patch('weathergpt_data.warning_tools.execute_warning', side_effect=fake):
                first = check_watch(store, object(), watch, now=NOW)
            self.assertEqual(first['fingerprint_basis'], 'baseline')
            trace[:] = [{'name': 'official_district_warning', 'cap_lifecycle_eligible': 0,
                         'cap_messages': 5}]
            with patch('weathergpt_data.warning_tools.execute_warning', side_effect=fake):
                second = check_watch(store, object(), store.get(watch['id']), now=NOW)
            self.assertEqual(second['fingerprint_basis'], 'changed')
            self.assertIsNotNone(second['notification'])
            self.assertEqual(len(OutboxStore(path).list()), 1)


class LockTests(unittest.TestCase):
    def test_second_holder_gets_a_clean_refusal(self):
        import subprocess
        import sys
        import time
        root = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            lock_path = str(path.with_suffix('.watch-check.lock'))
            holder = subprocess.Popen(
                [sys.executable, '-c',
                 'import sys,time; sys.path.insert(0, %r);'
                 'from weathergpt_data.filelock import try_lock_exclusive;'
                 'h = open(%r, "a"); try_lock_exclusive(h); time.sleep(20)' % (root, lock_path)])
            try:
                deadline = time.time() + 10
                acquired = False
                while time.time() < deadline:
                    time.sleep(0.5)
                    try:
                        from weathergpt_data.watches import check_lock
                        with check_lock(path):
                            pass
                    except SourceError:
                        acquired = True
                        break
                self.assertTrue(acquired, 'lock holder never took the lock')
                with self.assertRaises(SourceError):
                    check_due(store, object(), now=NOW)
            finally:
                holder.terminate()
                try:
                    holder.wait(timeout=15)
                except Exception:
                    holder.kill()


class CreateWatchRouteTests(unittest.TestCase):
    def test_create_validates_and_registers_without_guessing(self):
        import types
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            stub = types.SimpleNamespace(watch_store=lambda: WatchStore(path), clock=lambda: NOW)
            from weathergpt_data.workspace import Workspace
            result = Workspace.create_watch(stub, {'place': {'name': 'Kochi', 'latitude': 9.93,
                                                             'longitude': 76.27, 'state': 'Kerala'},
                                                   'hazard': 'heavy rain'})
            self.assertEqual(result['schema_version'], 'watch-create-v1')
            self.assertEqual(result['hazard'], 'heavy_rain')
            self.assertTrue(result['connected'])
            stored = WatchStore(path).get(result['id'])
            self.assertEqual(stored['place']['coordinates']['latitude'], 9.93)
            self.assertEqual(stored['place']['kind'], 'unknown')
            bad = [({} , 'missing place'),
                   ({'place': {'name': 'X', 'latitude': 1, 'longitude': 1}}, 'short name'),
                   ({'place': {'name': 'Kochi', 'latitude': 'north', 'longitude': 1}}, 'bad coords'),
                   ({'place': {'name': 'Kochi', 'latitude': 99, 'longitude': 1}}, 'bad range'),
                   ('not-a-dict', 'bad body')]
            for body, _ in bad:
                with self.assertRaises(SourceError):
                    Workspace.create_watch(stub, body)


class AckRouteTests(unittest.TestCase):
    def test_ack_route_validates_body_state_and_identity(self):
        import types
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            box = OutboxStore(path)
            stub = types.SimpleNamespace(watch_store=lambda: WatchStore(path), clock=lambda: NOW)
            from weathergpt_data.workspace import Workspace
            entry = box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
            box.set_state(entry['id'], 'sent', 'delivered', now=NOW)
            result = Workspace.ack_notification(stub, entry['id'], {'response': 'evacuating'})
            self.assertEqual(result['schema_version'], 'outbox-ack-v1')
            self.assertEqual(result['response'], 'evacuating')
            for body in ({}, {'response': 'panicking'}, {'response': ''}):
                with self.assertRaises(SourceError):
                    Workspace.ack_notification(stub, entry['id'], body)
            with self.assertRaises(SourceError):
                Workspace.ack_notification(stub, 'no-such-id', {'response': 'safe'})
            with self.assertRaises(SourceError):
                Workspace.ack_notification(stub, entry['id'], {'response': 'safe'})


class AckPathTests(unittest.TestCase):
    def test_parse_ack_path_accepts_only_the_ack_shape(self):
        from weathergpt_data.workspace import parse_ack_path
        self.assertEqual(parse_ack_path('/api/outbox/abc-123/ack'), 'abc-123')
        for bad in ('/api/outbox/abc-123', '/api/outbox/abc-123/ack/',
                    '/api/outbox//ack', '/api/outbox/abc-123/nack',
                    '/api/watches/abc-123/ack', '', None, '/api/outbox/abc-123/ack?x=1'):
            self.assertIsNone(parse_ack_path(bad))


class RobustnessTests(unittest.TestCase):
    def test_corrupt_rows_degrade_to_safe_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            store = WatchStore(path)
            box = OutboxStore(path)
            entry = box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {'a': 1}, now=NOW)
            db = sqlite3.connect(path)
            try:
                db.execute('UPDATE outbox SET payload=? WHERE id=?', ('{broken', entry['id']))
                db.execute("INSERT INTO watches (id,created_at,question,place,hazard,state,channels,consent_record)"
                           " VALUES ('w-bad','2026-09-16T00:00:00+00:00','q','{broken','heavy_rain',"
                           "'registered_check_on_request','[broken','{broken')")
                db.commit()
            finally:
                db.close()
            self.assertEqual(box.get(entry['id'])['payload'], {})
            bad = store.get('w-bad')
            self.assertEqual(bad['channels'], ['local_inbox'])
            self.assertEqual(bad['consent_record'], {})


class PayloadTests(unittest.TestCase):
    def test_payload_carries_official_facts_verbatim_with_limits(self):
        watch = {'id': 'w1', 'hazard': 'thunderstorm', 'place': {'name': 'Ahmedabad', 'state': 'Gujarat'},
                 'window_start': None, 'window_end': None}
        outcome = {'matched': True, 'reason': 'current_official_district_hazard_matches', 'detail': 'A match.'}
        payload = build_notification_payload(watch, outcome, [fact([4])], 'answered', now=NOW)
        self.assertEqual(payload['schema_version'], 'notification-v1')
        self.assertEqual(payload['facts'][0]['hazard_codes'], [4])
        self.assertEqual(payload['facts'][0]['source_id'], 'S15')
        self.assertTrue(any('all-clear' in line for line in payload['limitations']))
        self.assertEqual(payload['checked_at_utc'], '2026-09-16T00:00:00+00:00')


if __name__ == '__main__':
    unittest.main()
