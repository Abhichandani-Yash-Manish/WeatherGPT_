"""Feature 4 end-to-end lifecycle: register, warn, duplicate, update, withdraw, expire.

One watch walks the whole dissemination path with the warning tool mocked at
the boundary: baseline stores no notification, a new official state notifies
exactly once, a repeated state notifies nothing, an updated state notifies
once more, a withdrawn warning notifies (never as an all-clear), expiry ends
the watch silently, and a failing channel retries boundedly to dead.
"""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from weathergpt_data.outbox import (OutboxStore, acknowledge, dispatch_outbox,
                                    escalate_unacked)
from weathergpt_data.watches import WatchStore, check_due, check_watch

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def fact(codes, quiet=False, fact_id='e1-f1'):
    return {'id': fact_id, 'parameter': 'official_district_warning', 'label': 'Day 1',
            'value': 'yellow', 'unit': 'IMD district warning colour', 'hazard_codes': codes,
            'quiet': quiet, 'start': '2026-09-16T00:00:00+05:30', 'end': '2026-09-17T00:00:00+05:30',
            'source_id': 'S15'}


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.store = WatchStore(self.path)
        self.box = OutboxStore(self.path)
        self.facts = [fact([1], quiet=True)]
        self.patch = patch('weathergpt_data.warning_tools.execute_warning',
                           side_effect=lambda engine, packet, plan, task, **kw: {
                               **packet, 'facts': list(self.facts), 'status': 'answered'})
        self.patch.start()
        self.watch = self.store.create('Notify me if a heavy rain warning is issued for Ahmedabad tomorrow',
                                       {'name': 'Ahmedabad, Gujarat',
                                        'coordinates': {'latitude': 23.0, 'longitude': 72.5}},
                                       'heavy_rain', window_start='2026-09-16T00:00:00+05:30',
                                       window_end='2026-09-20T00:00:00+05:30')

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def check(self):
        return check_watch(self.store, object(), self.store.get(self.watch['id']), now=NOW)

    def test_full_lifecycle_new_duplicate_updated_withdrawn_expired(self):
        # 1. Registration check: quiet baseline, no notification.
        first = self.check()
        self.assertEqual(first['state'], 'checked_no_match')
        self.assertIsNone(first['notification'])
        self.assertEqual(self.box.list(), [])
        # 2. New warning: exactly one notification, dispatched to sent.
        self.facts = [fact([16])]
        warned = self.check()
        self.assertEqual(warned['state'], 'matched')
        self.assertIsNotNone(warned['notification'])
        dispatched = dispatch_outbox(self.path, now=NOW)
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0]['to'], 'sent')
        # 3. Duplicate state: nothing new enqueued, nothing dispatched.
        repeated = self.check()
        self.assertIsNone(repeated['notification'])
        self.assertEqual(len(self.box.list()), 1)
        self.assertEqual(dispatch_outbox(self.path, now=NOW), [])
        # 4. Updated state (new hazard code): exactly one more notification.
        self.facts = [fact([16]), fact([17], fact_id='e1-f2')]
        updated = self.check()
        self.assertIsNotNone(updated['notification'])
        self.assertNotEqual(updated['notification'], warned['notification'])
        self.assertEqual(len(self.box.list()), 2)
        # 5. Withdrawn warning (quiet again): notifies as a change, never an all-clear.
        self.facts = [fact([1], quiet=True)]
        withdrawn = self.check()
        self.assertEqual(withdrawn['state'], 'checked_no_match')
        self.assertIsNotNone(withdrawn['notification'])
        payload = self.box.get(withdrawn['notification'])['payload']
        self.assertFalse(payload['matched'])
        self.assertTrue(any('all-clear' in line for line in payload['limitations']))
        # 6. Owner acknowledges the latest notification.
        dispatch_outbox(self.path, now=NOW)
        latest = self.box.get(withdrawn['notification'])
        self.assertEqual(latest['state'], 'sent')
        acknowledge(self.path, latest['id'], 'safe', now=NOW)
        self.assertEqual(self.box.get(latest['id'])['state'], 'acked')
        # 7. Expiry ends the watch with no further notification.
        from datetime import timedelta
        late = NOW + timedelta(days=10)
        expired = check_watch(self.store, object(), self.store.get(self.watch['id']), now=late)
        self.assertEqual(expired['state'], 'expired')
        self.assertNotIn('notification', expired)
        self.assertEqual(len(self.box.list()), 3)

    def test_one_check_run_shares_one_correlation_id(self):
        second = self.store.create('Notify me if a thunderstorm warning is issued for Patna tomorrow',
                                   {'name': 'Patna, Bihar'}, 'thunderstorm',
                                   window_start='2026-09-16T00:00:00+05:30',
                                   window_end='2026-09-20T00:00:00+05:30')
        self.facts = [fact([4])]
        check_due(self.store, object(), now=NOW)
        self.facts = [fact([16])]
        check_due(self.store, object(), now=NOW)
        rows = self.box.list()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['correlation_id'], rows[1]['correlation_id'])

    def test_failing_channel_retries_bounded_and_dies(self):
        from datetime import timedelta
        entry = self.box.enqueue(self.watch['id'], 'corr-fail', 'fp', 'sms', {}, now=NOW)
        moment = NOW
        states = []
        for _ in range(6):
            for row in dispatch_outbox(self.path, now=moment):
                states.append(row['to'])
            moment = moment + timedelta(hours=1)
        self.assertIn('failed', states)
        self.assertEqual(states[-1], 'dead')
        self.assertEqual(self.box.get(entry['id'])['state'], 'dead')
        self.assertEqual(dispatch_outbox(self.path, now=moment), [])

    def test_escalation_fires_only_for_unacked_rows(self):
        from datetime import timedelta
        self.check()
        self.facts = [fact([16])]
        warned = self.check()
        self.assertIsNotNone(warned['notification'])
        dispatch_outbox(self.path, now=NOW)
        late = NOW + timedelta(hours=2)
        created = escalate_unacked(self.path, now=late)
        self.assertEqual(len(created), 1)
        acknowledge(self.path, warned['notification'], 'seen', now=late)
        dispatch_outbox(self.path, now=late)
        # The original stays quiet; its unacked follow-up escalates once more,
        # then the depth bound stops the chain.
        second = escalate_unacked(self.path, now=late + timedelta(hours=2))
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]['depth'], 2)
        dispatch_outbox(self.path, now=late + timedelta(hours=2))
        self.assertEqual(escalate_unacked(self.path, now=late + timedelta(hours=4)), [])


if __name__ == '__main__':
    unittest.main()
