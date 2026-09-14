"""Document intake: family recognition, issue evidence, extraction and sweep outcomes.

These are component checks over synthetic and recorded fixtures. They take no
measurement of their own. Nothing here establishes national coverage, publisher
behaviour or the currency of any bulletin; a recorded sweep manifest does that, and
only for the day it names.

The marker fixtures below are the printed titles of real inspected front pages, each
named in the test, because the same product is published under several titles and a
marker list fitted to two failures would not be evidence.
"""
import json
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from weathergpt_data import document_ingest as di
from weathergpt_data.bulletin_index import BulletinIndex
from weathergpt_data.documents import DocumentPruned, strip_controls
from weathergpt_data.transport import SourceError, digest, stamp

ROOT = Path(__file__).resolve().parents[1]
IST = ZoneInfo('Asia/Kolkata')
NOW = datetime(2026, 9, 14, 12, tzinfo=timezone.utc)


def minimal_pdf(text):
    """The smallest PDF pypdf will read, so extraction runs for real in these checks."""
    stream = b'BT /F1 12 Tf 40 700 Td (' + text.replace(b'(', b'').replace(b')', b'') + b') Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R '
               b'/Resources << /Font << /F1 5 0 R >> >> >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>' + chr(10).encode() + b'stream' +
               chr(10).encode() + stream + chr(10).encode() + b'endstream',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out, offsets = b'%PDF-1.4' + chr(10).encode(), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += str(number).encode() + b' 0 obj' + chr(10).encode() + body + chr(10).encode() + b'endobj' + chr(10).encode()
    start = len(out)
    out += b'xref' + chr(10).encode() + b'0 ' + str(len(objects) + 1).encode() + chr(10).encode()
    out += b'0000000000 65535 f ' + chr(10).encode()
    for offset in offsets:
        out += ('%010d 00000 n ' % offset).encode() + chr(10).encode()
    out += (b'trailer' + chr(10).encode() + b'<< /Size ' + str(len(objects) + 1).encode() +
            b' /Root 1 0 R >>' + chr(10).encode() + b'startxref' + chr(10).encode() +
            str(start).encode() + chr(10).encode() + b'%%EOF' + chr(10).encode())
    return out


def page(text, number=1, status=None):
    return {'physical_page': number, 'text': text,
            'source_locator': 'physical PDF page %d' % number,
            'extraction_status': status or ('text_extracted_reading_order_unverified' if text.strip() else 'ocr_required')}


class ExclusionTests(unittest.TestCase):
    def test_publisher_noise_never_enters_the_corpus(self):
        for url in ('https://mausam.imd.gov.in/uploads/sop_flood.pdf',
                    'https://mausam.imd.gov.in/files/recruitment-2026.pdf',
                    'https://mausam.imd.gov.in/files/advert_notice.pdf',
                    'https://mausam.imd.gov.in/files/health.pdf',
                    'https://mausam.imd.gov.in/files/clivar-paper.pdf',
                    'https://mausam.imd.gov.in/banner.png'):
            self.assertTrue(di.excluded(url), url)

    def test_real_weather_products_are_not_excluded(self):
        for url in ('https://mausam.imd.gov.in/Rainfall/national.pdf',
                    'https://mausam.imd.gov.in/responsive/marquee_data/ERF%2011.09.26.pdf',
                    'https://rsmcnewdelhi.imd.gov.in/uploads/special_advisory.pdf'):
            self.assertFalse(di.excluded(url), url)

    def test_a_filename_with_spaces_survives_encoding(self):
        encoded = di.quote_url('https://mausam.imd.gov.in/a/Press Release 11-09-2026.pdf')
        self.assertIn('Press%20Release', encoded)
        self.assertTrue(encoded.startswith('https://'))


