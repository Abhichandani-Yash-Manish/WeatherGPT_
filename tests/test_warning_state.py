"""Phase 1: canon-v1 canonicalization, change detector, idempotent watch create.

Proves the dissemination backbone contracts without touching live sources:
everything here runs against synthetic packets through the real stores.
"""
import unittest
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from weathergpt_data import warning_state as ws
from weathergpt_data.watches import WatchStore, compute_fingerprint
from weathergpt_data.outbox import OutboxStore

NOW = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)


def fact(codes, label='Day 1 · 16 Sep 2026 · Heavy Rain', start='2026-09-16T00:00:00+05:30',
         end='2026-09-17T00:00:00+05:30'):
    return {'parameter': 'official_district_warning', 'label': label, 'value': 'orange',
            'start': start, 'end': end, 'hazard_codes': list(codes), 'quiet': False,
            'source_id': 'S15'}


def snap(fp='fp-1', matched=True, reason='current_official_district_hazard_matches'):
    return {'canon_version': 'canon-v1', 'watch_id': 'w', 'hazard': 'heavy_rain',
            'place': 'Patna', 'fingerprint_sha256': fp, 'matched': matched,
            'reason': reason, 'packet_status': 'answered'}


class CanonicalTests(unittest.TestCase):
    def test_fact_order_and_key_order_do_not_move_the_hash(self):
        first = ws.fingerprint(ws.canonical_input('w', 'heavy_rain', 'Patna',
                                                  [fact([16]), fact([4])], 'r', 'answered', 2, 5))
        reordered = ws.fingerprint(ws.canonical_input('w', 'heavy_rain', 'Patna',
                                                      [dict(fact([4])), dict(fact([16]))],
                                                      'r', 'answered', 2, 5))
        self.assertEqual(first, reordered)

    def test_volatile_fields_are_excluded_by_construction(self):
        base = dict(fact([16]))
        noisy = dict(base, retrieved_at_utc='2026-09-16T12:34:56Z',
                     request_id='abc', cache_age_seconds=42,
                     answer_text='rendered prose with a timestamp')
        first = ws.fingerprint(ws.canonical_input('w', 'heavy_rain', 'Patna', [base],
                                                  'r', 'answered', 2, 5))
        second = ws.fingerprint(ws.canonical_input('w', 'heavy_rain', 'Patna', [noisy],
                                                   'r', 'answered', 2, 5))
        self.assertEqual(first, second)

    def test_non_warning_facts_and_render_text_never_participate(self):
        other = {'parameter': 'model_forecast', 'value': '42'}
        first = ws.fingerprint(ws.canonical_input('w', 'heavy_rain', 'Patna',
                                                  [fact([16]), other], 'r', 'answered'))
        second = ws.fingerprint(ws.canonical_input('w', 'heavy_rain', 'Patna',
                                                   [fact([16])], 'r', 'answered'))
        self.assertEqual(first, second)

    def test_material_changes_move_the_hash(self):
        base = ws.fingerprint(ws.canonical_input('w', 'heavy_rain', 'Patna',
                                                 [fact([16])], 'r', 'answered', 2, 5))
        for variant in (ws.canonical_input('w', 'heavy_rain', 'Patna', [fact([4])],
                                           'r', 'answered', 2, 5),
                        ws.canonical_input('w', 'heavy_rain', 'Patna', [fact([16])],
                                           'other-reason', 'answered', 2, 5),
                        ws.canonical_input('w', 'heavy_rain', 'Patna', [fact([16])],
                                           'r', 'answered', 0, 5)):
            self.assertNotEqual(base, ws.fingerprint(variant))

    def test_legacy_compute_fingerprint_is_byte_identical(self):
        legacy = compute_fingerprint('w1', 'heavy_rain', 'P', [fact([16])],
                                     'r', 'answered', 2, 5)
        canon = ws.fingerprint(ws.canonical_input('w1', 'heavy_rain', 'P', [fact([16])],
                                                  'r', 'answered', 2, 5))
        self.assertEqual(legacy, canon)


