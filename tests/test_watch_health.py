"""Phase 3: supervised monitoring — heartbeat, freshness, overlap skip, health."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from weathergpt_data.watches import (WatchStore, heartbeat_status, read_heartbeat,
                                     record_heartbeat)
from weathergpt_data.workspace import Workspace

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def fact(codes):
    return {'parameter': 'official_district_warning', 'label': 'Day 1 · 16 Sep',
            'value': 'orange', 'start': '2026-09-16T00:00:00+05:30',
            'end': '2026-09-17T00:00:00+05:30', 'hazard_codes': list(codes),
            'quiet': False, 'source_id': 'S15'}


def stub_workspace(tmp):
    workspace = Workspace.__new__(Workspace)
    workspace.service = SimpleNamespace(ingestion_database=Path(tmp) / 'ing.sqlite')
    workspace.clock = lambda: NOW
    workspace.conversation = object()
    return workspace


class HeartbeatTests(unittest.TestCase):
    def test_round_trip_and_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            self.assertIsNone(read_heartbeat(path))
            self.assertTrue(record_heartbeat(path, {'trigger': 'daemon', 'cycle': 3}, now=NOW))
            record = read_heartbeat(path)
            self.assertEqual(record['schema_version'], 'watch-heartbeat-v1')
            self.assertEqual(record['tick_at_utc'], '2026-09-16T12:00:00+00:00')
            self.assertEqual(record['cycle'], 3)

    def test_unreadable_heartbeat_reads_as_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            heartbeat = path.parent / 'watch-heartbeat.json'
            heartbeat.parent.mkdir(parents=True, exist_ok=True)
            heartbeat.write_text('not json{{{', encoding='utf-8')
            self.assertIsNone(read_heartbeat(path))

    def test_freshness_windows(self):
        tick = {'tick_at_utc': '2026-09-16T12:00:00+00:00', 'stale_after_seconds': 1860}
        fresh = heartbeat_status(tick, now=NOW + timedelta(minutes=30))
        self.assertTrue(fresh['fresh'])
        stale = heartbeat_status(tick, now=NOW + timedelta(hours=2))
        self.assertFalse(stale['fresh'])
        self.assertIn('older', stale['reason'])
        absent = heartbeat_status(None, now=NOW)
        self.assertFalse(absent['fresh'])
        broken = heartbeat_status({'tick_at_utc': 'yesterday-ish'}, now=NOW)
        self.assertFalse(broken['fresh'])


class DaemonCycleTests(unittest.TestCase):
    def run_cycle(self, facts, workspace=None, store=None):
        from scripts.watch_daemon import run_cycle
        if workspace is None:
            raise AssertionError('pass an explicit stub workspace (owns its temp dir)')
        if store is None:
            store = WatchStore(workspace.service.ingestion_database.parent / 'watches.sqlite')
        facts_box = {'facts': list(facts)}

        def fake(engine, packet, plan, task, **kw):
            return {**packet, 'facts': list(facts_box['facts']), 'status': 'answered',
                    'trace': {'tools': [], 'generation': None}}

        with patch('weathergpt_data.warning_tools.execute_warning', side_effect=fake):
            summary = run_cycle(workspace, store, lambda entry: (True, 'ok'),
                                cycle=1, interval=900, owner='test-owner', now=NOW)
        return summary, store, facts_box

    def test_baseline_then_change_cycles_report_counts_and_tick(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            workspace = stub_workspace(tmp.name)
            store = WatchStore(Path(tmp.name) / 'watches.sqlite')
            store.create('rain', {'name': 'Patna'}, 'heavy_rain')
            first, store, box = self.run_cycle([fact([1])], workspace, store)
            self.assertEqual((first['checked'], first['notifications_enqueued'],
                              first['dispatched'], first['skipped']), (1, 0, 0, False))
            box['facts'] = [fact([16])]
            second, store, _ = self.run_cycle([fact([16])], workspace, store)
            # Baseline was set by the first cycle: change -> enqueue + dispatch.
            self.assertEqual((second['checked'], second['notifications_enqueued'],
                              second['dispatched']), (1, 1, 1))
            tick = read_heartbeat(store.path)
            self.assertEqual(tick['trigger'], 'daemon')
            self.assertEqual(tick['interval_seconds'], 900)
            self.assertEqual(tick['stale_after_seconds'], 1860)
        finally:
            tmp.cleanup()

    def test_overlapping_run_is_skipped_not_crashed(self):
        from scripts.watch_daemon import run_cycle
        from weathergpt_data.transport import SourceError
        with tempfile.TemporaryDirectory() as tmp:
            workspace = stub_workspace(tmp)
            store = WatchStore(Path(tmp) / 'watches.sqlite')
            with patch('scripts.watch_daemon.check_due',
                       side_effect=SourceError('Another watch check is already running')):
                summary = run_cycle(workspace, store, lambda entry: (True, 'ok'),
                                    cycle=7, interval=900, owner='test-owner', now=NOW)
            self.assertTrue(summary['skipped'])
            self.assertIn('Overlapping', summary['last_error'])
            self.assertEqual(read_heartbeat(store.path)['cycle'], 7)

    def test_bad_cycle_is_recorded_and_heartbeat_still_written(self):
        from scripts.watch_daemon import run_cycle
        with tempfile.TemporaryDirectory() as tmp:
            workspace = stub_workspace(tmp)
            store = WatchStore(Path(tmp) / 'watches.sqlite')
            with patch('scripts.watch_daemon.check_due', side_effect=RuntimeError('boom')):
                summary = run_cycle(workspace, store, lambda entry: (True, 'ok'),
                                    cycle=2, interval=900, owner='test-owner', now=NOW)
            self.assertIn('boom', summary['last_error'])
            self.assertFalse(summary['skipped'])
            self.assertIsNotNone(read_heartbeat(store.path))


class HealthTests(unittest.TestCase):
    def test_health_without_heartbeat_is_manual_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            health = Workspace.watch_health(stub_workspace(tmp))
            self.assertEqual(health['schema_version'], 'watch-health-v1')
            self.assertEqual(health['mode'], 'manual-only')
            self.assertFalse(health['tick']['fresh'])
            self.assertEqual(health['watches'], {'total': 0, 'active': 0, 'expired': 0})
            self.assertIn('outbox', health)

    def test_health_with_fresh_daemon_tick_is_supervised(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = stub_workspace(tmp)
            store = WatchStore(Path(tmp) / 'watches.sqlite')
            store.create('rain', {'name': 'Patna'}, 'heavy_rain')
            record_heartbeat(store.path, {'trigger': 'daemon', 'interval_seconds': 900,
                                          'stale_after_seconds': 1860}, now=NOW)
            health = Workspace.watch_health(workspace)
            self.assertEqual(health['mode'], 'foreground-supervised')
            self.assertTrue(health['tick']['fresh'])
            self.assertEqual(health['watches']['active'], 1)
            self.assertIn('undispatched_depth', health['outbox'])


if __name__ == '__main__':
    unittest.main()
