"""Phase 2: claim/lease overlap safety, duplicate-safe enqueue, retry taxonomy.

Proves the crash-window and overlap gaps are closed without touching live
sources: everything runs against the real sqlite stores with synthetic rows.
"""
import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weathergpt_data.outbox import (OutboxStore, classify_error, dispatch_outbox,
                                    idempotency_key, retry_at_with_jitter,
                                    retry_delay, MAX_RETRIES)

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def fresh():
    tmp = tempfile.TemporaryDirectory()
    path = Path(tmp.name) / 'watches.sqlite'
    return tmp, OutboxStore(path), path


class ClaimTests(unittest.TestCase):
    def test_two_workers_never_own_the_same_row(self):
        tmp, box, path = fresh()
        try:
            entry = box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
            first = box.claim('worker-a', now=NOW)
            second = box.claim('worker-b', now=NOW)
            self.assertEqual([row['id'] for row in first], [entry['id']])
            self.assertEqual(second, [])
            self.assertEqual(box.get(entry['id'])['state'], 'claimed')
        finally:
            tmp.cleanup()

    def test_claimed_rows_are_invisible_to_due_until_reclaimed(self):
        tmp, box, path = fresh()
        try:
            entry = box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
            box.claim('worker-a', now=NOW)
            self.assertEqual(box.due(now=NOW), [])
            # Lease still live: reclaim does nothing.
            self.assertEqual(box.reclaim(now=NOW + timedelta(seconds=60))['requeued'], 0)
            # Lease expired (crashed worker): the row returns silently...
            self.assertEqual(box.reclaim(now=NOW + timedelta(seconds=3600))['requeued'], 1)
            row = box.get(entry['id'])
            self.assertEqual(row['state'], 'queued')
            self.assertIsNone(row['claimed_by'])
            # ...and dispatches normally with no duplicate ledger claim event.
            results = dispatch_outbox(path, now=NOW + timedelta(seconds=3600))
            self.assertEqual(results[0]['to'], 'sent')
            self.assertEqual([item['event'] for item in box.ledger(entry['id'])],
                             ['queued', 'sent'])
        finally:
            tmp.cleanup()

    def test_dispatch_sends_from_claim_without_changing_ledger_shape(self):
        tmp, box, path = fresh()
        try:
            row = box.enqueue('w1', 'c1', 'f1', 'local_inbox', {}, now=NOW)
            dispatch_outbox(path, now=NOW, send=lambda entry: (False, 'temporary failure'))
            result = dispatch_outbox(path, now=NOW + timedelta(minutes=2))
            self.assertEqual(result[0]['to'], 'sent')
            self.assertEqual([item['event'] for item in box.ledger(row['id'])],
                             ['queued', 'failed', 'queued', 'sent'])
        finally:
            tmp.cleanup()


class DedupeTests(unittest.TestCase):
    def test_same_logical_event_enqueues_once(self):
        tmp, box, path = fresh()
        try:
            first = box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {'n': 1}, now=NOW)
            second = box.enqueue('w1', 'c2', 'fp1', 'local_inbox', {'n': 2}, now=NOW)
            self.assertEqual(first['id'], second['id'])
            self.assertEqual(len(box.list()), 1)
        finally:
            tmp.cleanup()

    def test_changed_state_is_a_new_event(self):
        tmp, box, path = fresh()
        try:
            box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
            other = box.enqueue('w1', 'c1', 'fp2', 'local_inbox', {}, now=NOW)
            self.assertEqual(len(box.list()), 2)
            self.assertEqual(other['fingerprint_sha256'], 'fp2')
        finally:
            tmp.cleanup()

    def test_enqueue_changed_is_duplicate_safe_across_retries(self):
        tmp, box, path = fresh()
        try:
            from weathergpt_data.watches import WatchStore
            store = WatchStore(path)
            watch = store.create('rain', {'name': 'Patna'}, 'heavy_rain')
            first = box.enqueue_changed(watch['id'], 'c1', 'fp-x', ['local_inbox'],
                                        {'v': 1}, now=NOW)
            second = box.enqueue_changed(watch['id'], 'c2', 'fp-x', ['local_inbox'],
                                         {'v': 2}, now=NOW)
            self.assertEqual(first[0]['id'], second[0]['id'])
            self.assertEqual(len(box.list()), 1)
        finally:
            tmp.cleanup()

    def test_key_is_stable_and_channel_scoped(self):
        self.assertEqual(idempotency_key('w', 'fp', 'local_inbox'),
                         idempotency_key('w', 'fp', 'local_inbox'))
        self.assertNotEqual(idempotency_key('w', 'fp', 'local_inbox'),
                            idempotency_key('w', 'fp', 'web_push'))


class TaxonomyTests(unittest.TestCase):
    def test_purged_subscription_marks_gone_not_retried(self):
        tmp, box, path = fresh()
        try:
            entry = box.enqueue('w1', 'c1', 'fp1', 'web_push', {}, now=NOW)
            results = dispatch_outbox(path, now=NOW,
                                      send=lambda row: (False, 'Every push subscription for this watch expired and was retired'))
            self.assertEqual(results[0]['to'], 'gone')
            self.assertEqual(results[0]['error_class'], 'purged')
            self.assertEqual(box.get(entry['id'])['state'], 'gone')
            self.assertEqual(dispatch_outbox(path, now=NOW + timedelta(hours=1)), [])
        finally:
            tmp.cleanup()

    def test_retryable_uses_jittered_backoff_within_bounds(self):
        instant = retry_at_with_jitter(NOW, 1)
        from weathergpt_data.transport import parsed
        delta = (parsed(instant) - NOW).total_seconds()
        self.assertGreaterEqual(delta, retry_delay(1) * 0.8)
        self.assertLessEqual(delta, retry_delay(1) * 1.2)

    def test_over_age_row_goes_dead_instead_of_retrying_forever(self):
        tmp, box, path = fresh()
        try:
            entry = box.enqueue('w1', 'c1', 'fp1', 'sms', {}, now=NOW)
            late = NOW + timedelta(days=2)
            results = dispatch_outbox(path, now=late,
                                      send=lambda row: (False, 'temporary failure'))
            terminal = [row for row in results if row['to'] == 'dead']
            self.assertEqual(len(terminal), 1)
            self.assertIn('age', box.get(entry['id'])['last_error'])
        finally:
            tmp.cleanup()

    def test_classify_error_only_trusts_own_vocabulary(self):
        self.assertEqual(classify_error('Every push subscription for this watch expired and was retired'),
                         'purged')
        self.assertEqual(classify_error('Push failed: timeout'), 'retryable')
        self.assertEqual(classify_error('Sender raised RuntimeError: boom'), 'retryable')
        self.assertEqual(classify_error(None), 'retryable')

    def test_stats_reports_depth_for_health(self):
        tmp, box, path = fresh()
        try:
            box.enqueue('w1', 'c1', 'fp1', 'local_inbox', {}, now=NOW)
            stats = box.stats(now=NOW)
            self.assertEqual(stats['undispatched_depth'], 1)
            self.assertEqual(stats['counts']['queued'], 1)
        finally:
            tmp.cleanup()


if __name__ == '__main__':
    unittest.main()
