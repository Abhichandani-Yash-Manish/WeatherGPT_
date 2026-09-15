"""Source-based parent context and task isolation; no agronomic acceptance claim."""
import copy
import unittest
from unittest.mock import patch

from weathergpt_data.bulletin_index import extract
from weathergpt_data.bulletin_context import parent_context, qualification_flags
from weathergpt_data.transport import SourceError
from test_bulletin_retrieval import ROOT, NOW, SOURCES
import test_bulletin_retrieval as bulletin_fixtures
from source_fixtures import source_fixture
from test_product_stage_one import task

DIBRUGARH = ('Dibrugarh', 'Assam', '57e47b6892371cb3a87f9aa9ca648deee8adaa055f5bc36f7c935b00263ec8ee')


class ParentSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.contexts = {}, {}
        for district, state, sha in SOURCES + [DIBRUGARH]:
            raw = source_fixture(sha)
            doc = extract(raw.read_bytes(), state, district, NOW)
            doc['provenance'] = {'raw_file': str(raw)}
            cls.docs[district] = doc
            cls.contexts[district] = parent_context(doc)

    def test_cross_page_heading_keeps_body_page_and_excludes_print_furniture(self):
        sections, _ = self.contexts['Dibrugarh']
        general = next(s for s in sections if s['section'] == 'General Advisory:')
        self.assertEqual((general['heading_page'], general['page']), (1, 2))
        self.assertIn('farmers can continue their farm operations', general['text'])
        self.assertNotIn('District Advisory', general['text'])
        self.assertNotIn('https://', general['text'])
        self.assertNotIn('SMS Advisory', general['text'])

    def test_far_page_restriction_is_not_lost_behind_crop_filter(self):
        sections, coverage = self.contexts['Dibrugarh']
        impacts = next(s for s in sections if s['section'] == 'Impact based advisories (General)')
        self.assertEqual(impacts['page'], 3)
        self.assertIn('Avoid working in the fields during thunderstorm/lightning period', impacts['text'])
        self.assertIn('Postpone sowing of rice, jute, maize and vegetables', impacts['text'])
        flags = qualification_flags([c for c in self.docs['Dibrugarh']['chunks'] if c['crop_key'] == 'rice'], sections)
        self.assertEqual([f['activity'] for f in flags], ['sowing'])
        self.assertIn(impacts['id'], flags[0]['passage_ids'])

    def test_unreadable_section_is_disclosed_not_silently_cleaned(self):
        sections, coverage = self.contexts['Dibrugarh']
        self.assertEqual(coverage['status'], 'partial')
        self.assertEqual(coverage['omitted_sections'][0]['section'], 'Likely impacts of weather warnings (General)')
        self.assertFalse(any('(cid:' in s['text'] for s in sections))

    def test_warning_heading_and_body_dates_do_not_become_current_alert(self):
        sections, coverage = self.contexts['Dibrugarh']
        warning = next(s for s in sections if s['section'].startswith('Weather Warnings'))
        self.assertIn('08:30 IST of the next day', warning['section'])
        self.assertIn('12th to 14th September, 2026', warning['text'])
        self.assertFalse(coverage['dissemination_eligible'])
        self.assertIn('unverified', warning['applicability'])

    def test_no_warning_phrase_preserves_its_source_date(self):
        sections, _ = self.contexts['Coimbatore']
        warning = next(s for s in sections if s['section'] == 'Weather Warning')
        self.assertIn('16.09.2026 : No Warning', warning['text'])
        self.assertIn('12.09.2026 to 15.09.2026', warning['text'])
        self.assertNotIn('stake banana', warning['text'])
        self.assertTrue(any('stake banana' in s['text'] for s in sections))

    def test_general_row_reuses_source_identity_without_becoming_crop_match(self):
        sections, _ = self.contexts['Ahmedabad']
        general = next(s for s in sections if s['section'] == 'General advice')
        source = next(c for c in self.docs['Ahmedabad']['chunks'] if c['id'] == general['source_chunk_id'])
        self.assertEqual(general['text'], source['text'])
        self.assertNotEqual(general['id'], source['id'])
        self.assertEqual(general['crop_key'], '')
        self.assertIn('optimum soil moisture', general['text'])

    def test_parent_context_does_not_inherit_another_crop_stage(self):
        for sections, _ in self.contexts.values():
            self.assertTrue(all(s['crop_key'] == '' and s['stage'] == '' for s in sections))
            self.assertTrue(all('4.5 kg/bigha' not in s['text'] for s in sections))

    def test_na_is_preserved_as_source_text_not_an_all_clear(self):
        sections, _ = self.contexts['Kamrup']
        self.assertEqual(sum(s['text'] == 'NA' for s in sections), 3)
        self.assertTrue(all('unverified' in s['applicability'] for s in sections))

    def test_hash_change_cannot_attach_context_to_another_document(self):
        d = copy.deepcopy(self.docs['Kamrup']); d['sha256'] = 'a' * 64
        with self.assertRaisesRegex(SourceError, 'hash mismatch'):
            parent_context(d)

    def test_held_surat_and_madurai_editions_are_still_rejected(self):
        for name, state, sha in [('Surat', 'Gujarat', '5e8120cf3b228944634faa709f524f3a76c0c4e043635e4a3fce7b4739bcf9bb'), ('Madurai', 'Tamil Nadu', '2a5c1798e89380e862a2c429522f7a1c18b459f912bf600c1d449c787954b730')]:
            with self.assertRaises(SourceError):
                extract(source_fixture(sha).read_bytes(), state, name, NOW)

    def test_stop_pest_movement_is_not_a_spraying_prohibition(self):
        snippets = [{'id': 'a', 'text': 'To stop the movement of pests, spray the bunds.'},
                    {'id': 'b', 'text': 'Farmers can continue spraying.'}]
        self.assertEqual(qualification_flags(snippets, []), [])


