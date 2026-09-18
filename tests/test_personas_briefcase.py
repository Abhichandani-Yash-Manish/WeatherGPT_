"""Personas and the briefcase: framing that changes no finding, and a store that keeps one.

These are offline checks. A persona is pinned as an emphasis, never a source of facts: it
cannot add a value, a source or a claim, it cannot drop a surface, and an unknown one is
refused rather than guessed. The briefcase is pinned as a store of briefs the workspace
composed: provenance must be present to keep one, the content hash is the composer's own
identity, an export is Markdown and never a delivery, and deleting removes it locally.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from weathergpt_data.personas import (KEYS, PERSONA_IDS, PERSONA_NOTE, annotate, catalogue, get,
                                       surface_order)
from weathergpt_data.alert_brief import compose
from weathergpt_data.briefcase import BriefStore, KIND_LABELS, content_hash, markdown, place_of, sources_of, title_of
from weathergpt_data.transport import SourceError

NOW = datetime(2026, 9, 15, 6, 30, tzinfo=timezone.utc)


def alert_payload():
    return {'status': 'ok', 'brief_id': 'b' * 64,
            'place': {'district': 'PATNA', 'state': 'BIHAR', 'label': 'Patna, Bihar', 'latitude': 25.6, 'longitude': 85.1},
            'day': {'day': 1, 'label': '15 Sep 2026', 'starts_utc': '2026-09-15T18:30:00+00:00',
                    'ends_utc': '2026-09-16T18:30:00+00:00'},
            'sources': [{'source_id': 'S63'}], 'not_established': ['No all-clear is implied.'],
            'status_line': 'Yellow alert for thunderstorm on day 1, as published.'}


def day_row(number):
    return {'day': number, 'label': '1%d Sep 2026' % number, 'date_local': '2026-09-1%d' % number,
            'colour': 'yellow', 'colour_code': 3, 'hazards': ['Thunderstorm/lightning/squall'], 'quiet': False,
            'source_text': 'Thunderstorm with lightning at isolated places.',
            'starts_utc': '2026-09-1%dT18:30:00+00:00' % number,
            'ends_utc': '2026-09-1%dT18:30:00+00:00' % (number + 1)}


def warnings_view():
    return {'schema_version': 'product-view-v1', 'view': 'warnings.place', 'status': 'ok',
            'generated_at_utc': '2026-09-15T04:11:36+00:00',
            'data': {'district': 'PATNA', 'state': 'BIHAR', 'issued_at_utc': '2026-09-15T00:00:00+00:00',
                     'day_boundary_basis': 'Day n is the nth IST calendar day counted from the bulletin date.',
                     'temporal_applicability': 'derived', 'source_locator': '$.features[605]',
                     'days': [day_row(1), day_row(2)]},
            'sources': [{'source_id': 'S63', 'product': 'IMD district warning product',
                         'layer': 'imd:district_warnings_india', 'retrieved_at_utc': '2026-09-15T04:11:36+00:00'}],
            'limitations': ['Day windows are derived from the bulletin date.'],
            'not_established': ['This is district-level warning guidance, not a flood warning and not an all-clear.']}


def markdown_payload():
    """A brief the compose function itself built, so the export renders a real payload."""
    return compose(warnings_view(),
                   {'data': {'messages': 9, 'eligible_by_lifecycle': 0, 'latest_sent': '2026-09-09T12:54:34+05:30'},
                    'sources': [{'source_id': 'S06'}]}, 1)


class PersonaTests(unittest.TestCase):
    def test_every_registered_persona_has_a_unique_identifier(self):
        # The researcher position was added on 18 September 2026 with the persona and language
        # verification batch: the brief asks for farmers, civilians and researchers by name, and
        # only three positions were registered.
        self.assertEqual(PERSONA_IDS, ('farmer', 'district_officer', 'traveller', 'researcher'))
        self.assertEqual(len(set(PERSONA_IDS)), 4)

    def test_every_persona_carries_the_registered_keys(self):
        for item in catalogue()['personas']:
            self.assertEqual(set(item), set(KEYS) | {'note'})
            self.assertEqual(item['note'], PERSONA_NOTE)
            self.assertTrue(item['starters'] and item['keeps_aside'] and item['surfaces'])

    def test_no_persona_chooses_a_language(self):
        # Language support is measured, not selected by a reading position.
        for item in catalogue()['personas']:
            self.assertNotIn('language', item)

    def test_annotate_is_emphasis_only_and_says_so(self):
        block = annotate('farmer')
        self.assertEqual(block['applied'], 'emphasis_only')
        self.assertEqual(block['note'], PERSONA_NOTE)
        self.assertEqual(set(block), set(KEYS) | {'note', 'applied'})
        self.assertIn('changes no value', block['note'])

    def test_absent_persona_is_not_an_error(self):
        for empty in (None, '', 'none'):
            self.assertIsNone(get(empty))
            self.assertIsNone(annotate(empty))

    def test_unknown_persona_is_refused(self):
        with self.assertRaises(SourceError):
            annotate('journalist')

    def test_surface_order_keeps_every_surface_and_moves_its_own_first(self):
        surfaces = ['overview', 'warnings', 'forecast', 'aviation', 'advisories']
        ordered = surface_order('traveller', surfaces)
        self.assertEqual(sorted(ordered), sorted(surfaces))
        self.assertEqual(ordered[:2], ['forecast', 'aviation'])
        self.assertEqual(surface_order(None, surfaces), surfaces)


class BriefcaseTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / 'briefs.sqlite'
        self.store = BriefStore(self.path)

    def test_save_keeps_the_composers_identity_and_the_entry_metadata(self):
        entry = self.store.save('alert_brief', alert_payload(), now=NOW)
        self.assertEqual(entry['content_sha256'], 'b' * 64)
        self.assertEqual(entry['saved_at'], '2026-09-15T06:30:00+00:00')
        self.assertEqual(entry['sources'], ['S63'])
        self.assertEqual(entry['place']['district'], 'PATNA')
        self.assertEqual(entry['delivery'], 'local_only_no_delivery')
        self.assertEqual(self.store.get(entry['id'])['payload']['status_line'], alert_payload()['status_line'])

    def test_a_payload_with_no_provenance_is_refused_not_stored(self):
        with self.assertRaises(SourceError):
            self.store.save('alert_brief', {'status': 'ok', 'status_line': 'fine, trust me'})
        self.assertEqual(self.store.list(), [])

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(SourceError):
            self.store.save('forecast', alert_payload())

    def test_a_not_available_brief_can_be_kept_and_says_what_is_missing(self):
        brief = {'status': 'not_available', 'why': 'the edition does not name this crop',
                 'attempts': ['district_agromet/KOHIMA'], 'not_established': ['no prescription']}
        entry = self.store.save('advisory_brief', brief, now=NOW)
        self.assertIn('not available', entry['title'])
        self.assertIn('does not name this crop', entry['evidence']['why'])

    def test_list_is_newest_first_and_delete_removes_locally(self):
        first = self.store.save('alert_brief', alert_payload(), now=NOW)
        later = self.store.save('alert_brief', alert_payload(), now=NOW.replace(hour=8))
        self.assertEqual([item['id'] for item in self.store.list()], [later['id'], first['id']])
        self.store.delete(first['id'])
        self.assertEqual([item['id'] for item in self.store.list()], [later['id']])
        with self.assertRaises(SourceError):
            self.store.delete(first['id'])

    def test_export_is_markdown_and_claims_no_delivery(self):
        payload = markdown_payload()
        entry = self.store.save('alert_brief', payload, now=NOW)
        text = markdown(entry)
        self.assertTrue(text.startswith('<!--'))
        self.assertIn('Nothing was delivered or published', text)
        self.assertIn('**Kept:** 2026-09-15T06:30:00+00:00', text)
        self.assertIn('Content hash:** sha256 ' + payload['brief_id'][:16], text)
        self.assertIn('# Alert brief', text)
        self.assertIn('Thunderstorm with lightning at isolated places.', text)

    def test_export_quotes_a_payload_this_version_cannot_render(self):
        entry = self.store.save('alert_brief', alert_payload(), now=NOW)
        text = markdown(entry)
        self.assertIn('could not be re-rendered', text)
        self.assertIn('Yellow alert for thunderstorm', text)

    def test_helpers_read_both_brief_shapes(self):
        advisory = {'status': 'ok', 'request': {'crop': 'cotton', 'growth_stage': 'sowing', 'region': 'Ahmedabad', 'window': 'this week'},
                    'published_advice': {'region': 'Ahmedabad', 'passages': [{'source_id': 'S57'}]}, 'not_established': ['no prescription']}
        self.assertEqual(sources_of(advisory), ['S57'])
        self.assertEqual(place_of(advisory)['district'], 'Ahmedabad')
        self.assertEqual(title_of('advisory_brief', advisory), 'Advisory brief — cotton · sowing · Ahmedabad')
        self.assertEqual(KIND_LABELS['alert_brief'], 'Alert brief')

    def test_content_hash_falls_back_to_the_stored_payload(self):
        self.assertEqual(content_hash({'status': 'ok', 'sources': ['S63']}),
                         content_hash({'sources': ['S63'], 'status': 'ok'}))
        self.assertNotEqual(content_hash({'status': 'ok', 'sources': ['S63']}),
                            content_hash({'status': 'ok', 'sources': ['S15']}))


if __name__ == '__main__':
    unittest.main()