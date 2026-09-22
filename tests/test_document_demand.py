"""The demand ledger, the queue it orders, and the freshness it reports (docs/142).

These exist because the sweep looked healthy for a week while doing no work. Its exit code
was zero, its manifest recorded forty targets, and the corpus behind it had not moved since
14 September. Every assertion here is about the difference between those two things.
"""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weathergpt_data.document_demand import (BUCKETS, DemandLedger, freshness, head_state,
                                             region_key, sweep_queue)

NOW = datetime(2026, 9, 22, 6, 0, tzinfo=timezone.utc)
TARGETS = [{'state': 'Karnataka', 'district': 'Davanagere'},
           {'state': 'Punjab', 'district': 'Ludhiana'},
           {'state': 'Maharashtra', 'district': 'Nashik'},
           {'state': 'Bihar', 'district': 'Patna'}]


def when(days):
    return (NOW - timedelta(days=days)).isoformat()


class LedgerTests(unittest.TestCase):
    def ledger(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        return DemandLedger(Path(self.directory.name) / 'demand.sqlite')

    def test_a_request_is_counted_and_repeated_requests_accumulate(self):
        ledger = self.ledger()
        ledger.mark('Punjab', 'Ludhiana', NOW)
        ledger.mark('Punjab', 'Ludhiana', NOW)
        ledger.mark('Bihar', 'Patna', NOW)
        self.assertEqual(ledger.counts()[region_key('Punjab', 'Ludhiana')], 2)
        self.assertEqual(ledger.counts()[region_key('Bihar', 'Patna')], 1)

    def test_an_incomplete_request_is_not_recorded(self):
        ledger = self.ledger()
        self.assertIsNone(ledger.mark('', 'Ludhiana', NOW))
        self.assertIsNone(ledger.mark('Punjab', '', NOW))
        self.assertEqual(ledger.counts(), {})

    def test_the_district_alone_is_the_key_because_the_directory_refuses_a_repeat(self):
        # The publisher's own second selector step is keyed on the district alone, and the
        # two head namespaces in the index spell the state differently or not at all.
        self.assertEqual(region_key('Punjab', 'Ludhiana'), region_key('PUNJAB', 'ludhiana'))


class QueueTests(unittest.TestCase):
    def test_a_district_read_today_is_not_queued_again(self):
        held = {region_key('', t['district']): (when(0), 'ok') for t in TARGETS}
        self.assertEqual(sweep_queue(TARGETS, held, {}, now=NOW), [])

    def test_a_failure_today_is_not_retried_today(self):
        """Changed when the refresh became resident, and it matters more than it looks.

        This used to assert the opposite — that a failed read leaves the district queued —
        which is harmless under a job that runs twice and stops. A worker that runs for as
        long as the machine is on would spin on it: 71 of 698 districts last read with a
        failure, most of them held outcomes like `layout_unrecognised` that will fail again
        on the next byte-identical body. The worker would re-download those same PDFs for
        the rest of the day and never reach the districts it can actually read.

        An attempt is an attempt. `--retry-failed` is the switch that says try them again.
        """
        held = {region_key('', 'Ludhiana'): (when(0), 'failed')}
        queued = [item['target']['district'] for item in sweep_queue(TARGETS, held, {}, now=NOW)]
        self.assertNotIn('Ludhiana', queued)
        retried = [item['target']['district'] for item in
                   sweep_queue(TARGETS, held, {}, now=NOW, retry_failed=True)]
        self.assertEqual(retried, ['Ludhiana'])

    def test_a_failure_yesterday_is_queued_again_today(self):
        held = {region_key('', 'Ludhiana'): (when(1), 'failed')}
        queued = [item['target']['district'] for item in sweep_queue(TARGETS, held, {}, now=NOW)]
        self.assertIn('Ludhiana', queued)

    def test_everything_attempted_today_empties_the_queue(self):
        # What lets the resident worker go idle instead of spinning.
        held = {region_key('', t['district']): (when(0), 'failed' if i % 2 else 'ok')
                for i, t in enumerate(TARGETS)}
        self.assertEqual(sweep_queue(TARGETS, held, {}, now=NOW), [])

    def test_demand_outranks_staleness_and_staleness_outranks_directory_order(self):
        held = {region_key('', 'Davanagere'): (when(1), 'ok'),
                region_key('', 'Ludhiana'): (when(9), 'ok'),
                region_key('', 'Nashik'): (when(4), 'ok'),
                region_key('', 'Patna'): (when(2), 'ok')}
        # Nobody has asked: the longest unread goes first.
        plain = [item['target']['district'] for item in sweep_queue(TARGETS, held, {}, now=NOW)]
        self.assertEqual(plain, ['Ludhiana', 'Nashik', 'Patna', 'Davanagere'])
        # One reader asked about the district that was read most recently. It goes first
        # anyway, because somebody is waiting on it and nobody is waiting on the others.
        asked = {region_key('', 'Davanagere'): 1}
        with_demand = [item['target']['district'] for item in sweep_queue(TARGETS, held, asked, now=NOW)]
        self.assertEqual(with_demand[0], 'Davanagere')

    def test_a_district_nobody_holds_and_somebody_asked_for_comes_first_of_all(self):
        held = {region_key('', 'Ludhiana'): (when(9), 'ok')}
        asked = {region_key('', 'Ludhiana'): 5, region_key('', 'Patna'): 1}
        queue = sweep_queue(TARGETS, held, asked, now=NOW)
        self.assertEqual(queue[0]['target']['district'], 'Patna')
        self.assertEqual(queue[0]['bucket'], 0)
        self.assertEqual(queue[0]['why'], BUCKETS[0])
        self.assertEqual(queue[1]['target']['district'], 'Ludhiana')

    def test_more_readers_asking_moves_a_district_up(self):
        held = {region_key('', t['district']): (when(3), 'ok') for t in TARGETS}
        asked = {region_key('', 'Patna'): 9, region_key('', 'Nashik'): 2}
        queue = [item['target']['district'] for item in sweep_queue(TARGETS, held, asked, now=NOW)]
        self.assertEqual(queue[:2], ['Patna', 'Nashik'])

    def test_the_limit_bounds_the_run_without_losing_the_rest_of_the_order(self):
        held = {}
        self.assertEqual(len(sweep_queue(TARGETS, held, {}, now=NOW, limit=2)), 2)
        self.assertEqual(len(sweep_queue(TARGETS, held, {}, now=NOW)), 4)

    def test_retry_failed_takes_only_the_errors(self):
        held = {region_key('', 'Ludhiana'): (when(1), 'failed'),
                region_key('', 'Nashik'): (when(1), 'ok'),
                region_key('', 'Patna'): (when(1), 'ok'),
                region_key('', 'Davanagere'): (when(1), 'ok')}
        queue = [item['target']['district'] for item in
                 sweep_queue(TARGETS, held, {}, now=NOW, retry_failed=True)]
        self.assertEqual(queue, ['Ludhiana'])

    def test_the_queue_does_not_restart_at_the_alphabet_each_day(self):
        """The defect this module exists to close.

        The old sweep read its 'already done' set out of the DAY's manifest, so the first
        forty names in directory order were swept twice a day and the other 658 never. Here
        the record is the index, so yesterday's work counts and the queue moves on.
        """
        first = sweep_queue(TARGETS, {}, {}, now=NOW, limit=2)
        held = {region_key('', item['target']['district']): (when(0), 'ok') for item in first}
        second = [item['target']['district'] for item in sweep_queue(TARGETS, held, {}, now=NOW, limit=2)]
        self.assertFalse(set(second) & {item['target']['district'] for item in first})


class FreshnessTests(unittest.TestCase):
    def test_it_counts_the_corpus_rather_than_the_run(self):
        held = {region_key('', 'Ludhiana'): (when(0), 'ok'),
                region_key('', 'Nashik'): (when(8), 'ok'),
                region_key('', 'Patna'): (when(8), 'failed')}
        state = freshness(TARGETS, held, now=NOW)
        self.assertEqual(state['listed'], 4)
        self.assertEqual(state['read_today'], 1)
        self.assertEqual(state['never_held'], 1)          # Davanagere
        self.assertEqual(state['held_but_stale'], 2)
        self.assertEqual(state['last_read_failed'], 1)
        self.assertEqual(state['oldest_read_days'], 8)


class HeadNamespaceTests(unittest.TestCase):
    """The index keeps district heads under two different keys; both mean 'was read'."""

    def index(self):
        from weathergpt_data.bulletin_index import BulletinIndex
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return BulletinIndex(Path(directory.name) / 'index.sqlite')

    def write(self, index, region, checked_at, status='ok'):
        with index.connection() as db:
            db.execute('INSERT OR REPLACE INTO heads VALUES (?,?,?,?,?)',
                       (region, 'sha', checked_at, status, ''))

    def test_both_namespaces_are_read_and_the_newer_wins(self):
        index = self.index()
        self.write(index, 'document|district_agromet|Ludhiana', when(5))
        self.write(index, 'punjab|ludhiana', when(1))
        self.assertEqual(head_state(index)[region_key('', 'Ludhiana')][0], when(1))

    def test_the_sweeps_own_namespace_is_read_when_it_is_the_only_one(self):
        index = self.index()
        self.write(index, 'document|district_agromet|Nashik', when(3))
        self.assertEqual(head_state(index)[region_key('', 'Nashik')][0], when(3))

    def test_another_family_is_not_mistaken_for_a_district(self):
        index = self.index()
        self.write(index, 'document|coastal_bulletin|-', when(0))
        self.assertNotIn('-', head_state(index))


if __name__ == '__main__':
    unittest.main()
