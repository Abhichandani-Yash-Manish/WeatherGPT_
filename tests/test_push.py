"""Web push: VAPID keys, subscriptions, sending, and 410 retirement.

Keys generate once and reload deterministically. Subscriptions validate before
storage and retire on expiry or on a 410 Gone from the push service. Sending
never raises: per-endpoint outcomes return to the caller for ledger recording.
"""
import base64
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from weathergpt_data.push import (PushStore, channel_sender, public_b64url, push_payload,
                                  send_push, validate_subscription, vapid_keypair)
from weathergpt_data.transport import SourceError
from weathergpt_data.watches import WatchStore

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)
P256DH = base64.urlsafe_b64encode(b'0' * 65).rstrip(b'=').decode()
AUTH = base64.urlsafe_b64encode(b'1' * 16).rstrip(b'=').decode()
ENDPOINT = 'https://push.example.org/endpoint/abc123'


def make_entry(watch_id='w1'):
    return {'id': 'o1', 'watch_id': watch_id, 'channel': 'web_push',
            'payload': {'watch_id': watch_id, 'hazard': 'thunderstorm',
                        'place': {'name': 'Ahmedabad'}, 'matched': True,
                        'facts': [{'label': 'Day 1', 'value': 'yellow'}],
                        'checked_at_utc': '2026-09-16T00:00:00+00:00'}}


class VapidTests(unittest.TestCase):
    def test_keys_generate_once_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            key_path = Path(tmp) / 'push-vapid.json'
            vapid, public = vapid_keypair(key_path)
            self.assertEqual(len(public), 87)
            self.assertEqual(public_b64url(vapid), public)
            second, public_again = vapid_keypair(key_path)
            self.assertEqual(public_again, public)
            self.assertEqual(public_b64url(second), public)

    def test_a_tampered_public_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            key_path = Path(tmp) / 'push-vapid.json'
            _, public = vapid_keypair(key_path)
            record = json.loads(key_path.read_text(encoding='utf-8'))
            record['public_b64url'] = 'A' * 87
            key_path.write_text(json.dumps(record), encoding='utf-8')
            with self.assertRaises(SourceError):
                vapid_keypair(key_path)

    def test_an_unreadable_key_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            key_path = Path(tmp) / 'push-vapid.json'
            key_path.write_text('not json', encoding='utf-8')
            with self.assertRaises(SourceError):
                vapid_keypair(key_path)


class SubscriptionValidationTests(unittest.TestCase):
    def test_a_well_formed_subscription_passes(self):
        validate_subscription(ENDPOINT, P256DH, AUTH)

    def test_non_https_or_missing_parts_fail(self):
        for endpoint in ['http://push.example.org/x', 'not-a-url', '', None]:
            with self.assertRaises(SourceError):
                validate_subscription(endpoint, P256DH, AUTH)
        with self.assertRaises(SourceError):
            validate_subscription(ENDPOINT, '', AUTH)
        with self.assertRaises(SourceError):
            validate_subscription(ENDPOINT, P256DH, '!!!not-base64!!!')


class PushStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.watches = WatchStore(self.path)
        self.store = PushStore(self.path)
        self.watch = self.watches.create('Notify me if a thunderstorm warning is issued for Ahmedabad tomorrow',
                                         {'name': 'Ahmedabad'}, 'thunderstorm')

    def tearDown(self):
        self.tmp.cleanup()

    def test_subscribe_list_unsubscribe(self):
        entry = self.store.subscribe(ENDPOINT, P256DH, AUTH, watch_id=self.watch['id'], now=NOW)
        self.assertEqual(entry['state'], 'active')
        self.assertEqual(len(self.store.list(state='active')), 1)
        result = self.store.unsubscribe(ENDPOINT)
        self.assertEqual(result['revoked'], 1)
        self.assertEqual(self.store.list(state='active'), [])
        with self.assertRaises(SourceError):
            self.store.unsubscribe(ENDPOINT)

    def test_subscribe_to_an_unknown_watch_raises(self):
        with self.assertRaises(SourceError):
            self.store.subscribe(ENDPOINT, P256DH, AUTH, watch_id='no-such-watch', now=NOW)

    def test_unbound_subscriptions_serve_every_watch(self):
        self.store.subscribe(ENDPOINT, P256DH, AUTH, now=NOW)
        self.store.subscribe('https://push.example.org/other', P256DH, AUTH, watch_id=self.watch['id'], now=NOW)
        targets = self.store.active_for_watch(self.watch['id'])
        self.assertEqual(len(targets), 2)
        others = self.store.active_for_watch('another-watch')
        self.assertEqual(len(others), 1)
        self.assertIsNone(others[0].get('watch_id'))

    def test_purge_expired_retires_only_past_due_rows(self):
        self.store.subscribe(ENDPOINT, P256DH, AUTH, expires_at='2026-09-15T00:00:00+00:00', now=NOW)
        self.store.subscribe('https://push.example.org/fresh', P256DH, AUTH,
                             expires_at='2026-09-17T00:00:00+00:00', now=NOW)
        result = self.store.purge_expired(now=NOW)
        self.assertEqual(result['retired'], 1)
        self.assertEqual(len(self.store.list(state='expired')), 1)
        self.assertEqual(len(self.store.list(state='active')), 1)

    def test_unknown_subscription_states_raise(self):
        with self.assertRaises(SourceError):
            self.store.set_state('no-such-id', 'bogus')

    def test_repeat_subscribe_is_idempotent(self):
        first = self.store.subscribe(ENDPOINT, P256DH, AUTH, watch_id=self.watch['id'], now=NOW)
        second = self.store.subscribe(ENDPOINT, P256DH, AUTH, watch_id=self.watch['id'], now=NOW)
        self.assertEqual(first['id'], second['id'])
        self.assertTrue(second.get('duplicate'))
        self.assertEqual(len(self.store.list(state='active')), 1)

    def test_bound_subscribe_adds_channel_and_consent(self):
        self.store.subscribe(ENDPOINT, P256DH, AUTH, watch_id=self.watch['id'], now=NOW)
        watch = self.watches.get(self.watch['id'])
        self.assertIn('web_push', watch['channels'])
        self.assertEqual(watch['consent_record']['web_push']['source'], 'browser_push_grant')

    def test_unbound_subscribe_changes_no_watch(self):
        self.store.subscribe(ENDPOINT, P256DH, AUTH, now=NOW)
        watch = self.watches.get(self.watch['id'])
        self.assertEqual(watch['channels'], ['local_inbox'])

    def test_unsubscribe_removes_channel_and_consent(self):
        self.store.subscribe(ENDPOINT, P256DH, AUTH, watch_id=self.watch['id'], now=NOW)
        result = self.store.unsubscribe(ENDPOINT, now=NOW)
        self.assertEqual(result['channels_removed'], [self.watch['id']])
        watch = self.watches.get(self.watch['id'])
        self.assertEqual(watch['channels'], ['local_inbox'])
        self.assertNotIn('web_push', watch['consent_record'])


class DeliverableChannelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.watches = WatchStore(self.path)
        self.store = PushStore(self.path)
        self.watch = self.watches.create('Notify me if a thunderstorm warning is issued for Ahmedabad tomorrow',
                                         {'name': 'Ahmedabad'}, 'thunderstorm')

    def tearDown(self):
        self.tmp.cleanup()

    def test_local_inbox_is_always_deliverable(self):
        from weathergpt_data.push import deliverable_channels
        ok, skipped = deliverable_channels(self.path, self.watches.get(self.watch['id']), now=NOW)
        self.assertEqual(ok, ['local_inbox'])
        self.assertEqual(skipped, [])

    def test_push_needs_consent_and_subscription(self):
        from weathergpt_data.push import deliverable_channels
        self.watches.set_channels(self.watch['id'], ['local_inbox', 'web_push'],
                                  consent_source='browser_push_grant', now=NOW)
        ok, skipped = deliverable_channels(self.path, self.watches.get(self.watch['id']), now=NOW)
        self.assertEqual(ok, ['local_inbox'])
        self.assertEqual(skipped[0]['reason'], 'no active push subscription')
        self.store.subscribe(ENDPOINT, P256DH, AUTH, watch_id=self.watch['id'], now=NOW)
        ok, skipped = deliverable_channels(self.path, self.watches.get(self.watch['id']), now=NOW)
        self.assertEqual(ok, ['local_inbox', 'web_push'])
        self.assertEqual(skipped, [])

    def test_channel_without_consent_is_skipped(self):
        from weathergpt_data.push import deliverable_channels
        watch = self.watches.get(self.watch['id'])
        watch['channels'] = ['local_inbox', 'web_push']
        watch['consent_record'] = {}
        ok, skipped = deliverable_channels(self.path, watch, now=NOW)
        self.assertEqual(ok, ['local_inbox'])
        self.assertEqual(skipped[0]['reason'], 'no recorded push consent')


