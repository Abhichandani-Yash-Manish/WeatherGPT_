"""The published-corpus index: listing state, filters and honest absence.

Offline component checks over a synthetic index with the real schema. They do not read the runtime
corpus and they are not acceptance of the corpus: what they pin is that a printed issue date,
a retained body, a pruned body and an unknown body are four different states, that filters never
change the counts, and that a missing index is reported rather than answered with an empty list.
"""
import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from weathergpt_data import corpus_overview, corpus_tools, product_api
from weathergpt_data.bulletin_index import EXTRACTION_VERSION

SCHEMA = ('CREATE TABLE documents (sha TEXT PRIMARY KEY, payload TEXT, payload_hash TEXT);'
          'CREATE TABLE passages (id TEXT PRIMARY KEY, document_sha TEXT, family TEXT, scope TEXT,'
          ' region TEXT, payload TEXT, payload_hash TEXT, embedding TEXT, embedding_hash TEXT,'
          ' model_revision TEXT);')


def document_row(sha, family, issue_date, region=None, state=None, district=None,
                 retrieved='2026-09-12T06:00:00+00:00', blob=None, url='https://example.test/bulletin.pdf', pages=4):
    payload = {'sha256': sha, 'family': family, 'pages': pages, 'issue_date': issue_date, 'language': 'en',
               'currency': 'measured_at_intake' if issue_date else 'printed_issue_not_stated',
               'state': state, 'district': district, 'quarantined_passages': [],
               'provenance': {'source_id': 'S57', 'url': url, 'retrieved_at_utc': retrieved}}
    if blob:
        payload['provenance']['blob'] = blob
    return (sha, json.dumps(payload), 'hash-of-' + sha)


def passage_row(sha, family, index, page, region=None, issue_date='2026-09-11'):
    payload = {'document_sha256': sha, 'family': family, 'scope': 'district', 'region': region,
               'physical_page': page, 'issue_date': issue_date, 'passage_index': index,
               'source_id': 'S57', 'text': 'Passage ' + str(index)}
    return ('p' + str(index) + '-' + sha[:6], sha, family, 'district', region, json.dumps(payload), 'ph', '{}', 'eh', 'v2')


class CorpusListingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = Path(self.temp.name) / 'runtime'
        self.index = corpus_overview.index_path(self.runtime)
        self.index.parent.mkdir(parents=True)
        first, pruned, undated = 'a' * 64, 'b' * 64, 'c' * 64
        with sqlite3.connect(self.index) as db:
            db.executescript(SCHEMA)
            db.executemany('INSERT INTO documents VALUES (?,?,?)', [
                document_row(first, 'district_agromet', '2026-09-11', region='Ahmedabad', state='Gujarat',
                             district='Ahmedabad', blob='blobs/' + first),
                document_row(pruned, 'district_agromet', '2026-09-10', region='Rajkot', state='Gujarat',
                             district='Rajkot', blob='blobs/absent-body'),
                document_row(undated, 'national_bulletin', None, region=None, url='https://example.test/national.pdf'),
            ])
            db.executemany('INSERT INTO passages VALUES (?,?,?,?,?,?,?,?,?,?)', [
                passage_row(first, 'district_agromet', 1, 1, region='Ahmedabad'),
                passage_row(first, 'district_agromet', 2, 3, region='Ahmedabad'),
                passage_row(pruned, 'district_agromet', 3, 2, region='Rajkot', issue_date='2026-09-10'),
                passage_row(undated, 'national_bulletin', 4, 1, region=None, issue_date=None),
            ])
        body = self.runtime / 'documents' / 'blobs' / first
        body.parent.mkdir(parents=True)
        body.write_bytes(b'%PDF-1.4 synthetic')

    def test_a_printed_issue_date_a_retained_body_and_a_pruned_body_are_separate_states(self):
        result = corpus_overview.documents(self.runtime)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['counts']['documents'], 3)
        self.assertEqual(result['counts']['passages'], 4)
        self.assertEqual(result['counts']['pruned'], 1)
        self.assertEqual(result['counts']['bodies_available'], 1)
        self.assertEqual(result['counts']['regions'], 2)
        by_sha = {row['sha_prefix']: row for row in result['documents']}
        retained = by_sha['a' * 12]
        self.assertEqual(retained['body'], 'available')
        self.assertEqual(retained['age_days'], 1)
        self.assertEqual(retained['passages'], 2)
        self.assertEqual((retained['first_page'], retained['last_page']), (1, 3))
        self.assertEqual(by_sha['b' * 12]['body'], 'pruned')
        self.assertEqual(by_sha['c' * 12]['body'], 'unknown')

    def test_a_document_that_prints_no_issue_date_sorts_last_and_keeps_currency_unknown(self):
        result = corpus_overview.documents(self.runtime)
        self.assertEqual(result['documents'][-1]['sha_prefix'], 'c' * 12)
        self.assertIsNone(result['documents'][-1]['issue_date'])
        self.assertIsNone(result['documents'][-1]['age_days'])
        self.assertEqual(result['counts']['documents_without_a_printed_issue_date'], 1)

    def test_a_passage_date_is_used_when_the_document_payload_states_none(self):
        sha = 'e' * 64
        with sqlite3.connect(self.index) as db:
            db.execute('INSERT INTO documents VALUES (?,?,?)', document_row(sha, 'district_agromet', None, region='Surat'))
            db.execute('INSERT INTO passages VALUES (?,?,?,?,?,?,?,?,?,?)',
                       passage_row(sha, 'district_agromet', 9, 1, region='Surat', issue_date='2026-09-13'))
        row = [item for item in corpus_overview.documents(self.runtime)['documents'] if item['sha_prefix'] == 'e' * 12][0]
        self.assertEqual(row['issue_date'], '2026-09-13')
        self.assertEqual(row['passages'], 1)

    def test_a_filter_narrows_the_list_and_never_changes_the_counts(self):
        narrowed = corpus_overview.documents(self.runtime, query='rajkot')
        self.assertEqual(narrowed['counts']['documents'], 3, 'the counts describe the index, not the page')
        self.assertEqual(narrowed['counts']['documents_matching'], 1)
        self.assertEqual(narrowed['documents'][0]['region'], 'Rajkot')
        family = corpus_overview.documents(self.runtime, family='national_bulletin')
        self.assertEqual(family['counts']['documents_matching'], 1)
        self.assertEqual(family['documents'][0]['family_label'], corpus_tools.family_label('national_bulletin'))

    def test_a_limit_changes_the_page_and_not_the_counts(self):
        limited = corpus_overview.documents(self.runtime, limit=1)
        self.assertEqual(limited['counts']['documents'], 3)
        self.assertEqual(limited['counts']['documents_listed'], 1)
        self.assertEqual(len(limited['documents']), 1)

    def test_a_missing_index_is_reported_with_its_path_rather_than_answered_empty(self):
        missing = Path(self.temp.name) / 'absent'
        result = corpus_overview.documents(missing)
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['documents'], [])
        self.assertEqual(result['index'], str(corpus_overview.index_path(missing)))
        self.assertIn('No corpus index is present', result['reason'])
        self.assertIn(EXTRACTION_VERSION, result['index'])


