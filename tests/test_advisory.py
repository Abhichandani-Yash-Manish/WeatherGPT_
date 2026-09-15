"""The advisory brief: published crop advice quoted, the forecast kept apart, no prescription.

These are component checks over a synthetic index. They take no measurement of any publisher.
What they pin is the discipline the review asked for: advice is quoted with its page and printed
issue date, another crop's passages are never served for the requested crop, a missing edition is
reported rather than substituted, decision support names what it does not know, and nothing here
becomes a dose, a diagnosis or a go/no-go decision.
"""
import json
import tempfile
import unittest
from pathlib import Path

from weathergpt_data.advisory import compose, markdown, resolve_indexed_name
from weathergpt_data.bulletin_index import BulletinIndex
from weathergpt_data.transport import digest

COTTON = ('Cotton Squaring/ Flowering/ Boll formation If irrigation facilities are available then apply need based '
          'irrigation through drip irrigation by considering soil moisture condition in standing crop.')
GROUNDNUT = ('Groundnut Flowering/ Pod formation Leaf-eating caterpillar in groundnut can be controlled by installing '
             'pheromone traps and by need based spray.')
GENERAL = ('Advisory General advice Undertake interculturing and weeding operations to conserve moisture in standing '
           'crops and apply need based light irrigation by considering weather and soil moisture condition.')


def encoder(texts, query=False):
    return [[1.0, 0.5] for _ in texts]


def passage(sha, family, scope, region, issue, text, page=1, source_id='S57'):
    item = {'document_sha256': sha, 'family': family, 'scope': scope, 'region': region, 'section': None,
            'text': text, 'physical_page': page, 'passage_index': page, 'source_locator': 'physical PDF page %d' % page,
            'issue_date': issue, 'language': 'en', 'text_quality': 'text_layer_clean', 'source_id': source_id,
            'extraction_version': 'document-passages-v1'}
    item['id'] = digest(json.dumps(item, sort_keys=True, ensure_ascii=False).encode())
    return item


def document(family, scope, region, issue, sections, state=None, source_id='S57'):
    sha = digest((family + '|' + str(region) + '|' + str(issue)).encode())
    rows = [passage(sha, family, scope, region, issue, text, page=number, source_id=source_id)
            for number, text in enumerate(sections, 1)]
    body = {'sha256': sha, 'family': family, 'scope': scope, 'region': region, 'language': 'en', 'pages': len(rows),
            'source_id': source_id, 'extraction_status': 'text_layer_extracted_reading_order_unverified',
            'currency': 'printed_issue_differs_from_retrieval_date', 'age_days': 4, 'quarantined_pages': [],
            'passages': rows}
    if state:
        body['source_state'] = state
    return body


class AdvisoryCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = BulletinIndex(Path(self.tmp.name) / 'index.sqlite')

    def publish(self, body):
        self.index.publish_document(body, {'sha256': body['sha256'], 'blob': None}, '2026-09-15T06:00:00+00:00',
                                    encoder=encoder)
        return body['sha256']

    def district_edition(self, region='Ahmedabad'):
        self.publish(document('district_agromet', 'district', region, '2026-09-11', [COTTON, GROUNDNUT, GENERAL],
                              state='Gujarat'))

    def state_edition(self):
        self.publish(document('state_agromet', 'state', 'Gujarat', '2026-09-14', [COTTON, GENERAL], state='Gujarat'))

    def brief(self, **overrides):
        request = {'region': 'Ahmedabad', 'state': 'Gujarat', 'crop': 'cotton', 'stage': '', 'topic': 'irrigation',
                   'mode': 'source_lookup', 'window': None, 'point': None}
        request.update(overrides)
        return compose(self.index, request, encoder=encoder,
                       forecast=[{'parameter': 'precipitation', 'value': '0.0', 'unit': 'mm',
                                  'start': '2026-09-15T00:00:00+00:00', 'end': '2026-09-15T23:00:00+00:00',
                                  'source_id': 'S62', 'label': 'precipitation'}])


