"""The state agromet sweep: listed targets, honest outcomes, and a sampled Hindi marker.

Measured on 15 September 2026: of 22 listed state agromet centres, five serve a bulletin at the
publisher's centre path and seventeen do not (fourteen answer HTTP 404 there, and one run hit the
provider's cooldown). The two Hindi editions that were sampled - Jaipur/Rajasthan and
Lucknow/Uttar Pradesh - are Devanagari bulletins whose title is 'संयुक्त कृषि-मौसम सलाहकार सेवा
बुलेटिन'; the family marker now covers them because those front pages were sampled, not because a
single failure asked for a wider pattern.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from test_document_ingest import Store, minimal_pdf, vectors
from weathergpt_data import document_ingest as di
from weathergpt_data.bulletin_index import BulletinIndex
from weathergpt_data.transport import SourceError, digest, stamp

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)
REGISTRY = ROOT / 'data' / 'registry' / 'state-agromet-targets.json'
ENGLISH_FRONT = ('Agromet Advisory Service Bulletin Gujarat State Issued on 11-09-2026 '
               'Bulletin No. 72/2026 India Meteorological Department Ahmedabad')

HINDI_FRONT = ('संयुक्त कृषि-मौसम सलाहकार सेवा बुलेटिन राजस्थान राज्य जारी तिथि 11.09.2026 '
               'बुलेटिन संख्या: 72/2026 कृषि विज्ञान केंद्र जयपुर भारत मौसम विज्ञान विभाग')


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(REGISTRY.read_text(encoding='utf-8'))

    def test_every_listed_target_is_an_https_centre_address(self):
        candidates = self.document['candidates']
        self.assertGreaterEqual(len(candidates), 20)
        addresses = [item['address'] for item in candidates]
        self.assertEqual(len(set(addresses)), len(addresses))
        for item in candidates:
            self.assertTrue(item['address'].startswith('https://mausam.imd.gov.in/'), item['address'])
            self.assertIn(item['centre'] + '/mcdata/agromet.pdf', item['address'])
            self.assertTrue(item['state'].strip())

    def test_the_sweep_records_every_target_and_never_invents_an_issue(self):
        outcomes = self.document.get('outcomes') or {}
        self.assertEqual(len(outcomes), len(self.document['candidates']))
        for key, row in outcomes.items():
            self.assertIn(row['outcome'], sorted(di.DISTRICT_OUTCOMES), key)
            if row['outcome'] in ('failed', 'layout_unrecognised', 'no_text_layer'):
                self.assertTrue(str(row.get('error') or '').strip(), key + ' records a reason')
            if row.get('issue_date'):
                self.assertIn(row['outcome'], ('fetched_new', 'unchanged'), key)

    def test_the_ingested_states_are_the_ones_the_documents_name(self):
        outcomes = self.document.get('outcomes') or {}
        ingested = [row for row in outcomes.values() if row['outcome'] in ('fetched_new', 'unchanged')]
        self.assertGreaterEqual(len(ingested), 5)
        measured = [row for row in ingested if row.get('state_named_in_document') is not None]
        self.assertGreaterEqual(len(measured), 5, 'the five ingested states carry their name check')
        for row in measured:
            self.assertIs(row['state_named_in_document'], True, row['state'])
        self.assertTrue(all(row.get('state_named_in_document') in (None, True) for row in ingested))


class StateSpecTests(unittest.TestCase):
    def test_a_state_target_needs_a_state_and_an_https_address(self):
        with self.assertRaises(SourceError):
            di.state_spec('', 'https://mausam.imd.gov.in/jaipur/mcdata/agromet.pdf')
        with self.assertRaises(SourceError):
            di.state_spec('Rajasthan', 'http://mausam.imd.gov.in/jaipur/mcdata/agromet.pdf')

    def test_the_spec_carries_the_state_and_the_centre_address(self):
        spec = di.state_spec('Rajasthan', 'https://mausam.imd.gov.in/jaipur/mcdata/agromet.pdf')
        self.assertEqual(spec['region'], 'Rajasthan')
        self.assertEqual(spec['scope'], 'state')
        self.assertEqual(spec['source_id'], 'S07')
        self.assertEqual(spec['address'], 'https://mausam.imd.gov.in/jaipur/mcdata/agromet.pdf')
        self.assertIn('मौसम सलाहकार', spec['markers_any'])


class StateIngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.index = BulletinIndex(Path(self.temp.name) / 'index.sqlite')
        self.url = 'https://mausam.imd.gov.in/jaipur/mcdata/agromet.pdf'

    def run_one(self, body, state='Rajasthan'):
        # A deterministic encoder keeps these intake checks independent of the optional
        # multilingual embedding stack; passage ranking quality is not what is under test.
        return di.ingest_state(Store({self.url: body}), self.index, state, self.url, now=NOW, encoder=vectors)

    def test_a_sampled_english_edition_is_accepted_with_its_issue_date(self):
        record = self.run_one(minimal_pdf(ENGLISH_FRONT.encode('utf-8')), state='Gujarat')
        self.assertEqual(record['outcome'], 'fetched_new', record.get('error'))
        self.assertIn('agromet advisory service bulletin', record['marker_basis'])
        self.assertEqual(record['issue_date'], '2026-09-11')
        self.assertIs(record['state_named_in_document'], True)
        self.assertGreater(record['passages'], 0)

    def test_a_front_page_with_no_reviewed_title_is_held_not_indexed(self):
        body = minimal_pdf('Some other bulletin about rainfall and temperature in Teststate'.encode('utf-8'))
        record = self.run_one(body)
        self.assertEqual(record['outcome'], 'layout_unrecognised')
        self.assertIn('marker', str(record.get('error')))

    def test_a_reply_that_is_not_a_pdf_is_a_failure_with_its_stage(self):
        record = self.run_one(b'<html>not a pdf</html>')
        self.assertEqual(record['outcome'], 'failed')
        self.assertEqual(record['stage'], 'fetch')

    def test_the_same_body_again_is_unchanged_rather_than_re_extracted(self):
        body = minimal_pdf(ENGLISH_FRONT.encode('utf-8'))
        first = self.run_one(body)
        second = self.run_one(body)
        self.assertEqual(first['outcome'], 'fetched_new')
        self.assertEqual(second['outcome'], 'unchanged')

    def test_a_state_the_document_does_not_name_is_recorded_as_unverified(self):
        record = self.run_one(minimal_pdf(ENGLISH_FRONT.encode('utf-8')), state='Karnataka')
        self.assertEqual(record['outcome'], 'fetched_new')
        self.assertIs(record['state_named_in_document'], False)




class DevanagariMarkerTests(unittest.TestCase):
    def marker(self, text):
        from weathergpt_data.document_ingest import family, marker_match
        return marker_match([{'text': text}], family('state_agromet'))

    def test_the_two_sampled_hindi_front_pages_are_recognised(self):
        self.assertIn('मौसम सलाहकार', self.marker(HINDI_FRONT))
        lucknow = ('Govt. of India/भारत सरकार Ministry of Earth Sciences/पृथ्वी विज्ञान मंत्रालय '
                   'India Meteorological Department/भारत मौसम विज्ञान विभाग Regional Meteorological Centre Lucknow/ '
                   'प्रादेशिक मौसम केन्द्र, लखनऊ उत्तर प्रदेश संयुक्त कृषि-मौसम सलाहकार सेवा बुलेटिन')
        self.assertIn('मौसम सलाहकार', self.marker(lucknow))

    def test_an_unrelated_bulletin_is_refused_rather_than_matched_by_an_empty_pattern(self):
        from weathergpt_data.transport import SourceError
        with self.assertRaises(SourceError):
            self.marker('Some other bulletin about rainfall and temperature in Teststate')

    def test_squashing_a_devanagari_title_does_not_produce_an_empty_pattern(self):
        from weathergpt_data.document_ingest import _squash
        self.assertTrue(_squash('मौसम सलाहकार'))
        self.assertNotIn(_squash('मौसम सलाहकार'), _squash('Some other bulletin'))

if __name__ == '__main__':
    unittest.main()