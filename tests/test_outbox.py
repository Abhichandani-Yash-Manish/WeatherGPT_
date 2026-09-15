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
from weathergpt_data.watches import WatchStore, check_watch, compute_fingerprint

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
        self.assertNotIn('payload', packet['notifications'][0])
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
            self.assertEqual(packet['schema_version'], 'watch-dma-v1')
            self.assertEqual(len(packet['districts']), 1)
            district = packet['districts'][0]
            self.assertEqual(district['place'], 'Ahmedabad, Gujarat')
            self.assertEqual(district['watches'], 1)
            self.assertEqual(district['notifications'], 1)
            self.assertEqual(district['acked'], 1)
            self.assertEqual(district['need_help'], 1)
            self.assertEqual(district['unacked'], 0)


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