class MarkerTests(unittest.TestCase):
    """Each fixture is the printed title of a named district's real front page."""

    def match(self, text, spec=None):
        return di.marker_match([page(text)], spec or di.DISTRICT_SPEC)

    def test_the_common_spaced_title_is_recognised(self):  # Kaushambi, Mirzapur, Sheohar
        self.assertEqual(self.match('Gramin Krishi Mausam Sewa\nAgromet Advisory Bulletin for SHEOHAR District'),
                         'matched:gramin krishi mausam sewa')

    def test_a_title_whose_spaces_the_pdf_dropped_is_recognised(self):  # Wayanad
        self.assertEqual(self.match('AAS Bulletin No:74/2026 GraminKrishiMausamSewa(GKMS) Wayanad'),
                         'matched:gramin krishi mausam sewa')

    def test_an_uppercase_title_is_recognised(self):  # Kullu
        self.assertEqual(self.match('GRAMIN KRISHI MAUSAM SEWA (Agromet Advisory Bulletin for Kullu District)'),
                         'matched:gramin krishi mausam sewa')

    def test_a_title_naming_only_the_abbreviation_is_recognised(self):  # Raigad
        self.assertEqual(self.match('AGROMET ADVISORY SERVICE BULLETIN FOR RAIGAD DISTRICT (Issued jointly by GKMS)'),
                         'matched:gkms')

    def test_a_publisher_using_only_the_product_name_is_recognised(self):  # Madurai, Gondia
        self.assertEqual(self.match('AgroMet Advisory Bulletin (AAB)\nJointly released by Regional Meteorology Centre'),
                         'matched:agromet advisory')
        self.assertEqual(self.match('Dr. Panjabrao Deshmukh Krishi Vidyapeeth, Akola\nAgro-Met Advisory Bulletin'),
                         'matched:agromet advisory')

    def test_an_unrelated_document_is_refused(self):
        with self.assertRaises(SourceError):
            self.match('Standard Operating Procedure for office correspondence')

    def test_front_matter_is_searched_past_an_imageonly_first_page(self):
        pages = [page('', 1), page('Gramin Krishi Mausam Sewa\nAgromet Advisory Bulletin', 2)]
        self.assertEqual(di.marker_match(pages, di.DISTRICT_SPEC), 'matched:gramin krishi mausam sewa')

    def test_a_family_demanding_a_verbatim_marker_still_demands_it(self):
        spec = di.family('flash_flood_national')
        with self.assertRaises(SourceError):
            di.marker_match([page('South Asia Flash Flood Guidance Bulletin')], spec)
        self.assertEqual(di.marker_match([page('National Flash Flood Guidance Bulletin')], spec),
                         'all_named_markers_present')

    def test_an_unknown_family_is_refused_rather_than_guessed(self):
        with self.assertRaises(SourceError):
            di.family('district_rainfall_guess')


class IssueEvidenceTests(unittest.TestCase):
    def test_the_observed_printed_date_layouts_are_read(self):
        for text, expected in (
                ('Weather Forecast of District PATNA Issued On : 2026-09-11', '2026-09-11'),   # Patna
                ('Agromet Advisory Bulletin Date : 2026-09-01', '2026-09-01'),                 # Nagpur
                ('Ahmedabad district agromet bulletin: 47/2026-27  Date: Friday, 11-09-2026', '2026-09-11')):
            value, basis = di.printed_issue([page(text)], di.DISTRICT_SPEC, NOW)
            self.assertEqual(value.isoformat(), expected, text)
            self.assertTrue(basis.startswith('family_rule:'), basis)

    def test_an_unstated_issue_date_stays_unstated(self):
        value, basis = di.printed_issue([page('Gramin Krishi Mausam Sewa, no date printed')], di.DISTRICT_SPEC, NOW)
        self.assertIsNone(value)
        self.assertEqual(basis, 'not_stated')

    def test_a_dated_filename_is_labelled_as_a_filename_not_a_printed_issue(self):
        value, basis = di.printed_issue([page('no date in the body')], {}, NOW,
                                        'https://mausam.imd.gov.in/a/Press%20Release%2011-09-2026.pdf')
        self.assertEqual(value.isoformat(), '2026-09-11')
        self.assertEqual(basis, 'filename')

    def test_a_future_date_is_never_accepted_as_an_issue(self):
        ahead = (NOW.astimezone(IST).date() + timedelta(days=30)).strftime('%d-%m-%Y')
        self.assertIsNone(di.from_filename('https://mausam.imd.gov.in/a/Press%20Release%20' + ahead + '.pdf', NOW))

    def test_currency_is_measured_against_the_printed_issue_not_the_fetch(self):
        spec = dict(di.DISTRICT_SPEC, region='Nagpur')
        stale = di.metadata([page('Gramin Krishi Mausam Sewa\nAgromet Advisory Bulletin Date : 2026-09-01')],
                            spec, 'a' * 64, NOW)
        self.assertEqual(stale['currency'], 'printed_issue_differs_from_retrieval_date')
        self.assertEqual(stale['age_days'], 13)
        self.assertFalse(stale['printed_issue_is_retrieval_date'])
        today = di.metadata([page('Gramin Krishi Mausam Sewa\nAgromet Advisory Bulletin Date : 2026-09-14')],
                            spec, 'a' * 64, NOW)
        self.assertEqual(today['currency'], 'printed_issue_matches_retrieval_date')
        self.assertEqual(today['age_days'], 0)

    def test_a_document_with_no_stated_issue_is_not_called_current(self):
        spec = dict(di.DISTRICT_SPEC, region='Nowhere')
        info = di.metadata([page('Gramin Krishi Mausam Sewa with no printed date at all')], spec, 'a' * 64, NOW)
        self.assertEqual(info['currency'], 'printed_issue_not_stated')
        self.assertIsNone(info['issue_date'])
        self.assertIsNone(info['age_days'])


