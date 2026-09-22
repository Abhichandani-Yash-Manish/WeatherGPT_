"""The resident refresh worker and the lease that makes a reader outrank it (docs/143).

The worker runs for as long as the machine is on, which changes what counts as a bug. A job
that runs twice a day and stops can waste a slot; a job that never stops can spin on one
district for the rest of the day, and did — fourteen consecutive attempts on Kadapa the first
time it was left running. Most of what is pinned here is about terminating.
"""
import importlib
import json
import tempfile
import time
import types
import unittest
from pathlib import Path

from weathergpt_data import refresh_lease


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_nobody_waiting_by_default(self):
        self.assertEqual(refresh_lease.waiting(self.root), [])

    def test_a_held_lease_is_seen_and_a_released_one_is_not(self):
        held = refresh_lease.hold(self.root, 'a question about Nashik')
        self.assertEqual(len(refresh_lease.waiting(self.root)), 1)
        held.release()
        self.assertEqual(refresh_lease.waiting(self.root), [])

    def test_two_questions_at_once_do_not_lose_each_others_lease(self):
        # A file per holder rather than a counter, so neither needs a lock and one releasing
        # cannot silence the other.
        first = refresh_lease.hold(self.root, 'one')
        second = refresh_lease.hold(self.root, 'two')
        self.assertEqual(len(refresh_lease.waiting(self.root)), 2)
        first.release()
        self.assertEqual(len(refresh_lease.waiting(self.root)), 1)
        second.release()
        self.assertEqual(refresh_lease.waiting(self.root), [])

    def test_a_holder_that_died_cannot_silence_the_worker_forever(self):
        """The reason the lease expires at all.

        A query killed mid-fetch leaves its file behind. Without an expiry the worker would
        read "somebody is waiting" from a process that no longer exists, and stand down until
        the machine was rebooted.
        """
        held = refresh_lease.hold(self.root, 'a query that crashed')
        stale = json.loads(held.path.read_text())
        stale['raised_at'] -= refresh_lease.LEASE_TTL_SECONDS + 60
        held.path.write_text(json.dumps(stale))
        self.assertEqual(refresh_lease.waiting(self.root), [])
        self.assertFalse(held.path.exists(), 'an expired lease is swept, not merely ignored')

    def test_the_context_manager_releases_on_an_exception(self):
        try:
            with refresh_lease.hold(self.root, 'a fetch that raises'):
                raise ValueError('the publisher refused')
        except ValueError:
            pass
        self.assertEqual(refresh_lease.waiting(self.root), [])

    def test_a_lease_that_cannot_be_written_never_breaks_the_query(self):
        # The reader's answer must not depend on the bookkeeping that makes a background job
        # polite. An unwritable path is a no-op, not an exception.
        held = refresh_lease.hold(Path('/nonexistent-volume/weathergpt'), 'x')
        self.assertIsNone(held.path)
        held.release()


class StandDownTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_it_returns_at_once_when_nobody_is_waiting(self):
        slept = []
        self.assertEqual(refresh_lease.stand_down(self.root, sleep=slept.append), 0.0)
        self.assertEqual(slept, [])

    def test_it_waits_while_a_reader_holds_and_proceeds_when_released(self):
        held = refresh_lease.hold(self.root, 'a reader mid-question')
        calls = []

        def sleep(seconds):
            calls.append(seconds)
            if len(calls) >= 3:
                held.release()

        refresh_lease.stand_down(self.root, patience=30, poll=0.01, sleep=sleep)
        self.assertEqual(len(calls), 3, 'it polled until the reader released, then went')

    def test_patience_is_bounded_so_a_busy_workspace_is_still_maintained(self):
        """A corpus that stops being maintained because the product is popular is the wrong failure."""
        refresh_lease.hold(self.root, 'a reader who never finishes')
        began = time.time()
        yielded = refresh_lease.stand_down(self.root, patience=0.3, poll=0.02)
        self.assertGreaterEqual(yielded, 0.3)
        self.assertLess(time.time() - began, 5, 'it proceeded rather than waiting forever')


def worker():
    return importlib.import_module('refresh_daemon')