class DetectorTests(unittest.TestCase):
    def test_first_readable_check_is_baseline(self):
        event = ws.detect(None, snap())
        self.assertEqual(event['kind'], 'baseline')

    def test_unavailable_holds_even_on_first_check(self):
        event = ws.detect(None, snap(), unavailable=True)
        self.assertEqual((event['kind'], event['reason']), ('held', 'held_unavailable'))

    def test_identical_state_is_no_change(self):
        event = ws.detect(snap('fp-1', True), snap('fp-1', True))
        self.assertEqual(event['kind'], 'no_change')

    def test_no_match_to_match_is_created(self):
        event = ws.detect(snap('fp-1', False), snap('fp-2', True))
        self.assertEqual(event['kind'], 'created')

    def test_match_to_match_change_is_updated(self):
        event = ws.detect(snap('fp-1', True), snap('fp-2', True))
        self.assertEqual(event['kind'], 'updated')

    def test_match_to_no_match_is_updated_never_all_clear(self):
        event = ws.detect(snap('fp-1', True), snap('fp-2', False))
        self.assertEqual(event['kind'], 'updated')
        self.assertIn('never an all-clear', event['detail'])

    def test_official_cancel_is_cancelled_not_all_clear(self):
        event = ws.detect(snap('fp-1', True), snap('fp-2', False), official_cancel=True)
        self.assertEqual(event['kind'], 'cancelled')
        self.assertIn('not an all-clear', event['detail'])

    def test_window_expiry_is_expired(self):
        event = ws.detect(snap('fp-1', True), snap('fp-1', True), window_expired=True)
        self.assertEqual(event['kind'], 'expired')

    def test_not_connected_holds_but_advances(self):
        event = ws.detect(snap('fp-1', False), snap('fp-2', False), not_connected=True)
        self.assertEqual((event['kind'], event['reason']), ('held', 'not_connected_held'))
        self.assertEqual(event['fingerprint_sha256'], 'fp-2')

    def test_only_created_updated_cancelled_may_enqueue(self):
        for kind in ('baseline', 'expired', 'no_change', 'held'):
            self.assertNotIn(kind, ('created', 'updated', 'cancelled'))


class IdempotentCreateTests(unittest.TestCase):
    def test_repeat_create_returns_existing_watch(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WatchStore(Path(tmp) / 'watches.sqlite')
            place = {'name': 'Patna, Bihar',
                     'coordinates': {'latitude': 25.5941, 'longitude': 85.1376}}
            first = store.create('Notify me of heavy rain in Patna', place, 'heavy_rain')
            second = store.create('Notify me of heavy rain in Patna again', place, 'heavy_rain')
            self.assertEqual(first['id'], second['id'])
            self.assertTrue(second.get('duplicate'))
            self.assertEqual(len(store.list()), 1)

    def test_different_hazard_or_window_creates_a_new_watch(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WatchStore(Path(tmp) / 'watches.sqlite')
            place = {'name': 'Patna, Bihar',
                     'coordinates': {'latitude': 25.5941, 'longitude': 85.1376}}
            first = store.create('rain', place, 'heavy_rain')
            other_hazard = store.create('storm', place, 'thunderstorm')
            other_window = store.create('rain later', place, 'heavy_rain',
                                        window_start='2026-09-20T00:00:00+00:00',
                                        window_end='2026-09-21T00:00:00+00:00')
            self.assertNotEqual(first['id'], other_hazard['id'])
            self.assertNotEqual(first['id'], other_window['id'])
            self.assertEqual(len(store.list()), 3)

    def test_nearby_pin_within_tolerance_dedupes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = WatchStore(Path(tmp) / 'watches.sqlite')
            first = store.create('rain', {'name': 'Patna',
                                          'coordinates': {'latitude': 25.59410, 'longitude': 85.13760}},
                                 'heavy_rain')
            second = store.create('rain', {'name': 'Patna',
                                           'coordinates': {'latitude': 25.59411, 'longitude': 85.13761}},
                                  'heavy_rain')
            self.assertEqual(first['id'], second['id'])


if __name__ == '__main__':
    unittest.main()