class CompositionTests(AdvisoryCase):
    def test_a_crop_brief_quotes_only_that_crop_and_says_what_it_left_out(self):
        self.district_edition()
        brief = self.brief()
        self.assertEqual(brief['status'], 'ok')
        crops = {passage['crop'] for passage in brief['published_advice']['passages']}
        self.assertIn('cotton', crops)
        self.assertNotIn('groundnut', crops, 'another crop must never be served for the requested one')
        limits = ' '.join(brief['not_established'])
        self.assertIn('groundnut', limits, 'the brief says which crops it left out')

    def test_advice_carries_its_page_printed_issue_and_source(self):
        self.district_edition()
        passage = self.brief()['published_advice']['passages'][0]
        for field in ('source_id', 'page', 'issue_date', 'quote', 'source_locator'):
            self.assertIn(field, passage)
        self.assertEqual(passage['issue_date'], '2026-09-11')
        self.assertEqual(passage['source_id'], 'S57')
        self.assertTrue(passage['quote'])

    def test_the_sources_own_conditions_are_quoted_as_conditions(self):
        self.district_edition()
        brief = self.brief()
        conditions = brief['conditions_named_by_the_source']
        self.assertTrue(conditions, 'the cotton passage states a condition')
        self.assertTrue(any('irrigation facilities are available' in clause.lower() for clause in conditions),
                        'the condition is quoted, not paraphrased')

    def test_a_crop_the_edition_does_not_name_is_disclosed_and_only_general_advice_is_served(self):
        self.district_edition()
        brief = self.brief(crop='wheat')
        self.assertEqual(brief['status'], 'ok')
        limits = ' '.join(brief['not_established'])
        self.assertIn('does not name wheat', limits, 'the brief says the edition does not name the crop asked about')
        self.assertTrue(brief['published_advice']['passages'], 'general advice for the district is still served')
        self.assertTrue(all(not passage['crop'] for passage in brief['published_advice']['passages']),
                        'no other crop\'s passage is served for wheat')

    def test_a_request_nothing_matches_is_reported_rather_than_approximated(self):
        self.district_edition()
        brief = self.brief(crop='cardamom', topic='harvest')
        self.assertEqual(brief['status'], 'not_available')
        self.assertIn('does not name cardamom', brief['why'])

    def test_a_district_without_an_edition_falls_back_to_the_state_edition_and_says_so(self):
        self.state_edition()
        brief = self.brief(region='Anand')
        self.assertEqual(brief['status'], 'ok')
        self.assertEqual(brief['published_advice']['family'], 'state_agromet')
        self.assertEqual(brief['published_advice']['region'], 'Gujarat')
        self.assertIn('No district edition matched', ' '.join(brief['not_established']))

    def test_decision_support_names_what_is_missing_and_refuses_a_decision(self):
        self.district_edition()
        brief = self.brief(mode='decision_support')
        self.assertIn('decision_support', brief)
        support = brief['decision_support']
        self.assertIn('soil moisture at the field', support['what_is_missing_for_a_decision'])
        self.assertIn('will not turn published advice into a go/no-go decision', support['statement'])

    def test_the_forecast_is_context_with_samples_and_no_summary(self):
        self.district_edition()
        brief = self.brief()
        self.assertEqual(brief['forecast']['status'], 'retrieved')
        self.assertIn('no summary is computed here', brief['forecast']['note'])
        self.assertEqual(brief['forecast']['values'][0]['parameter'], 'precipitation')

    def test_no_prescription_diagnosis_or_dose_decision_appears(self):
        self.district_edition()
        text = markdown(self.brief(mode='decision_support')).lower()
        for forbidden in ('you should spray', 'recommended dose', 'we recommend', 'safe to spray'):
            self.assertNotIn(forbidden, text)
        self.assertIn('does not diagnose crop symptoms', text)
        self.assertIn('not a prescription for a field', text)

    def test_the_brief_identity_is_stable_for_the_same_evidence(self):
        self.district_edition()
        first, second = self.brief(), self.brief()
        self.assertEqual(first['brief_id'], second['brief_id'])
        self.assertNotEqual(first['brief_id'], self.brief(mode='decision_support')['brief_id'])


class NameResolutionTests(AdvisoryCase):
    def test_a_spelling_the_publisher_does_not_use_is_read_to_the_indexed_name(self):
        self.district_edition()
        name, why = resolve_indexed_name(self.index, 'district_agromet', 'district', 'Ahmadabad')
        self.assertEqual(name, 'Ahmedabad')
        self.assertTrue(why)

    def test_an_unrelated_name_is_refused_rather_than_approximated(self):
        self.district_edition()
        name, why = resolve_indexed_name(self.index, 'district_agromet', 'district', 'Kohima')
        self.assertIsNone(name)
        self.assertIn('close enough', why)

    def test_a_family_with_no_indexed_edition_is_reported_as_such(self):
        name, why = resolve_indexed_name(self.index, 'district_agromet', 'district', 'Ahmedabad')
        self.assertIsNone(name)
        self.assertIn('no edition of this family is indexed', why)


if __name__ == '__main__':
    unittest.main()
