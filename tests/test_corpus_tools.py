"""Corpus retrieval: published text stays a record, never a current warning.

These are component checks over a synthetic index. They take no measurement of any
publisher. What they pin is the behaviour the review asked for: currency is read from
the printed issue date, warning text is separated and qualified, an earlier edition is
retired from current retrieval, and a district is never attached to the wrong state.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from weathergpt_data import speech
from weathergpt_data.bulletin_index import BulletinIndex
from weathergpt_data.corpus_tools import execute_corpus,directory_states
from weathergpt_data.dialogue import document_hint,ground_document_request
from weathergpt_data.tasks import validate_tasks
from weathergpt_data.transport import SourceError,digest

NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
_configured = speech.configured


def encoder(texts, query=False):
    """A deterministic fake: scores follow two topic words, so semantic ranking differs."""
    rows = []
    for text in texts:
        low = (text or '').lower()
        rows.append([1.0 if 'irrigation' in low else 0.0, 1.0 if 'wind' in low else 0.0, 0.5])
    return rows


def passage(sha, family, scope, region, issue, text, section=None, source_id='S57', page=1):
    item = {'document_sha256': sha, 'family': family, 'scope': scope, 'region': region, 'section': section,
            'text': text, 'physical_page': page, 'passage_index': 1, 'source_locator': 'physical PDF page %d' % page,
            'issue_date': issue, 'language': 'en', 'text_quality': 'text_layer_clean', 'source_id': source_id,
            'extraction_version': 'document-passages-v1'}
    item['id'] = digest(json.dumps(item, sort_keys=True, ensure_ascii=False).encode())
    return item


def document(family, scope, region, issue, text, state=None, section=None, source_id='S57'):
    sha = digest((family + '|' + str(region) + '|' + str(issue) + '|' + text).encode())
    body = {'sha256': sha, 'family': family, 'scope': scope, 'region': region, 'language': 'en', 'pages': 1,
            'source_id': source_id, 'extraction_status': 'text_layer_extracted_reading_order_unverified',
            'currency': 'printed_issue_differs_from_retrieval_date' if issue else 'printed_issue_not_stated',
            'age_days': 1 if issue else None, 'quarantined_pages': [],
            'passages': [passage(sha, family, scope, region, issue, text, section=section, source_id=source_id)]}
    if state:
        body['source_state'] = state
    return body


class FakeIndex(BulletinIndex):
    """The real index with a fixed encoder, so no test loads the embedding model."""

    def search_passages(self, *args, **kwargs):
        kwargs.setdefault('encoder', encoder)
        return super().search_passages(*args, **kwargs)


class FakeWorkspace:
    def __init__(self, path, now=NOW):
        self.path = path
        self.index = FakeIndex(path)
        self.now = now

    def document_index(self):
        return self.index

    def clock(self):
        return self.now


class CorpusCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = FakeWorkspace(Path(self.tmp.name) / 'index.sqlite')
        self.engine = SimpleNamespace(workspace=self.workspace)

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self, body, checked_at='2026-09-15T06:00:00+00:00'):
        self.workspace.index.publish_document(body, {'sha256': body['sha256'], 'blob': None}, checked_at, encoder=encoder)
        return body['sha256']

    def multi(self, family, scope, region, issue, sections, state=None, source_id='S57'):
        """One edition with several printed sections, published in printed order."""
        sha = digest((family + '|' + str(region) + '|' + str(issue) + '|multi|' + '|'.join(t for _, t in sections)).encode())
        rows = [passage(sha, family, scope, region, issue, text, section=section, source_id=source_id, page=position)
                for position, (section, text) in enumerate(sections, start=1)]
        body = {'sha256': sha, 'family': family, 'scope': scope, 'region': region, 'language': 'en', 'pages': len(sections),
                'source_id': source_id, 'extraction_status': 'text_layer_extracted_reading_order_unverified',
                'currency': 'printed_issue_differs_from_retrieval_date' if issue else 'printed_issue_not_stated',
                'age_days': 1 if issue else None, 'quarantined_pages': [], 'passages': rows}
        if state:
            body['source_state'] = state
        return body

    def run_corpus(self, plan, request, question='What does the document say?'):
        task = {'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'],
                'request_quote': question, 'corpus_request': request}
        result = {'question': question, 'plan': plan, 'trace': {'tools': [], 'generation': None}, 'facts': [], 'citations': []}
        return execute_corpus(self.engine, result, plan, task)


class RetrievalTests(CorpusCase):
    def test_a_district_document_keeps_issue_page_and_state(self):
        self.publish(document('district_agromet', 'district', 'Ahmedabad', '2026-09-12',
                              'Apply light irrigation to the standing cotton crop. Source passage.', state='Gujarat'))
        plan = {'places': [{'name': 'Ahmedabad', 'state': 'Gujarat', 'district': 'Ahmedabad', 'kind': 'district'}]}
        result = self.run_corpus(plan, {'query': 'cotton irrigation', 'family': 'district_agromet', 'scope': 'district'})
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['passages'][0]['physical_page'], 1)
        self.assertEqual(result['document_evidence'][0]['issue_date'], '2026-09-12')
        self.assertIn('printed issue 2026-09-12', result['answer'])
        self.assertIn('document', result['citations'][0]['local_document_path'])

    def test_a_district_without_a_recorded_state_uses_the_dated_directory(self):
        self.publish(document('district_agromet', 'district', 'Ahmedabad', '2026-09-12',
                              'Apply light irrigation to the standing cotton crop.'))
        plan = {'places': [{'name': 'Ahmedabad', 'state': 'Gujarat', 'district': 'Ahmedabad', 'kind': 'district'}]}
        result = self.run_corpus(plan, {'query': 'cotton', 'family': 'district_agromet', 'scope': 'district'})
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['document_evidence'][0]['state'], 'Gujarat')
        self.assertEqual(directory_states('Ahmedabad'), ['Gujarat'])

    def test_a_wrong_state_is_refused_rather_than_substituted(self):
        self.publish(document('district_agromet', 'district', 'Ahmedabad', '2026-09-12',
                              'Apply light irrigation to the standing cotton crop.', state='Gujarat'))
        plan = {'places': [{'name': 'Ahmedabad', 'state': 'Rajasthan', 'district': 'Ahmedabad', 'kind': 'district'}]}
        result = self.run_corpus(plan, {'query': 'cotton', 'family': 'district_agromet', 'scope': 'district'})
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('was not substituted', result['answer'])

    def test_an_unstated_issue_date_is_unknown_currency_not_current(self):
        self.publish(document('state_agromet', 'state', 'Gujarat', None, 'Irrigation advice for the state.'))
        plan = {'places': [{'name': 'Gujarat', 'state': '', 'district': '', 'kind': 'state'}]}
        result = self.run_corpus(plan, {'query': 'irrigation', 'family': 'state_agromet', 'scope': 'state'})
        self.assertEqual(result['status'], 'partial')
        self.assertIn('printed issue not stated', result['answer'])
        self.assertIn('currency is unknown', result['answer'])

    def test_warning_text_is_separated_and_never_a_current_warning(self):
        self.publish(document('coastal_bulletin', 'marine', None, '2026-09-14',
                              'Storm Surge Warning: swell waves are forecast off the coast.', section='COASTAL WARNING'))
        result = self.run_corpus({'places': []}, {'query': 'swell waves', 'family': 'coastal_bulletin', 'scope': 'marine'})
        # Serving a warning-classified passage does not reduce the reading to partial: the
        # passage is served with its label, the answer says what it is and is not, and the
        # warning *task* is the only thing that can speak about applicability. A reduced
        # reading stays partial for the reasons the other checks pin: an unstated issue date,
        # expired printed validity, a retired edition or a disclosed weaker match.
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['retrieval_coverage']['evidence_classes'].get('warning_reference'), 1)
        self.assertIn('reference only', result['answer'])
        self.assertIn('not a current applicable official warning', result['answer'])
        self.assertEqual(result['passages'][0]['evidence_kind'], 'warning_reference')
        self.assertFalse(result['retrieval_coverage']['scores_are_confidence'])

    def test_an_earlier_edition_is_retired_from_current_retrieval(self):
        old = self.publish(document('state_agromet', 'state', 'Gujarat', '2026-09-10',
                                    'Cotton sowing is advised after the dry spell ends.'))
        new = self.publish(document('state_agromet', 'state', 'Gujarat', '2026-09-14',
                                    'Wind speeds are likely to increase along the coast.'))
        plan = {'places': [{'name': 'Gujarat', 'state': '', 'district': '', 'kind': 'state'}]}
        result = self.run_corpus(plan, {'query': 'cotton sowing', 'family': 'state_agromet', 'scope': 'state'})
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('superseded', result['answer'])
        self.assertEqual(result['retrieval_coverage']['superseded_retired'], 1)
        current = self.run_corpus(plan, {'query': 'wind speeds', 'family': 'state_agromet', 'scope': 'state'})
        self.assertEqual(current['document_evidence'][0]['sha256'], new)
        history = self.run_corpus(plan, {'query': 'historical cotton sowing', 'family': 'state_agromet', 'scope': 'state'})
        self.assertEqual(history['document_evidence'][0]['sha256'], old)

    def test_an_indic_script_question_without_a_translation_is_a_disclosed_semantic_match(self):
        # No language service key is configured here, so the top semantic matches are served with
        # the lack of wording support stated.
        self.publish(document('state_agromet', 'state', 'Gujarat', '2026-09-14',
                              'Irrigation should be light and need based across the state.'))
        self.publish(document('state_agromet', 'state', 'Maharashtra', '2026-09-14',
                              'Wind speeds are likely to increase along the coast.'))
        plan = {'places': [{'name': 'Gujarat', 'state': '', 'district': '', 'kind': 'state'}]}
        speech.configured = lambda: False
        try:
            result = self.run_corpus(plan, {'query': 'સિંચાઈ વિશે શું કહ્યું છે', 'family': 'state_agromet',
                                            'scope': 'state'})
        finally:
            speech.configured = _configured
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['retrieval_coverage']['match_basis'], 'semantic_only_indic_script_disclosed')
        self.assertIn('semantic matches', result['answer'])
        self.assertEqual(result['document_evidence'][0]['region'], 'Gujarat')

    def test_an_indic_script_question_is_retrieved_through_a_disclosed_translation(self):
        # A key is configured on this machine, so the question is translated for retrieval only.
        # Measured 15 September 2026: the Hindi question shared no word with the English bulletin
        # and could only be served as a semantic guess.
        self.publish(document('state_agromet', 'state', 'Gujarat', '2026-09-14',
                              'Irrigation should be light and need based across the state.'))
        self.publish(document('state_agromet', 'state', 'Maharashtra', '2026-09-14',
                              'Wind speeds are likely to increase along the coast.'))
        original = (speech.translate, speech.configured)

        def stub(text, target, source='en-IN', **kwargs):
            return 'irrigation advice across the state', {'service': 'stub', 'operation': 'translate', 'model': 'stub'}

        speech.translate = stub
        speech.configured = lambda: True
        try:
            plan = {'places': [{'name': 'Gujarat', 'state': '', 'district': '', 'kind': 'state'}]}
            result = self.run_corpus(plan, {'query': 'સિંચાઈ વિશે શું કહ્યું છે', 'family': 'state_agromet',
                                            'scope': 'state'})
        finally:
            speech.translate, speech.configured = original
        coverage = result['retrieval_coverage']
        self.assertEqual(coverage['match_basis'], 'translated_query_lexical_overlap')
        self.assertEqual(coverage['query_translation']['text'], 'irrigation advice across the state')
        self.assertTrue(coverage['query_translation']['used_for_retrieval'])
        self.assertIn('translated to English for retrieval only', result['answer'])
        self.assertIn('not on the original wording', result['answer'])
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(all('irrigation' in (passage['text'] or '').lower() for passage in result['passages']))

    def test_no_match_names_the_filters_and_substitutes_nothing(self):
        self.publish(document('national_bulletin', 'national', None, '2026-09-14', 'Rainfall summary for the country.'))
        result = self.run_corpus({'places': []}, {'query': 'snow over Leh', 'family': 'national_bulletin', 'scope': 'national'})
        self.assertEqual(result['status'], 'unavailable')
        self.assertIn('nothing was substituted', result['answer'])


class WholeEditionRecallTests(CorpusCase):
    """A whole-edition reading names every printed section, not only the ones it quotes."""

    def edition(self, count):
        sections = [('SECTION %02d' % number, 'Printed text of section %d with enough words to quote.' % number)
                    for number in range(1, count + 1)]
        self.publish(self.multi('national_bulletin', 'national', None, '2026-09-14', sections))

    def test_every_section_is_served_when_the_edition_is_within_the_limit(self):
        self.edition(11)
        result = self.run_corpus({'places': []}, {'query': 'Give me the main points of this bulletin',
                                                  'family': 'national_bulletin', 'scope': 'national'},
                                 question='Give me the main points of the bulletin')
        self.assertEqual(result['whole_document']['sections_indexed'], 11)
        self.assertEqual(result['whole_document']['sections_served'], 11)
        self.assertEqual(len(result['passages']), 11)

    def test_a_longer_edition_names_the_sections_it_did_not_quote(self):
        self.edition(18)
        result = self.run_corpus({'places': []}, {'query': 'Give me the main points of this bulletin',
                                                  'family': 'national_bulletin', 'scope': 'national'},
                                 question='Give me the main points of the bulletin')
        served = result['whole_document']['sections_served']
        self.assertEqual(result['whole_document']['sections_indexed'], 18)
        self.assertLess(served, 18)
        self.assertEqual(result['retrieval_coverage']['sections_listed'], 18)
        self.assertIn('The edition index contains 18 section(s)', result['answer'])
        # The heading and page of every section are named, including the unquoted ones.
        self.assertIn('SECTION 18', result['answer'])
        self.assertIn('Ask about a heading to read that section', result['answer'])
        self.assertEqual(len(result['whole_document']['sections']), 18)

    def test_the_reading_still_says_it_is_bounded(self):
        self.edition(11)
        result = self.run_corpus({'places': []}, {'query': 'Give me the main points of this bulletin',
                                                  'family': 'national_bulletin', 'scope': 'national'},
                                 question='Give me the main points of the bulletin')
        self.assertIn('not its full text', result['answer'])
        self.assertIn('not a completeness claim', result['retrieval_coverage']['scope'])


class RoutingTests(unittest.TestCase):
    def plan(self, quote, kind='agriculture', parameters=None, document_request=None):
        task = {'request_quote': quote, 'kind': kind, 'operation': 'lookup',
                'parameters': parameters or ['agricultural_advisory'], 'years': [], 'period': 'annual',
                'start_local': '', 'end_local': '', 'place_indices': []}
        if document_request is not None:
            task['document_request'] = document_request
        return {'intent': kind, 'language': 'en', 'places': [], 'tasks': [task]}

    def test_a_named_national_product_becomes_a_document_task(self):
        quote = 'What does the latest national weather bulletin say about heavy rainfall?'
        plan = self.plan(quote, document_request={'query': quote, 'crop': '', 'growth_stage': '', 'topic': 'general', 'mode': 'source_lookup'})
        grounded = ground_document_request(plan, quote)
        self.assertEqual(grounded['tasks'][0]['kind'], 'document')
        self.assertEqual(grounded['tasks'][0]['corpus_request']['family'], 'national_bulletin')
        self.assertNotIn('document_request', grounded['tasks'][0])

    def test_a_district_agromet_question_keeps_its_crop_path(self):
        quote = 'What does the agromet advisory bulletin say about cotton in Ahmedabad district?'
        plan = self.plan(quote, document_request={'query': quote, 'crop': 'cotton', 'growth_stage': '', 'topic': 'general', 'mode': 'source_lookup'})
        grounded = ground_document_request(plan, quote)
        self.assertEqual(grounded['tasks'][0]['kind'], 'agriculture')
        self.assertIsNone(document_hint(quote))

    def test_marine_and_state_products_are_recognised(self):
        self.assertEqual(document_hint('what does the coastal weather bulletin say')[0], 'coastal_bulletin')
        self.assertEqual(document_hint('show the sea area bulletin')[0], 'sea_area_bulletin')
        self.assertEqual(document_hint('the state composite agromet bulletin')[0], 'state_agromet')

    def test_a_named_state_is_bound_only_when_the_planner_omits_places(self):
        from weathergpt_data.dialogue import ground_named_place
        plan = {'places': [], 'clarification': '', 'tasks': [{'kind': 'document', 'place_indices': []}]}
        bound = ground_named_place({**plan}, 'What does the Gujarat state agromet bulletin say about irrigation?')
        self.assertEqual([p['name'] for p in bound['places']], ['Gujarat'])
        self.assertEqual(bound['places'][0]['kind'], 'state')
        self.assertEqual(bound['tasks'][0]['place_indices'], [0])
        two = ground_named_place({'places': [], 'clarification': '', 'tasks': [{'kind': 'document', 'place_indices': []}]},
                                 'Compare the Gujarat and Maharashtra bulletins.')
        self.assertEqual(two['places'], [])
        native = ground_named_place({'places': [], 'clarification': '', 'tasks': [{'kind': 'document', 'place_indices': []}]},
                                    'શું ગુજરાત રાજ્યના એગ્રોમેટ બુલેટિનમાં સિંચાઈ વિશે કંઈ કહ્યું છે?')
        self.assertEqual([p['name'] for p in native['places']], ['Gujarat'])
        existing = ground_named_place({'places': [{'name': 'Surat'}], 'clarification': '', 'tasks': [{'kind': 'document', 'place_indices': []}]},
                                      'What does the Gujarat bulletin say?')
        self.assertEqual([p['name'] for p in existing['places']], ['Surat'])

    def test_the_task_schema_refuses_an_unknown_family_and_a_misplaced_request(self):
        base = {'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'], 'years': [],
                'period': 'annual', 'start_local': '', 'end_local': '', 'place_indices': [],
                'corpus_request': {'query': 'x', 'family': 'not_a_family', 'scope': 'national'}}
        with self.assertRaises(SourceError):
            validate_tasks([base], [])
        misplaced = {**base, 'kind': 'forecast', 'corpus_request': {'query': 'x', 'family': '', 'scope': ''}}
        with self.assertRaises(SourceError):
            validate_tasks([misplaced], [])

    def test_the_retrieval_plan_resolves_every_document_source(self):
        from weathergpt_data.capabilities import retrieval_plan
        plan = retrieval_plan({'tasks': [{'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'],
                                          'years': [], 'period': 'annual', 'start_local': '', 'end_local': '',
                                          'place_indices': [], 'corpus_request': {'query': 'x', 'family': 'national_bulletin', 'scope': 'national'}}]})
        self.assertEqual(plan[0]['status'], 'planned')
        self.assertEqual(plan[0]['candidates'][0]['tool'], 'published_documents')
        self.assertEqual(len(plan[0]['candidates'][0]['sources']), 9)
        for source in plan[0]['candidates'][0]['sources']:
            self.assertTrue(source['registry_status'])


class WholeDocumentTests(CorpusCase):
    """A question about the edition is answered from the edition's own structure."""

    SECTIONS = [('SYNOPTIC SITUATION', 'A trough runs from a cyclonic circulation over the north-west.'),
                ('RAINFALL', 'Rainfall was recorded over parts of the state.'),
                ('GENERAL ADVICE', 'Light irrigation is advised where soil moisture is low.'),
                ('GENERAL ADVICE', 'Young seedlings need protection from wind.'),
                ('COASTAL WARNING', 'Storm surge warning: swell waves are likely off the coast.')]

    def publish_edition(self, issue='2026-09-14'):
        return self.publish(self.multi('state_agromet', 'state', 'Gujarat', issue, self.SECTIONS, state='Gujarat'))

    def plan(self):
        return {'places': [{'name': 'Gujarat', 'state': '', 'district': '', 'kind': 'state'}]}

    def test_a_summary_question_serves_one_passage_per_printed_section_in_order(self):
        self.publish_edition()
        result = self.run_corpus(self.plan(), {'query': 'What does the whole Gujarat agromet bulletin say overall?',
                                              'family': 'state_agromet', 'scope': 'state'},
                                 question='What does the whole Gujarat agromet bulletin say overall?')
        self.assertIsNotNone(result['whole_document'])
        self.assertEqual(result['retrieval_coverage']['mode'], 'whole_document_sections')
        self.assertTrue(result['retrieval_coverage']['whole_document'])
        self.assertEqual(result['whole_document']['passages_indexed'], 5)
        self.assertEqual(result['whole_document']['sections_indexed'], 4)
        self.assertEqual(result['whole_document']['passages_served'], 4)
        pages = [item['physical_page'] for item in result['passages']]
        self.assertEqual(pages, sorted(pages), 'Sections are served in printed order')
        self.assertEqual(len({item['section'] for item in result['passages']}), 4, 'One passage per printed section')
        self.assertIn('one per printed section in printed order', result['answer'])
        self.assertIn('not its full text', result['answer'])
        self.assertIn('reference only', result['answer'])

    def test_a_topic_question_is_still_keyword_retrieval(self):
        self.publish_edition()
        result = self.run_corpus(self.plan(), {'query': 'light irrigation soil moisture',
                                              'family': 'state_agromet', 'scope': 'state'},
                                 question='What is the irrigation advice?')
        self.assertIsNone(result['whole_document'])
        # Keyword retrieval, and the words that name the topic rather than the product or the
        # region decide which passages are served.
        self.assertEqual(result['retrieval_coverage']['match_basis'], 'lexical_overlap_topic')
        self.assertTrue(result['retrieval_coverage']['topic_matched'])
        self.assertEqual(result['retrieval_coverage']['topic_tokens'], ['light', 'irrigation', 'soil', 'moisture'])
        self.assertFalse(result['retrieval_coverage']['whole_document'])

    def test_a_summary_without_a_named_product_lists_products_instead_of_guessing(self):
        self.publish_edition()
        self.publish(self.multi('national_bulletin', 'national', None, '2026-09-14',
                                [('SYNOPTIC SITUATION', 'A low pressure area lies over the Bay of Bengal.')]))
        result = self.run_corpus({'places': []}, {'query': 'Give me the main points of the latest bulletin', 'family': '', 'scope': ''},
                                 question='Give me the main points of the latest bulletin')
        self.assertEqual(result['status'], 'needs_clarification')
        self.assertIn('Name one', result['answer'])
        self.assertIn('newest printed issue 2026-09-14', result['answer'])
        self.assertEqual(result['retrieval_coverage']['match_basis'], 'whole_document_needs_product')