class ExtractionTests(unittest.TestCase):
    def meta(self):
        return {'sha256': 'a' * 64, 'source_id': 'S57', 'scope': 'district', 'region': 'Testpur',
                'language': 'en', 'issue_date': '2026-09-14'}

    def test_a_page_without_a_text_layer_is_quarantined_not_dropped_silently(self):
        pages = [page('Gramin Krishi Mausam Sewa advisory text that is long enough to keep as a passage.', 1),
                 page('', 2)]
        passages, quarantined = di.passages_of(pages, self.meta(), 'district_agromet')
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0]['physical_page'], 2)
        self.assertIn('OCR', quarantined[0]['reason'])
        self.assertTrue(passages)

    def test_every_passage_keeps_its_physical_page_and_locator(self):
        pages = [page('Sowing advisory for the coming week across the district, issued jointly with the university.', 3)]
        passages, _ = di.passages_of(pages, self.meta(), 'district_agromet')
        for passage in passages:
            self.assertEqual(passage['physical_page'], 3)
            self.assertEqual(passage['source_locator'], 'physical PDF page 3')
            self.assertEqual(passage['region'], 'Testpur')
            self.assertEqual(passage['extraction_version'], di.DOCUMENT_EXTRACTION_VERSION)

    def test_repeated_page_furniture_is_treated_as_boilerplate(self):
        furniture = 'India Meteorological Department, New Delhi - all rights reserved notice'
        pages = [page(furniture + chr(10) + 'Distinct advisory content for page %d of this bulletin edition.' % n, n)
                 for n in range(1, 5)]
        passages, _ = di.passages_of(pages, self.meta(), 'district_agromet')
        self.assertTrue(passages)
        self.assertFalse(any(furniture in p['text'] for p in passages))

    def test_unprintable_publisher_codes_are_replaced_and_the_damage_is_flagged(self):
        cleaned, damaged = strip_controls('advisory' + chr(1) + 'text')
        self.assertTrue(damaged)
        self.assertNotIn(chr(1), cleaned)
        self.assertEqual(strip_controls('ordinary advisory text')[1], False)

    def test_a_damaged_passage_says_so_in_its_own_record(self):
        pages = [page('Apply irrigation' + chr(1) + ' to the standing crop before the forecast dry spell arrives.', 1)]
        passages, _ = di.passages_of(pages, self.meta(), 'district_agromet')
        self.assertEqual(passages[0]['text_quality'], 'control_characters_replaced')

    def test_an_oversized_document_is_refused_rather_than_truncated(self):
        pages = [page(chr(10).join(chr(10).join(['Advisory paragraph %d for this district edition today.' % n])
                                   for n in range(40)), 1)]
        with patch.object(di, 'MAX_PASSAGES', 3):
            with self.assertRaises(SourceError):
                di.passages_of(pages, self.meta(), 'district_agromet')