class StubStore:
    def __init__(self, root):
        self.root = root


class StubFoundation:
    def __init__(self, root):
        self.store = StubStore(root)


class CorpusViewTests(unittest.TestCase):
    def test_the_view_carries_its_limits_and_never_promotes_a_stored_document(self):
        with tempfile.TemporaryDirectory() as directory:
            view = product_api.corpus_documents(StubFoundation(Path(directory)))
        self.assertEqual(view['view'], 'corpus.documents')
        self.assertEqual(view['status'], 'unavailable')
        self.assertTrue(any('retention window' in note for note in view['limitations']))
        self.assertTrue(any('applies to a place' in note for note in view['not_established']))
        self.assertTrue(any('not nationwide coverage' in note for note in view['limitations']))
        self.assertEqual(view['data']['counts']['documents'], 0)

    def test_the_view_reports_the_families_the_counts_and_the_measured_currency(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            path = corpus_overview.index_path(runtime)
            path.parent.mkdir(parents=True)
            sha = 'd' * 64
            with sqlite3.connect(path) as db:
                db.executescript(SCHEMA)
                db.execute('INSERT INTO documents VALUES (?,?,?)',
                           document_row(sha, 'state_agromet', date(2026, 9, 10).isoformat(), state='Karnataka',
                                        retrieved=date(2026, 9, 12).isoformat() + 'T06:00:00+00:00',
                                        blob='blobs/gone'))
                db.execute('INSERT INTO passages VALUES (?,?,?,?,?,?,?,?,?,?)',
                           passage_row(sha, 'state_agromet', 1, 1, region='Karnataka', issue_date='2026-09-10'))
            view = product_api.corpus_documents(StubFoundation(runtime))
        self.assertEqual(view['status'], 'ok')
        self.assertEqual(view['coverage']['documents'], 1)
        self.assertEqual(view['coverage']['bodies_pruned'], 1, 'a recorded but absent body is pruned, not available')
        self.assertEqual(view['data']['documents'][0]['age_days'], 2)
        self.assertEqual(view['sources'][0]['source_id'], 'S57')
        self.assertTrue(view['data']['families'][0]['label'])


if __name__ == '__main__':
    unittest.main()