class TtlTests(unittest.TestCase):
    def test_ttl_follows_the_window_end_with_bounds(self):
        from datetime import timedelta
        from weathergpt_data.push import push_ttl, PUSH_TTL_SECONDS
        soon = {'payload': {'window': {'ends': (NOW + timedelta(minutes=10)).isoformat()}}}
        self.assertEqual(push_ttl(soon, now=NOW), 600)
        far = {'payload': {'window': {'ends': (NOW + timedelta(days=30)).isoformat()}}}
        self.assertEqual(push_ttl(far, now=NOW), 86400)
        past = {'payload': {'window': {'ends': (NOW - timedelta(hours=1)).isoformat()}}}
        self.assertEqual(push_ttl(past, now=NOW), PUSH_TTL_SECONDS)
        self.assertEqual(push_ttl({'payload': {}}, now=NOW), PUSH_TTL_SECONDS)


class SubscribeRouteTests(unittest.TestCase):
    def setUp(self):
        import types
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.watches = WatchStore(self.path)
        self.store = PushStore(self.path)
        self.watch = self.watches.create('Notify me if a thunderstorm warning is issued for Ahmedabad tomorrow',
                                         {'name': 'Ahmedabad'}, 'thunderstorm')
        self.stub = types.SimpleNamespace(watch_store=lambda: WatchStore(self.path), clock=lambda: NOW)

    def tearDown(self):
        self.tmp.cleanup()

    def test_subscribe_route_binds_and_reports(self):
        from weathergpt_data.workspace import Workspace
        result = Workspace.push_subscribe(self.stub, {'endpoint': ENDPOINT,
                                                      'keys': {'p256dh': P256DH, 'auth': AUTH},
                                                      'watch_id': self.watch['id']})
        self.assertEqual(result['schema_version'], 'push-subscription-v1')
        self.assertEqual(result['watch_id'], self.watch['id'])
        self.assertFalse(result['duplicate'])
        self.assertIn('web_push', WatchStore(self.path).get(self.watch['id'])['channels'])
        again = Workspace.push_subscribe(self.stub, {'endpoint': ENDPOINT,
                                                     'keys': {'p256dh': P256DH, 'auth': AUTH},
                                                     'watch_id': self.watch['id']})
        self.assertTrue(again['duplicate'])
        for body in ({}, {'endpoint': 'http://bad/x', 'keys': {}},
                     {'endpoint': ENDPOINT, 'keys': {'p256dh': P256DH, 'auth': AUTH},
                      'watch_id': 'no-such-watch'}):
            with self.assertRaises(SourceError):
                Workspace.push_subscribe(self.stub, body)

    def test_unsubscribe_route_revokes_and_unlinks(self):
        from weathergpt_data.workspace import Workspace
        Workspace.push_subscribe(self.stub, {'endpoint': ENDPOINT,
                                             'keys': {'p256dh': P256DH, 'auth': AUTH},
                                             'watch_id': self.watch['id']})
        result = Workspace.push_unsubscribe(self.stub, {'endpoint': ENDPOINT})
        self.assertEqual(result['channels_removed'], [self.watch['id']])
        with self.assertRaises(SourceError):
            Workspace.push_unsubscribe(self.stub, {})
        with self.assertRaises(SourceError):
            Workspace.push_unsubscribe(self.stub, {'endpoint': ENDPOINT})