class EditionDifferenceTests(CorpusCase):
    """Two editions of one product are compared and named, never ranked."""

    def plan(self):
        return {'places': [{'name': 'Gujarat', 'state': '', 'district': '', 'kind': 'state'}]}

    def test_a_section_the_newer_edition_dropped_is_named_not_hidden(self):
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-10',
                                [('SYNOPTIC SITUATION', 'A trough runs from a cyclonic circulation over the north-west.'),
                                 ('FARMER ADVISORY', 'Cotton sowing is advised after the dry spell ends.')], state='Gujarat'))
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-14',
                                [('SYNOPTIC SITUATION', 'A trough runs from a cyclonic circulation over the north-west.'),
                                 ('RAINFALL', 'Rainfall was recorded over parts of the state.')], state='Gujarat'))
        result = self.run_corpus(self.plan(), {'query': 'cyclonic circulation trough', 'family': 'state_agromet', 'scope': 'state'},
                                 question='What does the synoptic situation say?')
        self.assertEqual(len(result['edition_differences']), 1)
        item = result['edition_differences'][0]
        self.assertEqual(item['kind'], 'section_absent_from_newer')
        self.assertEqual(item['section'], 'FARMER ADVISORY')
        self.assertEqual(item['earlier']['page'], 2)
        self.assertIn('2026-09-10', result['answer'])
        self.assertIn('2026-09-14', result['answer'])
        self.assertIn('is not printed in the', result['answer'])
        self.assertIn('not a withdrawal', result['answer'])
        self.assertIn('does not decide which edition is current', result['answer'])
        self.assertEqual(result['retrieval_coverage']['edition_differences'], 1)

    def test_materially_different_section_text_is_shown_from_both_editions(self):
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-10',
                                [('SYNOPTIC SITUATION', 'A western disturbance lies over the north-west; dry weather is expected.')],
                                state='Gujarat'))
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-14',
                                [('SYNOPTIC SITUATION', 'A low pressure area over the Bay of Bengal is likely to bring rain to the coast.')],
                                state='Gujarat'))
        result = self.run_corpus(self.plan(), {'query': 'low pressure area Bay of Bengal coast', 'family': 'state_agromet', 'scope': 'state'},
                                 question='What does the synoptic situation say?')
        self.assertEqual(len(result['edition_differences']), 1)
        item = result['edition_differences'][0]
        self.assertEqual(item['kind'], 'section_text_differs')
        self.assertLess(item['similarity'], 0.62)
        self.assertIn('differs materially between the', result['answer'])
        self.assertIn('Both editions are retained and none is ranked', result['answer'])

    def test_a_change_question_with_one_edition_says_exactly_that(self):
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-14',
                                [('SYNOPTIC SITUATION', 'A trough runs from a cyclonic circulation over the north-west.')],
                                state='Gujarat'))
        result = self.run_corpus(self.plan(), {'query': 'What changed in the Gujarat agromet bulletin?',
                                              'family': 'state_agromet', 'scope': 'state'},
                                 question='What changed in the Gujarat agromet bulletin?')
        self.assertEqual(result['edition_differences'], [])
        self.assertEqual(result['edition_comparison']['state'], 'single_edition_indexed')
        self.assertEqual(result['edition_comparison']['newest_issue'], '2026-09-14')
        self.assertEqual(result['retrieval_coverage']['edition_comparison'], 'single_edition_indexed')
        self.assertEqual(result['retrieval_coverage']['editions_indexed_for_this_product'], 1)
        self.assertIn('no earlier edition can be compared', result['answer'])
        self.assertIn('not a statement that nothing changed', result['answer'])

    def test_two_editions_report_a_comparison_state_not_a_single_edition_state(self):
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-10',
                                [('SYNOPTIC SITUATION', 'A western disturbance lies over the north-west.')], state='Gujarat'))
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-14',
                                [('SYNOPTIC SITUATION', 'A low pressure area lies over the Bay of Bengal.')], state='Gujarat'))
        result = self.run_corpus(self.plan(), {'query': 'What changed in the Gujarat agromet bulletin?',
                                              'family': 'state_agromet', 'scope': 'state'},
                                 question='What changed in the Gujarat agromet bulletin?')
        self.assertEqual(result['edition_comparison']['state'], 'compared')
        self.assertEqual(result['edition_comparison']['editions_indexed'], 2)
        self.assertNotIn('no earlier edition can be compared', result['answer'])

    def test_one_edition_reports_no_comparison(self):
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-14',
                                [('SYNOPTIC SITUATION', 'A trough runs from a cyclonic circulation over the north-west.')],
                                state='Gujarat'))
        result = self.run_corpus(self.plan(), {'query': 'cyclonic circulation trough', 'family': 'state_agromet', 'scope': 'state'},
                                 question='What does the synoptic situation say?')
        self.assertEqual(result['edition_differences'], [])
        self.assertNotIn('Editions compared', result['answer'])




