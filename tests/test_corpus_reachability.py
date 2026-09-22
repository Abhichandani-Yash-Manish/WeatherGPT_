"""The published corpus as a chat route: registered families, honest absences, topic matches.

Measured on 15 September 2026 against the real workspace, four defects stood between a reader
and the 571 district editions already indexed here: the family was refused as unknown by task
validation, a printed valid-till time crashed the turn, a state the publisher's directory
covers but no edition is held for was answered as a missing place, and a question about grapes
was answered with the edition's pearl-millet and paddy passages because every passage carries
the district name. These checks pin the repairs on a synthetic index; they measure no publisher.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from weathergpt_data import document_tools

from weathergpt_data.bulletin_index import BulletinIndex
from weathergpt_data.corpus_tools import execute_corpus, printed_validity, topic_tokens
from weathergpt_data.document_ingest import ALL_FAMILIES, FAMILIES
from weathergpt_data.document_tools import execute_document
from weathergpt_data.tasks import validate_tasks
from weathergpt_data.transport import SourceError, digest

NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)


def encoder(texts, query=False):
    rows = []
    for text in texts:
        low = (text or '').lower()
        rows.append([1.0 if 'grape' in low else 0.0, 1.0 if 'district' in low else 0.0, 0.5])
    return rows


def passage(sha, family, scope, region, issue, text, section=None, source_id='S57', page=1, state=None):
    item = {'document_sha256': sha, 'family': family, 'scope': scope, 'region': region, 'section': section,
            'text': text, 'physical_page': page, 'passage_index': 1, 'source_locator': 'physical PDF page %d' % page,
            'issue_date': issue, 'language': 'en', 'text_quality': 'text_layer_clean', 'source_id': source_id,
            'extraction_version': 'document-passages-v1'}
    if state:
        item['source_state'] = state
    item['id'] = digest(json.dumps(item, sort_keys=True, ensure_ascii=False).encode())
    return item


def document(family, scope, region, issue, texts, state=None, section=None, source_id='S57'):
    texts = texts if isinstance(texts, list) else [texts]
    sha = digest((family + '|' + str(region) + '|' + str(issue) + '|' + '|'.join(texts)).encode())
    body = {'sha256': sha, 'family': family, 'scope': scope, 'region': region, 'language': 'en', 'pages': len(texts),
            'source_id': source_id, 'extraction_status': 'text_layer_extracted_reading_order_unverified',
            'currency': 'printed_issue_differs_from_retrieval_date' if issue else 'printed_issue_not_stated',
            'age_days': 1 if issue else None, 'quarantined_pages': [],
            'printed_times': {}, 'passages': [passage(sha, family, scope, region, issue, text, section=section,
                                                      source_id=source_id, page=position, state=state)
                                              for position, text in enumerate(texts, start=1)]}
    if state:
        body['source_state'] = state
    return body


class FakeIndex(BulletinIndex):
    def search_passages(self, *args, **kwargs):
        kwargs.setdefault('encoder', encoder)
        return super().search_passages(*args, **kwargs)


class FakeWorkspace:
    """A workspace whose bulletin index is the synthetic one built for the test."""

    def __init__(self, path, corpus_path, now=NOW):
        self.path = path
        self.corpus_path = corpus_path
        self.index = FakeIndex(corpus_path)
        self.now = now
        self.service = SimpleNamespace(raw_root=Path(path) / 'raw')

    def document_index(self):
        return self.index

    def clock(self):
        return self.now


class CorpusReachability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.corpus = self.root / 'bulletins' / 'bulletin-grid-v2' / 'index.sqlite'
        self.workspace = FakeWorkspace(self.root, self.corpus)
        self.engine = SimpleNamespace(workspace=self.workspace, gazetteer=None)

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self, body):
        self.workspace.index.publish_document(body, {'sha256': body['sha256'], 'blob': None},
                                              '2026-09-15T06:00:00+00:00', encoder=encoder)
        return body['sha256']

    def run_corpus(self, plan, request, question='What does the document say?'):
        task = {'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'],
                'request_quote': question, 'corpus_request': request}
        result = {'question': question, 'plan': plan, 'trace': {'tools': [], 'generation': None}, 'facts': [],
                  'citations': [], 'notes': []}
        return execute_corpus(self.engine, result, plan, task)

    def run_document(self, plan, question, request=None, resolved=None):
        task = {'kind': 'agriculture', 'operation': 'lookup', 'parameters': ['agricultural_advisory'],
                'request_quote': question,
                'document_request': request or {'query': question, 'crop': '', 'growth_stage': '',
                                                'topic': 'general', 'mode': 'source_lookup'}}
        result = {'question': question, 'plan': plan, 'trace': {'tools': [], 'generation': None}, 'facts': [],
                  'citations': [], 'notes': []}
        return execute_document(self.engine, result, plan, task, resolved=resolved or {})


class RegistryTests(CorpusReachability):
    def test_the_district_family_is_registered_for_a_chat_request(self):
        # 571 district editions were indexed while a request naming that family was refused as
        # unknown: the family lives in DISTRICT_SPEC and validation only asked FAMILIES.
        self.assertNotIn('district_agromet', FAMILIES)
        self.assertIn('district_agromet', ALL_FAMILIES)
        validate_tasks([{'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'],
                         'years': [], 'period': 'annual', 'start_local': '', 'end_local': '', 'place_indices': [0],
                         'request_quote': 'What does today\'s district agromet bulletin for Nashik say?',
                         'corpus_request': {'query': 'district agromet bulletin Nashik', 'family': 'district_agromet',
                                            'scope': 'district'}}],
                       [{'name': 'Nashik', 'state': '', 'district': '', 'kind': 'unknown'}])

    def test_an_unregistered_family_is_still_refused(self):
        with self.assertRaises(SourceError):
            validate_tasks([{'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'],
                             'years': [], 'period': 'annual', 'start_local': '', 'end_local': '', 'place_indices': [],
                             'corpus_request': {'query': 'x', 'family': 'made_up_family', 'scope': ''}}], [])


class PrintedValidityTests(CorpusReachability):
    def test_a_printed_valid_till_time_is_a_timezone_not_an_offset(self):
        # The national flash flood guidance question failed the whole turn with
        # "tzinfo argument must be None or of a tzinfo subclass" until this was a timezone.
        valid = printed_validity({'printed_times': {'valid_till': '1730 IST'}, 'issue_date': '2026-09-14'})
        self.assertEqual(valid.isoformat(), '2026-09-14T17:30:00+05:30')
        self.assertEqual(printed_validity({'printed_times': {'valid_till': '1730 UTC'}, 'issue_date': '2026-09-14'}).isoformat(),
                         '2026-09-14T17:30:00+00:00')
        self.assertLess(valid, datetime(2026, 9, 15, 12, tzinfo=timezone.utc))
        self.assertIsNone(printed_validity({'printed_times': {}, 'issue_date': '2026-09-14'}))

    def test_an_expired_printed_validity_is_disclosed_not_silently_dropped(self):
        body = document('flash_flood_national', 'national', None, '2026-09-14',
                        'Flash flood guidance for the north-eastern districts.')
        body['printed_times'] = {'valid_till': '1730 IST'}
        self.publish(body)
        result = self.run_corpus({'places': []}, {'query': 'flash flood guidance', 'family': 'flash_flood_national',
                                                  'scope': 'national'})
        self.assertEqual(result['status'], 'partial')
        self.assertIn('printed validity', result['answer'])
        self.assertEqual(result['retrieval_coverage']['expired_printed_validity'], 1)


class RegionAbsenceTests(CorpusReachability):
    def test_a_directory_state_with_no_indexed_edition_is_an_absence_with_the_held_states(self):
        # "What changed in the latest state agromet bulletin for Maharashtra?" was answered by
        # asking which state was meant, although the publisher's own directory lists Maharashtra.
        self.publish(document('state_agromet', 'state', 'Gujarat', '2026-09-12',
                              'Irrigation advice for the state.', state='Gujarat'))
        plan = {'places': [{'name': 'Maharashtra', 'state': '', 'district': '', 'kind': 'unknown'}]}
        result = self.run_corpus(plan, {'query': 'what changed', 'family': 'state_agromet', 'scope': 'state'})
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('No indexed document is published for Maharashtra', result['answer'])
        self.assertIn('Gujarat', result['answer'])
        self.assertNotIn('Which state', result['answer'])

    def test_the_publishers_own_spelling_of_a_real_district_is_read_and_disclosed(self):
        """Changed deliberately in docs/142, and narrowed rather than loosened.

        This used to refuse: Kendrapada was met with "no district agromet edition is indexed
        under that name", the close spelling offered as a hint, and the reader asked to say
        it again. The rule behind it was that a near name is a reason to ask rather than a
        reason to answer for a district nobody named, and that rule still holds for a near
        name in general.

        What changed is where the nearness is judged. "Kendrapada" is not a different
        district that happens to look similar - it is the publisher's own Kendrapara, and
        the publisher's directory is the authority on that, not a string comparison against
        whatever this corpus happens to hold. The same bounded match already resolved
        Davangere to the directory's Davanagere one layer up, and refusing here meant a
        district the engine had just identified was then reported as not held.

        The disclosure is the price and it is not optional: the answer says which district
        it was read as, and that no other district's edition was substituted.
        """
        self.publish(document('district_agromet', 'district', 'Kendrapara', '2026-09-12',
                              'Apply light irrigation to the standing cotton crop.', state='Odisha'))
        plan = {'places': [{'name': 'Kendrapada', 'state': 'Odisha', 'district': 'Kendrapada', 'kind': 'district'}]}
        result = self.run_corpus(plan, {'query': 'cotton', 'family': 'district_agromet', 'scope': 'district'})
        self.assertEqual(result['status'], 'answered')
        self.assertTrue(result['passages'])
        self.assertTrue(any('Kendrapara' in note and 'substituted' in note for note in result['notes']))

    def test_a_district_the_publisher_does_not_list_is_still_an_absence(self):
        # The bound that keeps the above honest. Nothing close enough sits in the publisher's
        # directory, so no edition is read and the held names are offered as a hint.
        self.publish(document('district_agromet', 'district', 'Kendrapara', '2026-09-12',
                              'Apply light irrigation to the standing cotton crop.', state='Odisha'))
        plan = {'places': [{'name': 'Zzzqqxville', 'state': 'Odisha', 'district': 'Zzzqqxville', 'kind': 'district'}]}
        result = self.run_corpus(plan, {'query': 'cotton', 'family': 'district_agromet', 'scope': 'district'})
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['passages'], [])


class TopicMatchTests(CorpusReachability):
    def test_the_topic_word_decides_which_passage_is_served(self):
        # Asked about grapes, every passage of a Nashik edition matches "Nashik", so the district
        # name alone served pearl-millet and paddy passages.
        self.publish(document('district_agromet', 'district', 'Nashik', '2026-09-11',
                              ['Pearl millet vegetative stage hoeing and weeding in the Nashik district.',
                               'Grapes limestone content in the Nashik district vineyards was discussed.'],
                              state='Maharashtra'))
        plan = {'places': [{'name': 'Nashik', 'state': 'Maharashtra', 'district': 'Nashik', 'kind': 'district'}]}
        result = self.run_corpus(plan, {'query': 'What does the agromet bulletin for Nashik say about grapes?',
                                        'family': 'district_agromet', 'scope': 'district'},
                                 question='What does the agromet bulletin for Nashik say about grapes?')
        self.assertEqual([p['text'][:6] for p in result['passages']], ['Grapes'])
        self.assertEqual(result['retrieval_coverage']['topic_tokens'], ['grapes'])
        self.assertTrue(result['retrieval_coverage']['topic_matched'])
        self.assertEqual(result['status'], 'answered')

    def test_a_topic_the_edition_does_not_mention_is_stated_not_answered(self):
        self.publish(document('district_agromet', 'district', 'Nashik', '2026-09-11',
                              'Pearl millet vegetative stage hoeing and weeding in the Nashik district.',
                              state='Maharashtra'))
        plan = {'places': [{'name': 'Nashik', 'state': 'Maharashtra', 'district': 'Nashik', 'kind': 'district'}]}
        result = self.run_corpus(plan, {'query': 'What does the agromet bulletin for Nashik say about grapes?',
                                        'family': 'district_agromet', 'scope': 'district'},
                                 question='What does the agromet bulletin for Nashik say about grapes?')
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(result['retrieval_coverage']['topic_matched'])
        self.assertIn('does not answer it', result['answer'])
        self.assertIn('grapes', result['answer'])

    def test_topic_tokens_drop_the_place_and_the_document_words(self):
        plan = {'places': [{'name': 'Nashik', 'state': 'Maharashtra', 'district': 'Nashik', 'kind': 'district'}]}
        self.assertEqual(topic_tokens('What does the agromet bulletin for Nashik say about grapes?', plan, 'Nashik'),
                         ['grapes'])
        self.assertEqual(topic_tokens('Show me the latest district bulletin.', plan, 'Nashik'), [])


class DistrictChatRouteTests(CorpusReachability):
    def without_live_fetch(self):
        """No test reaches the publisher: the live reader is replaced in these checks."""
        from weathergpt_data import document_tools
        original = document_tools.sync

        def refuse(*args, **kwargs):
            raise SourceError('Printed district could not be verified with the supported layout rules')

        document_tools.sync = refuse
        return original

    def test_a_district_the_directory_does_not_list_is_asked_not_errored(self):
        plan = {'places': [{'name': 'Nowhereville', 'state': 'Maharashtra', 'district': 'Nowhereville',
                            'kind': 'settlement'}]}
        result = self.run_document(plan, 'What does the agromet bulletin for Nowhereville say?')
        self.assertEqual(result['status'], 'needs_clarification')
        self.assertIn('district directory does not list Nowhereville', result['answer'])
        self.assertEqual(result['pending_slots'][0]['field'], 'place')

    def test_a_division_label_falls_through_to_the_district_the_reader_named(self):
        # GeoNames files Nashik under "Nashik Division" (admin2), which is not a district. The
        # division label was passed to the publisher selector, the reader's own name was never
        # tried, and the turn ended as "District did not uniquely match the publisher directory".
        self.publish(document('district_agromet', 'district', 'Nashik', '2026-09-11',
                              'Grapes limestone content in the Nashik district vineyards was discussed.',
                              state='Maharashtra'))
        original = self.without_live_fetch()
        try:
            plan = {'places': [{'name': 'Nashik', 'state': '', 'district': '', 'kind': 'settlement'}]}
            result = self.run_document(plan, 'What does the agromet bulletin for Nashik say about grapes?',
                                       request={'query': 'grapes', 'crop': 'grapes', 'growth_stage': '',
                                                'topic': 'general', 'mode': 'source_lookup'},
                                       resolved={'Nashik': {'admin1': 'State of Mahārāshtra',
                                                            'admin2': 'Nashik Division'}})
        finally:
            document_tools.sync = original
        notes = ' '.join(result.get('notes') or [])
        self.assertIn('Nashik Division', notes)
        self.assertIn('Read as Nashik, Maharashtra in the publisher directory', notes)
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['document_evidence'][0]['region'], 'Nashik')

    def test_the_indexed_edition_answers_when_the_live_bulletin_cannot_be_verified(self):
        from weathergpt_data import document_tools
        self.publish(document('district_agromet', 'district', 'Nashik', '2026-09-11',
                              'Grapes limestone content in the Nashik district vineyards was discussed.',
                              state='Maharashtra'))
        original = document_tools.sync

        def refuse(*args, **kwargs):
            raise SourceError('Printed district could not be verified with the supported layout rules')

        document_tools.sync = refuse
        try:
            plan = {'places': [{'name': 'Nashik', 'state': 'Maharashtra', 'district': 'Nashik', 'kind': 'district'}]}
            result = self.run_document(plan, 'What does the agromet bulletin for Nashik say about grapes?',
                                       request={'query': 'grapes', 'crop': 'grapes', 'growth_stage': '',
                                                'topic': 'general', 'mode': 'source_lookup'},
                                       resolved={'Nashik': {'admin1': 'State of Mahārāshtra',
                                                            'admin2': 'Nashik Division'}})
        finally:
            document_tools.sync = original
        self.assertEqual(result['status'], 'answered')
        self.assertIn('could not be verified', result['answer'])
        self.assertIn('printed issue 2026-09-11', result['answer'])
        self.assertTrue(any('Grapes' in passage['text'] for passage in result['passages']))
        self.assertTrue(any('Crop and growth-stage annotation' in note for note in result['notes']))

    def test_a_place_written_in_another_script_resolves_to_the_stored_region(self):
        # Measured 15 September 2026: "નાસિક જિલ્લાની કૃષિ સલાહમાં …" extracted નાસિક and the corpus
        # answered that no edition was indexed under that name, although the Nashik edition is held.
        # The resolved record carries the publisher's English name and is tried first.
        self.publish(document('district_agromet', 'district', 'Nashik', '2026-09-11',
                              'Grapes limestone content in the Nashik district vineyards.', state='Maharashtra'))
        plan = {'places': [{'name': 'નાસિક', 'state': '', 'district': '', 'kind': 'district'}]}
        resolved = {'નાસિક': {'name': 'Nashik', 'admin2': 'Nashik Division', 'admin1': 'State of Mahārāshtra'}}
        task = {'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'],
                'request_quote': 'દ્રાક્ષ વિશે શું લખ્યું છે?',
                'corpus_request': {'query': 'grapes', 'family': 'district_agromet', 'scope': 'district'}}
        result = {'question': 'દ્રાક્ષ વિશે શું લખ્યું છે?', 'plan': plan, 'trace': {'tools': [], 'generation': None},
                  'facts': [], 'citations': [], 'notes': []}
        result = execute_corpus(self.engine, result, plan, task, resolved)
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['document_evidence'][0]['region'], 'Nashik')
        self.assertEqual(result['document_evidence'][0]['state'], 'Maharashtra')

    def test_a_name_the_reader_wrote_is_still_tried_last(self):
        self.publish(document('district_agromet', 'district', 'Nashik', '2026-09-11',
                              'Grapes limestone content in the Nashik district vineyards.', state='Maharashtra'))
        plan = {'places': [{'name': 'Nashik', 'state': '', 'district': '', 'kind': 'district'}]}
        task = {'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'],
                'request_quote': 'grapes', 'corpus_request': {'query': 'grapes', 'family': 'district_agromet',
                                                              'scope': 'district'}}
        result = {'question': 'grapes', 'plan': plan, 'trace': {'tools': [], 'generation': None}, 'facts': [],
                  'citations': [], 'notes': []}
        result = execute_corpus(self.engine, result, plan, task)
        self.assertEqual(result['document_evidence'][0]['region'], 'Nashik')


if __name__ == '__main__':
    unittest.main()
