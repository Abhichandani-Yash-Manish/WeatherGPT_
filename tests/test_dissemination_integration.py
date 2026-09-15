"""Synthetic lifecycle across real loopback HTTP and recovered delivery failures.

No provider warning or push-service request is made by these checks.
"""
import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from test_feature4_e2e import NOW, fact
from weathergpt_data.outbox import OutboxStore, dispatch_outbox
from weathergpt_data.watches import WatchStore
from weathergpt_data.workspace import Workspace, make_server


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'watches.sqlite'

    def test_retry_success_is_recorded_and_never_dispatched_again(self):
        box = OutboxStore(self.path)
        row = box.enqueue('w1', 'c1', 'f1', 'local_inbox', {}, now=NOW)
        dispatch_outbox(self.path, now=NOW, send=lambda entry: (False, 'temporary failure'))
        result = dispatch_outbox(self.path, now=NOW + timedelta(minutes=2))
        self.assertEqual(result[0]['to'], 'sent')
        self.assertEqual(box.get(row['id'])['retry_count'], 1)
        self.assertEqual(dispatch_outbox(self.path, now=NOW + timedelta(minutes=3)), [])
        self.assertEqual([item['event'] for item in box.ledger(row['id'])],
                         ['queued', 'failed', 'queued', 'sent'])

    def test_expired_failed_retry_never_calls_sender(self):
        store = WatchStore(self.path)
        watch = store.create('Watch heavy rain', {'name': 'Synthetic place'}, 'heavy_rain',
                             window_end=(NOW + timedelta(minutes=1)).isoformat(), now=NOW)
        row = OutboxStore(self.path).enqueue(watch['id'], 'c1', 'f1', 'local_inbox', {}, now=NOW)
        dispatch_outbox(self.path, now=NOW, send=lambda entry: (False, 'temporary failure'))
        def forbidden(entry):
            self.fail('An expired notification was sent')
        dispatch_outbox(self.path, now=NOW + timedelta(minutes=2), send=forbidden)
        self.assertEqual(OutboxStore(self.path).get(row['id'])['state'], 'gone')

    def test_http_registration_change_evidence_ack_and_retirement(self):
        moment = [NOW]
        app = Workspace(self.root / 'jobs.sqlite', self.root / 'raw', self.root / 'geography.sqlite', clock=lambda: moment[0])
        app.conversation = object()
        server = make_server(app, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join()))
        base = 'http://127.0.0.1:' + str(server.server_port)
        with urllib.request.urlopen(base) as response:
            token = re.search(r'name="workspace-token" content="([^"]+)"', response.read().decode())[1]
        def request(path, body=None, authenticated=True):
            headers = {'Content-Type': 'application/json'}
            if authenticated:
                headers['X-WeatherGPT-Token'] = token
            data = json.dumps(body).encode() if body is not None else None
            with urllib.request.urlopen(urllib.request.Request(base + path, data, headers), timeout=5) as response:
                return json.load(response)
        with self.assertRaises(urllib.error.HTTPError) as denied:
            request('/api/outbox', authenticated=False)
        self.assertEqual(denied.exception.code, 403)
        with self.assertRaises(urllib.error.HTTPError) as denied:
            request('/api/watches/create', {}, authenticated=False)
        self.assertEqual(denied.exception.code, 403)
        watch = request('/api/watches/create', {'place': {'name': 'Synthetic review place', 'latitude': 26.14, 'longitude': 91.74}, 'hazard': 'heavy rain'})
        facts = [fact([1], quiet=True)]
        with patch('weathergpt_data.warning_tools.execute_warning', side_effect=lambda engine, packet, *args, **kw: {**packet, 'facts': list(facts), 'status': 'answered'}):
            request('/api/watches/check', {'id': watch['id']})
            self.assertEqual(request('/api/outbox')['notifications'], [])
            facts[:] = [fact([16])]
            request('/api/watches/check', {'id': watch['id']})
            request('/api/watches/check', {'id': watch['id']})
        notices = request('/api/outbox')['notifications']
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]['state'], 'sent')
        evidence = notices[0]['payload']['facts'][0]
        for key in ('source_id', 'unit', 'start', 'end', 'value'):
            self.assertEqual(evidence[key], facts[0][key])
        moment[0] += timedelta(minutes=3)
        ack = request('/api/outbox/' + notices[0]['id'] + '/ack', {'response': 'need_help'})
        self.assertEqual(ack['state'], 'acked')
        self.assertEqual(ack['response'], 'need_help')
        self.assertEqual(request('/api/watches')['watches'][0]['last_notification_at'], NOW.isoformat())
        request('/api/watches/delete', {'id': watch['id']})
        self.assertTrue(all(item['state'] == 'expired' for item in request('/api/watches')['watches']))