class TaskMergeTests(CorpusCase):
    """The corpus reading travels with the passages into the turn result."""

    def test_the_whole_document_reading_and_comparison_reach_the_turn(self):
        from weathergpt_data.task_dispatch import execute_plan
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-10',
                                [('SYNOPTIC SITUATION', 'A western disturbance lies over the north-west.')], state='Gujarat'))
        self.publish(self.multi('state_agromet', 'state', 'Gujarat', '2026-09-14',
                                [('SYNOPTIC SITUATION', 'A low pressure area lies over the Bay of Bengal.'),
                                 ('RAINFALL', 'Rainfall was recorded over parts of the state.')], state='Gujarat'))
        plan = {'places': [{'name': 'Gujarat', 'state': '', 'district': '', 'kind': 'state'}], 'tasks': [
            {'kind': 'document', 'operation': 'lookup', 'parameters': ['published_document'],
             'place_indices': [0], 'years': [], 'period': 'sep', 'start_local': '', 'end_local': '',
             'request_quote': 'What changed overall?',
             'corpus_request': {'query': 'What changed in the whole Gujarat agromet bulletin?',
                                'family': 'state_agromet', 'scope': 'state'}}],
            'variables': [], 'assumptions': [], 'clarification': None}
        result = {'question': 'What changed in the whole Gujarat agromet bulletin?', 'plan': plan,
                  'trace': {'tools': [], 'generation': None}, 'facts': [], 'citations': [],
                  'task_results': [], 'charts': [], 'calculations': [], 'passages': [], 'document_evidence': [],
                  'airport_reports': [], 'warning_evidence': [], 'pending_slots': [], 'retrieval_coverage': [],
                  'notes': [], 'choices': [], 'status': 'needs_clarification', 'answer': ''}
        outcome = execute_plan(self.engine, result, plan, {}, None)
        self.assertTrue(outcome['whole_document'], 'the whole-document reading reaches the turn result')
        self.assertEqual(outcome['whole_document']['passages_indexed'], 2)
        self.assertEqual(outcome['edition_comparison']['state'], 'compared')
        self.assertEqual(len(outcome['edition_differences']), 1)
        self.assertEqual(outcome['edition_differences'][0]['kind'], 'section_text_differs')
        self.assertTrue(any(entry.get('whole_document') for entry in outcome['retrieval_coverage']))


if __name__ == '__main__':
    unittest.main()