class WorkerLoopTests(unittest.TestCase):
    """The loop, driven over a fake corpus so the publisher is never touched."""

    def setUp(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        self.module = worker()
        self.fetched = []
        self.slept = []
        self.heartbeats = []
        self.targets = [{'state': 'Punjab', 'district': d} for d in ('Ludhiana', 'Bhatinda', 'Patiala')]
        self.attempted = set()

    def install(self, outcome='fetched_new', raises=None):
        module = self.module
        original = {name: getattr(module, name) for name in
                    ('store_and_index', 'district_targets', 'head_state', 'sweep_queue',
                     'one_target', 'freshness', 'write_heartbeat', 'record_pass', 'DemandLedger')}

        def restore():
            for name, value in original.items():
                setattr(module, name, value)
        self.addCleanup(restore)

        setattr(module, 'store_and_index', lambda: (object(), types.SimpleNamespace(
            path=Path(tempfile.gettempdir()) / 'index.sqlite')))
        setattr(module, 'district_targets', lambda root: (self.targets, {}))
        setattr(module, 'head_state', lambda index: {})
        setattr(module, 'DemandLedger', lambda path: types.SimpleNamespace(counts=lambda: {}))
        setattr(module, 'freshness', lambda listed, held, now=None: {'listed': len(listed)})
        setattr(module, 'write_heartbeat', self.heartbeats.append)
        setattr(module, 'record_pass', lambda record: None)

        def queue(listed, held, counts, now=None, limit=None, **kwargs):
            outstanding = [{'target': t, 'bucket': 2, 'why': 'test', 'asked': 0, 'last_read_utc': None}
                           for t in listed if t['district'] not in self.attempted]
            return outstanding[:limit] if limit else outstanding
        setattr(module, 'sweep_queue', queue)

        def one(store, index, item, now=None):
            district = item['target']['district']
            self.fetched.append(district)
            self.attempted.add(district)
            if raises:
                raise raises
            return {'district': district, 'outcome': outcome, 'passages': 3}
        setattr(module, 'one_target', one)

    def test_it_works_through_the_queue_and_stops_when_everything_is_attempted(self):
        self.install()
        summary = self.module.run(once=True, pace=0, sleep=self.slept.append)
        self.assertEqual(self.fetched, ['Ludhiana', 'Bhatinda', 'Patiala'])
        self.assertEqual(summary['targets_this_run'], 3)
        self.assertEqual(summary['passages_this_run'], 9)

    def test_it_goes_idle_rather_than_spinning_once_the_queue_is_empty(self):
        self.install()
        self.attempted = {'Ludhiana', 'Bhatinda', 'Patiala'}
        summary = self.module.run(once=True, pace=0, sleep=self.slept.append)
        self.assertEqual(summary['targets_this_run'], 0)
        self.assertEqual(self.heartbeats[-1]['state'] if self.heartbeats else None, 'finished')
        self.assertTrue(any(beat.get('state') == 'idle' for beat in self.heartbeats))

    def test_the_limit_stops_it(self):
        self.install()
        summary = self.module.run(pace=0, limit=2, sleep=self.slept.append)
        self.assertEqual(summary['targets_this_run'], 2)

    def test_a_stop_signal_is_honoured_between_targets(self):
        """launchd sends SIGTERM on logout; dying mid-extraction would leave a false record."""
        self.install()
        stopping = types.SimpleNamespace(asked=False)
        module = self.module
        first = module.one_target

        def one(store, index, item, now=None):
            record = first(store, index, item, now=now)
            stopping.asked = True          # asked to stop while a target is in hand
            return record
        setattr(module, 'one_target', one)
        summary = module.run(pace=0, sleep=self.slept.append, stopping=stopping)
        self.assertEqual(summary['state'], 'stopped')
        self.assertEqual(summary['targets_this_run'], 1, 'it finished the target in hand, then stopped')

    def test_a_raising_target_backs_off_instead_of_becoming_a_busy_loop(self):
        # Resident mode, deliberately: with --once there is nothing to back off before, so the
        # loop exits instead of sleeping. It is the always-on case where "no network at all"
        # could otherwise turn into a spin.
        self.install(raises=OSError('the network is gone'))
        # A resident worker idles forever once the queue drains, which is the point of it, so
        # the test has to be the thing that stops: asked to stop the moment it settles into an
        # idle poll, which is exactly where a real SIGTERM would find it.
        stopping = types.SimpleNamespace(asked=False)

        def sleep(seconds):
            self.slept.append(seconds)
            if seconds == self.module.IDLE_POLL_SECONDS:
                stopping.asked = True
        summary = self.module.run(pace=0, sleep=sleep, stopping=stopping)
        self.assertEqual(summary['outcomes_this_run']['failed'], 3)
        self.assertEqual(self.slept.count(self.module.BACKOFF_SECONDS), 3)

    def test_the_resident_loop_idles_rather_than_exiting_when_there_is_nothing_to_do(self):
        # The difference between this worker and the twice-daily job: it does not finish.
        self.install()
        self.attempted = {'Ludhiana', 'Bhatinda', 'Patiala'}
        stopping = types.SimpleNamespace(asked=False)
        polls = []

        def sleep(seconds):
            polls.append(seconds)
            if len(polls) >= 3:
                stopping.asked = True
        self.module.run(pace=0, sleep=sleep, stopping=stopping)
        self.assertEqual(polls, [self.module.IDLE_POLL_SECONDS] * 3,
                         'it waits and looks again, rather than exiting')

    def test_once_exits_on_a_raising_target_rather_than_sleeping_first(self):
        self.install(raises=OSError('the network is gone'))
        summary = self.module.run(once=True, pace=0, sleep=self.slept.append)
        self.assertEqual(summary['outcomes_this_run']['failed'], 1)
        self.assertNotIn(self.module.BACKOFF_SECONDS, self.slept)

    def test_it_paces_itself_between_targets(self):
        self.install()
        self.module.run(pace=7, limit=2, sleep=self.slept.append)
        self.assertIn(7, self.slept, 'the publisher is somebody else’s public server')


class YieldOrderingTests(unittest.TestCase):
    """The reader is let through BEFORE the target is fetched, not after."""

    def test_one_target_stands_down_before_it_fetches(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
        module = worker()
        order = []
        original_stand, original_ingest = module.stand_down, module.ingest_district
        self.addCleanup(lambda: (setattr(module, 'stand_down', original_stand),
                                 setattr(module, 'ingest_district', original_ingest)))
        setattr(module, 'stand_down', lambda root: order.append('stood down') or 1.5)
        setattr(module, 'ingest_district', lambda *a, **k: order.append('fetched') or
                {'district': 'Ludhiana', 'outcome': 'fetched_new'})
        record = module.one_target(object(), object(),
                                   {'target': {'state': 'Punjab', 'district': 'Ludhiana'},
                                    'bucket': 2, 'why': 'test', 'asked': 0, 'last_read_utc': None})
        self.assertEqual(order, ['stood down', 'fetched'])
        self.assertEqual(record['yielded_to_reader_s'], 1.5,
                         'how long it waited for a reader is recorded on the target')


if __name__ == '__main__':
    unittest.main()