class PayloadTests(unittest.TestCase):
    def test_payload_carries_official_facts_verbatim(self):
        message = push_payload(make_entry())
        self.assertIn('thunderstorm', message['title'])
        self.assertIn('Ahmedabad', message['body'])
        self.assertIn('Day 1', message['body'])
        self.assertEqual(message['watch_id'], 'w1')
        self.assertEqual(message['outbox_id'], 'o1')
        self.assertLessEqual(len(json.dumps(message)), 4096)


class SendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'watches.sqlite'
        self.watches = WatchStore(self.path)
        self.store = PushStore(self.path)
        self.watch = self.watches.create('Notify me if a thunderstorm warning is issued for Ahmedabad tomorrow',
                                         {'name': 'Ahmedabad'}, 'thunderstorm')
        self.sub = self.store.subscribe(ENDPOINT, P256DH, AUTH, watch_id=self.watch['id'], now=NOW)
        key_path = Path(self.tmp.name) / 'push-vapid.json'
        self.vapid, _ = vapid_keypair(key_path)
        self.key_path = key_path

    def tearDown(self):
        self.tmp.cleanup()

    def test_successful_push_reports_delivery(self):
        from pywebpush import WebPushException  # noqa: F401
        with patch('pywebpush.webpush', return_value=None) as sender:
            outcome = send_push(make_entry(self.watch['id']), self.vapid, [self.sub])
        self.assertEqual(outcome['delivered'], [self.sub['id']])
        self.assertEqual(outcome['purged'], [])
        self.assertEqual(outcome['errors'], [])
        self.assertTrue(sender.called)

    def test_gone_endpoints_are_flagged_for_retirement(self):
        from pywebpush import WebPushException
        gone = WebPushException('gone', response=SimpleNamespace(status_code=410, text='gone'))
        with patch('pywebpush.webpush', side_effect=gone):
            outcome = send_push(make_entry(self.watch['id']), self.vapid, [self.sub])
        self.assertEqual(outcome['delivered'], [])
        self.assertEqual(outcome['purged'], [self.sub['id']])

    def test_transport_errors_return_without_raising(self):
        from pywebpush import WebPushException
        failure = WebPushException('boom', response=SimpleNamespace(status_code=503, text='busy'))
        with patch('pywebpush.webpush', side_effect=failure):
            outcome = send_push(make_entry(self.watch['id']), self.vapid, [self.sub])
        self.assertEqual(outcome['delivered'], [])
        self.assertEqual(outcome['purged'], [])
        self.assertEqual(len(outcome['errors']), 1)
        with patch('pywebpush.webpush', side_effect=RuntimeError('offline')):
            outcome = send_push(make_entry(self.watch['id']), self.vapid, [self.sub])
        self.assertEqual(len(outcome['errors']), 1)

    def test_channel_sender_delivers_local_inbox_and_push(self):
        from weathergpt_data.outbox import default_sender
        send = channel_sender(self.key_path, self.path)
        ok, _ = send({'channel': 'local_inbox'})
        self.assertTrue(ok)
        self.assertEqual(default_sender({'channel': 'local_inbox'})[0], True)
        ok, detail = send({'channel': 'sms'})
        self.assertFalse(ok)
        self.assertIn('not connected', detail)
        with patch('pywebpush.webpush', return_value=None):
            ok, detail = send(make_entry(self.watch['id']))
        self.assertTrue(ok)
        self.assertIn('1 subscription', detail)

    def test_channel_sender_with_no_subscription_fails_closed(self):
        self.store.unsubscribe(ENDPOINT)
        send = channel_sender(self.key_path, self.path)
        ok, detail = send(make_entry(self.watch['id']))
        self.assertFalse(ok)
        self.assertIn('No active push subscription', detail)


if __name__ == '__main__':
    unittest.main()
