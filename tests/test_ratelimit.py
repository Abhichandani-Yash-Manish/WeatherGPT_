"""Phase 4a: per-route abuse guards — limiter unit + route wiring."""
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from weathergpt_data import ratelimit
from weathergpt_data.ratelimit import RateLimited, RateLimiter
from weathergpt_data.watches import WatchStore

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


class LimiterTests(unittest.TestCase):
    def test_budget_trips_then_recovers_after_window(self):
        limiter = RateLimiter({'r': (2, 60.0)})
        self.assertTrue(limiter.allow('r', 'u', now=1000.0))
        self.assertTrue(limiter.allow('r', 'u', now=1001.0))
        with self.assertRaises(RateLimited):
            limiter.allow('r', 'u', now=1002.0)
        self.assertTrue(limiter.allow('r', 'u', now=1070.0))

    def test_identities_are_isolated_and_unknown_routes_pass(self):
        limiter = RateLimiter({'r': (1, 60.0)})
        limiter.allow('r', 'a', now=1000.0)
        self.assertTrue(limiter.allow('r', 'b', now=1000.0))
        self.assertTrue(limiter.allow('unconfigured', 'a', now=1000.0))

    def test_rate_limited_is_a_value_error_with_retry_hint(self):
        limiter = RateLimiter({'r': (1, 60.0)})
        limiter.allow('r', 'u', now=1000.0)
        try:
            limiter.allow('r', 'u', now=1001.0)
            self.fail('should have raised')
        except RateLimited as exc:
            self.assertIsInstance(exc, ValueError)
            self.assertIn('retry', str(exc))


class RouteWiringTests(unittest.TestCase):
    def test_create_route_trips_under_a_tight_budget(self):
        from weathergpt_data.workspace import Workspace
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            stub = types.SimpleNamespace(watch_store=lambda: WatchStore(path),
                                         clock=lambda: NOW)
            body = {'place': {'name': 'Kochi', 'latitude': 9.93, 'longitude': 76.27}}
            with patch.object(ratelimit._limiter, 'budgets', {'watches/create': (2, 60.0)}):
                Workspace.create_watch(stub, dict(body))
                Workspace.create_watch(stub, dict(body))
                with self.assertRaises(RateLimited):
                    Workspace.create_watch(stub, dict(body))

    def test_ack_route_trips_under_a_tight_budget(self):
        from datetime import datetime, timezone
        from weathergpt_data.outbox import OutboxStore
        from weathergpt_data.workspace import Workspace
        now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'watches.sqlite'
            box = OutboxStore(path)
            stub = types.SimpleNamespace(watch_store=lambda: WatchStore(path),
                                         clock=lambda: now)
            ids = []
            for index in range(3):
                entry = box.enqueue('w1', 'c%d' % index, 'fp%d' % index,
                                    'local_inbox', {}, now=now)
                box.set_state(entry['id'], 'sent', 'ok', now=now)
                ids.append(entry['id'])
            with patch.object(ratelimit._limiter, 'budgets', {'outbox/ack': (2, 60.0)}):
                Workspace.ack_notification(stub, ids[0], {'response': 'safe'})
                Workspace.ack_notification(stub, ids[1], {'response': 'seen'})
                with self.assertRaises(RateLimited):
                    Workspace.ack_notification(stub, ids[2], {'response': 'safe'})


if __name__ == '__main__':
    unittest.main()