class DistrictDirectoryTests(unittest.TestCase):
    def test_the_publisher_directory_lists_every_district_once(self):
        targets, provenance = di.district_targets(ROOT)
        self.assertEqual(len(targets), provenance['listed_district_entries'])
        self.assertEqual(len({t['district'] for t in targets}), len(targets))
        self.assertTrue(all(t['state'] and t['district'] for t in targets))

    def test_a_repeated_district_name_is_refused_because_the_selector_cannot_resolve_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / di.DISTRICT_DIRECTORY
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'results': [
                {'state': 'Bihar', 'records': [{'id': 'Aurangabad'}]},
                {'state': 'Maharashtra', 'records': [{'id': 'Aurangabad'}]}]}))
            with self.assertRaises(SourceError):
                di.district_targets(root)

    def test_a_missing_directory_snapshot_is_reported_not_assumed_empty(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(SourceError):
                di.district_targets(Path(temp))

    def test_a_target_needs_both_a_state_and_a_district(self):
        for state, district in ((None, 'Patna'), ('Bihar', ''), ('', 'Patna')):
            with self.assertRaises(SourceError):
                di.district_spec(state, district)


class Store:
    """A store stand-in that serves recorded bodies. It reaches no network."""

    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def fetch(self, source_id, url, params=None, ttl=900, max_bytes=0, refresh=False,
              validator=None, product_validator=None):
        key = url if not params else url + '?' + '&'.join('%s=%s' % kv for kv in sorted(params.items()))
        self.requests.append(key)
        for pattern, body in self.responses.items():
            if pattern in key:
                if isinstance(body, Exception):
                    raise body
                return body, {'sha256': digest(body), 'blob': 'blobs/' + digest(body) + '.bin',
                              'content_type': 'application/pdf' if body.startswith(b'%PDF') else 'text/html',
                              'url': key, 'retrieved_at_utc': stamp(NOW)}
        raise SourceError('No recorded response for ' + key)


def selector(pdf_url):
    return ('<html><body><input id="pdfurl" value="%s"></body></html>' % pdf_url).encode()


class DistrictOutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.index = BulletinIndex(Path(self.temp.name) / 'index.sqlite')

    def run_one(self, responses, district='Testpur'):
        return di.ingest_district(Store(responses), self.index, 'Teststate', district, now=NOW, fetch_ttl=3600)

    def test_every_outcome_carries_its_own_meaning(self):
        self.assertEqual(sorted(di.DISTRICT_OUTCOMES), ['failed', 'fetched_new', 'layout_unrecognised',
                                                        'no_text_layer', 'not_issued', 'unchanged'])
        for outcome, meaning in di.DISTRICT_OUTCOMES.items():
            self.assertTrue(meaning.strip().endswith('.'), outcome)

    def test_a_publisher_saying_not_issued_is_not_recorded_as_a_failure(self):
        record = self.run_one({'district_current_en_get.php': selector('bulletin not issued today')})
        self.assertEqual(record['outcome'], 'not_issued')
        self.assertIsNone(record['url'])
        self.assertIn('not a failure', record['outcome_meaning'])

    def test_an_address_off_the_inspected_hosts_is_refused(self):
        record = self.run_one({'district_current_en_get.php': selector('https://example.invalid/bulletin.pdf')})
        self.assertEqual(record['outcome'], 'failed')
        self.assertEqual(record['stage'], 'selection')
        self.assertIn('official hosts', record['error'])

    def test_a_reply_that_is_not_a_pdf_is_a_failure_with_its_stage_named(self):
        record = self.run_one({'district_current_en_get.php': selector('https://imdagrimet.gov.in/Services/DistrictBulletin.php?d=1'),
                               'DistrictBulletin.php': b'<html>service unavailable</html>'})
        self.assertEqual(record['outcome'], 'failed')
        self.assertEqual(record['stage'], 'fetch')

    def test_a_front_page_of_another_product_is_held_rather_than_indexed(self):
        body = minimal_pdf(b'Standard Operating Procedure for office correspondence')
        record = self.run_one({'district_current_en_get.php': selector('https://imdagrimet.gov.in/Services/DistrictBulletin.php?d=2'),
                               'DistrictBulletin.php': body})
        self.assertEqual(record['outcome'], 'layout_unrecognised')
        self.assertIn('marker', record['error'])
        head = self.index.document_head('district_agromet', 'Testpur')
        self.assertEqual(head['status'], 'failed', 'A held edition must leave a recorded failure behind.')

    def test_a_failure_record_is_preserved_rather_than_cleaned_up(self):
        self.test_a_front_page_of_another_product_is_held_rather_than_indexed()
        head = self.index.document_head('district_agromet', 'Testpur')
        self.assertTrue(head['error'])
        self.assertEqual(head['checked_at'], stamp(NOW))





BULLETIN = (b'Gramin Krishi Mausam Sewa Agromet Advisory Bulletin for TESTPUR District '
            b'Date : 2026-09-14 Apply irrigation to the standing crop before the forecast '
            b'dry spell and keep the harvested produce covered against the expected showers.')


def vectors(texts, query=False):
    return [[1., 0., 0.] for _ in texts]


class IndexingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.index = BulletinIndex(self.root / 'index.sqlite')
        self.body = minimal_pdf(BULLETIN)
        self.store = Store({'district_current_en_get.php': selector(
            'https://imdagrimet.gov.in/Services/DistrictBulletin.php?district=Testpur'),
            'DistrictBulletin.php': self.body})

    def ingest(self):
        return di.ingest_district(self.store, self.index, 'Teststate', 'Testpur',
                                  now=NOW, fetch_ttl=3600, encoder=vectors)

    def test_a_recognised_edition_is_indexed_with_its_printed_issue_evidence(self):
        record = self.ingest()
        self.assertEqual(record['outcome'], 'fetched_new')
        self.assertEqual(record['issue_date'], '2026-09-14')
        self.assertTrue(record['issue_date_basis'].startswith('family_rule:'))
        self.assertEqual(record['marker_basis'], 'matched:gramin krishi mausam sewa')
        self.assertEqual(record['currency'], 'printed_issue_matches_retrieval_date')
        self.assertGreater(record['passages'], 0)

    def test_a_second_pass_over_an_unchanged_body_reindexes_nothing(self):
        first = self.ingest()
        second = self.ingest()
        self.assertEqual(second['outcome'], 'unchanged')
        self.assertEqual(second['sha256'], first['sha256'])
        self.assertNotIn('passages', second)
        self.assertIn('nothing was re-extracted', second['outcome_meaning'])

    def test_the_indexed_passages_are_retrievable_by_family_and_region(self):
        self.ingest()
        results, method = self.index.search_passages('irrigation', family='district_agromet',
                                                     region='Testpur', encoder=vectors)
        self.assertTrue(results)
        self.assertFalse(method['scores_are_confidence'],
                         'A retrieval rank must never be presented as a confidence.')
        self.assertTrue(all(r['region'] == 'Testpur' for r in results))

    def test_a_document_publication_does_not_collide_with_a_chunk_publication(self):
        record = self.ingest()
        published = self.index.document_publications(record['sha256'])
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0].parent.name, 'documents')
        self.assertFalse((published[0].parent.parent / (record['sha256'] + '.json')).exists())

    def test_one_edition_serving_several_districts_publishes_once_per_district(self):
        # A Haryana bulletin is the published edition for eight districts. The bytes are
        # the same and the attributed extraction is not, so each district gets its own
        # publication and the record says the edition is shared.
        first = self.ingest()
        second = di.ingest_district(self.store, self.index, 'Teststate', 'Otherpur',
                                    now=NOW, fetch_ttl=3600, encoder=vectors)
        self.assertEqual(second['outcome'], 'fetched_new')
        self.assertEqual(second['sha256'], first['sha256'])
        self.assertEqual(len(self.index.document_publications(first['sha256'])), 2)
        self.assertEqual(self.index.document_regions(first['sha256']), ['Otherpur', 'Testpur'])
        published = self.index.passage_document(first['sha256'])
        self.assertTrue(published['is_shared_edition'])
        self.assertEqual(published['selected_for_regions'], ['Otherpur', 'Testpur'])