class ParentEngineTests(unittest.TestCase):
    setUp = bulletin_fixtures.EngineDocumentTests.setUp
    publish = bulletin_fixtures.EngineDocumentTests.publish
    add_place = bulletin_fixtures.EngineDocumentTests.add_place
    ask = bulletin_fixtures.EngineDocumentTests.ask
    chat = bulletin_fixtures.EngineDocumentTests.chat
    setup_document = bulletin_fixtures.EngineDocumentTests.setup_document

    def context(self, status='extracted_scoped'):
        self.setup_document()
        section = {'id': 'parent1', 'section': 'Weather Warning', 'page': 1,
                   'text': 'Published warning with its original condition.',
                   'crop': '', 'stage': '', 'document_sha256': 'a' * 64,
                   'evidence_kind': 'published_bulletin_context'}
        coverage = {'status': status, 'omitted_sections': []}
        return section, patch('weathergpt_data.document_tools.parent_context', return_value=([section], coverage))

    def test_parent_passages_have_same_task_and_pdf_citation(self):
        section, mocked = self.context()
        with mocked:
            r = self.chat(question='cotton bulletin')
        self.assertEqual(r['status'], 'answered')
        self.assertEqual(len(r['passages']), 2)
        self.assertEqual(r['retrieval_coverage'][0]['returned'], 1)
        self.assertEqual(r['retrieval_coverage'][0]['parent_context']['attached'], 1)
        self.assertEqual(r['passages'][1]['citation_ids'], r['passages'][0]['citation_ids'])
        self.assertIn(section['text'], r['answer'])

    def test_missing_parent_context_marks_crop_result_partial(self):
        section, mocked = self.context('unavailable')
        with mocked:
            r = self.chat(question='cotton bulletin')
        self.assertEqual(r['status'], 'partial')
        self.assertEqual(r['task_coverage']['completed'], 0)
        self.assertIn('Bulletin context is incomplete', r['answer'])

    def test_explanation_preserves_structured_context_gaps(self):
        section, mocked = self.context('partial')
        with mocked:
            first = self.chat(question='cotton bulletin')
        self.model.value.update(context_action='explain_previous', changed_fields=[])
        second = self.chat(question='Explain that', conversation_id=first['conversation_id'])
        self.assertEqual(second['retrieval_coverage'], first['retrieval_coverage'])
        self.assertEqual(second['status'], 'partial')
        self.assertEqual(second['passages'], first['passages'])

    def test_context_does_not_leak_into_forecast_or_fill_missing_crop(self):
        section, mocked = self.context()
        p = self.model.value
        p['tasks'].append(task(kind='forecast', years=[], parameters=['precipitation'],
                              start_local=p['start_local'], end_local=p['end_local']))
        with mocked:
            r = self.chat(question='cotton bulletin and rain')
        self.assertEqual(r['task_results'][1]['passage_ids'], [])
        self.assertTrue(all(x['task_id'] == 't1' for x in r['passages']))

    def test_no_crop_match_does_not_fall_back_to_general_context(self):
        doc, index = self.setup_document(crop='wheat')
        index.search.return_value = (doc, [], {'candidates': 0})
        with patch('weathergpt_data.document_tools.parent_context') as mocked:
            r = self.chat(question='wheat bulletin')
        mocked.assert_not_called()
        self.assertFalse(r.get('passages'))
        self.assertEqual(r['status'], 'unavailable')