class RetentionTests(unittest.TestCase):
    """Bodies age out; the hash, the passages and the day manifest do not."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('prune_bulletins', ROOT / 'scripts' / 'prune_bulletins.py')
        self.prune = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.prune)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Path(self.temp.name)
        (self.store / 'blobs').mkdir()
        (self.store / 'cache').mkdir()

    def record(self, name, days_old, body=b'%PDF-1.4 body'):
        sha = digest(body)
        (self.store / 'blobs' / (sha + '.bin')).write_bytes(body)
        (self.store / 'cache' / (name + '.json')).write_text(json.dumps({
            'source_id': 'S57', 'url': 'https://imdagrimet.gov.in/' + name,
            'retrieved_at_utc': stamp(NOW - timedelta(days=days_old)),
            'sha256': sha, 'blob': 'blobs/' + sha + '.bin'}))
        return sha

    def test_a_body_inside_the_window_is_kept(self):
        self.record('fresh', 2)
        report = self.prune.survey(self.store, 7, now=NOW)
        self.assertEqual(report['prunable'], [])
        self.assertEqual(len(report['retained']), 1)

    def test_a_body_past_the_window_is_removed_and_the_space_reported(self):
        sha = self.record('stale', 30, b'%PDF-1.4 an older bulletin body')
        report = self.prune.survey(self.store, 7, now=NOW)
        result = self.prune.prune(self.store, report, apply=True)
        self.assertEqual(result['bodies_removed'], 1)
        self.assertGreater(result['bytes_freed'], 0)
        self.assertFalse((self.store / 'blobs' / (sha + '.bin')).exists())

    def test_a_report_only_run_deletes_nothing(self):
        sha = self.record('stale', 30, b'%PDF-1.4 an older bulletin body')
        report = self.prune.survey(self.store, 7, now=NOW)
        self.prune.prune(self.store, report, apply=False)
        self.assertTrue((self.store / 'blobs' / (sha + '.bin')).exists())

    def test_a_body_still_wanted_by_a_newer_retrieval_is_not_pruned(self):
        body = b'%PDF-1.4 one body reached by two request identities'
        sha = self.record('old-identity', 30, body)
        self.record('recent-identity', 1, body)
        report = self.prune.survey(self.store, 7, now=NOW)
        result = self.prune.prune(self.store, report, apply=True)
        self.assertEqual(result['bodies_removed'], 0)
        self.assertTrue((self.store / 'blobs' / (sha + '.bin')).exists())

    def test_pruning_never_touches_the_extracted_evidence(self):
        self.record('stale', 30, b'%PDF-1.4 an older bulletin body')
        report = self.prune.survey(self.store, 7, now=NOW)
        result = self.prune.prune(self.store, report, apply=True)
        self.assertIn('passages', result['kept'])
        self.assertIn('manifests', result['kept'])


class PrunedDocumentTests(unittest.TestCase):
    """A body outside the window is gone; the document is still known."""

    def setUp(self):
        from weathergpt_data.workspace import Workspace
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.index = BulletinIndex(self.root / 'bulletins' / 'v' / 'index.sqlite')
        self.body = minimal_pdf(BULLETIN)
        store = Store({'district_current_en_get.php': selector(
            'https://imdagrimet.gov.in/Services/DistrictBulletin.php?district=Testpur'),
            'DistrictBulletin.php': self.body})
        self.record = di.ingest_district(store, self.index, 'Teststate', 'Testpur',
                                         now=NOW, fetch_ttl=3600, encoder=vectors)
        self.workspace = Workspace.__new__(Workspace)
        self.workspace.document_index = lambda: self.index
        self.workspace.DOCUMENT_STORE = self.root / 'documents'
        (self.root / 'documents' / 'blobs').mkdir(parents=True)

    def body_path(self):
        return self.workspace.DOCUMENT_STORE / self.record['blob']

    def test_a_present_body_is_served(self):
        self.body_path().write_bytes(self.body)
        served = self.workspace.bulletin_pdf.__func__(self.workspace, self.record['sha256'])
        self.assertEqual(digest(served), self.record['sha256'])

    def test_a_pruned_body_is_reported_as_pruned_not_as_unknown(self):
        with self.assertRaises(DocumentPruned) as raised:
            self.workspace.bulletin_pdf.__func__(self.workspace, self.record['sha256'])
        self.assertIn('retention window', raised.exception.detail)
        self.assertEqual(raised.exception.sha, self.record['sha256'])

    def test_what_survives_a_prune_is_named(self):
        retained = self.workspace.document_retention.__func__(self.workspace, self.record['sha256'])
        self.assertEqual(retained['sha256'], self.record['sha256'])
        self.assertEqual(retained['region'], 'Testpur')
        self.assertEqual(retained['issue_date'], '2026-09-14')
        self.assertGreater(retained['retained_passages'], 0)
        self.assertTrue(retained['retained_physical_pages'])

    def test_a_body_that_does_not_hash_to_its_identity_is_refused(self):
        self.body_path().write_bytes(b'%PDF-1.4 a different body entirely')
        with self.assertRaises(SourceError):
            self.workspace.bulletin_pdf.__func__(self.workspace, self.record['sha256'])

    def test_an_identity_that_is_not_a_hash_is_refused(self):
        with self.assertRaises(SourceError):
            self.workspace.bulletin_pdf.__func__(self.workspace, '../../etc/passwd')


if __name__ == '__main__':
    unittest.main()
