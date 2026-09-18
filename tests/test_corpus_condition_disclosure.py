"""The reconciled condition, carried through a real corpus answer.

`tests/test_activity_condition_reconciliation.py` pins the wording rule. This file pins what the reader
actually receives: that an edition which restricts spraying in rain and permits it in dry weather is
answered as one rule with its condition named, and is no longer reduced to partial for wording the
document itself had already qualified — while an edition that genuinely does not separate the two keeps
both the conflict sentence and the partial status.

The passages are the sentences indexed on this machine from the Tumakuru (2026-09-11) and Dibrugarh
(2026-09-11) district agromet editions. This is a component check over the answer path; it is not
acceptance of either advisory, and nothing here decides whether a condition holds at a field.
"""
import unittest

from tests.test_corpus_reachability import CorpusReachability, document


class ConditionDisclosureTests(CorpusReachability):
    def corpus_answer(self, texts, question):
        sha = self.publish(document('district_agromet', 'district', 'Tumakuru', '2026-09-11', texts,
                                    state='Karnataka'))
        plan = {'output_language': 'en',
                'places': [{'name': 'Tumakuru', 'state': 'Karnataka', 'district': 'Tumakuru', 'kind': 'district'}]}
        result = self.run_corpus(plan, {'query': question, 'family': 'district_agromet', 'scope': 'district'},
                                 question=question)
        return sha, result

    def test_a_reconciled_rule_is_stated_once_with_its_condition_and_is_not_partial(self):
        _, result = self.corpus_answer(
            ['The limited rainfall forecast suggests that most farm operations can continue, but crop-protection '
             'and spraying activities should be undertaken only during rain-free periods with clear skies, '
             'preferably after dew has dried in the morning.',
             'Avoid spraying during rainfall or strong winds.'],
            'What does the district agromet bulletin say about spraying?')
        answer = result['answer']
        self.assertIn('one rule in two places', answer)
        self.assertIn('rain', answer)
        self.assertIn('dry', answer)
        # The old wording announced opposition. It must not appear for an edition that qualified itself.
        self.assertNotIn('Opposing wording was found', answer)
        coverage = result['retrieval_coverage']
        self.assertEqual(coverage['activity_conflicts_unresolved'], [])
        self.assertEqual([flag['activity'] for flag in coverage['activity_conditional_guidance']], ['spraying'])
        self.assertEqual(result['status'], 'answered')

    def test_the_reconciliation_does_not_claim_the_condition_holds(self):
        """Reconciling the wording is not a field decision, and the answer has to say so itself."""
        _, result = self.corpus_answer(
            ['In case of urgency, spraying of pesticides can be done in dry weather only.',
             'Do not spray if rain is about to happen.'],
            'Can I spray today?')
        self.assertIn('not established', result['answer'])

    def test_wording_the_edition_does_not_separate_stays_a_disclosed_conflict(self):
        _, result = self.corpus_answer(
            ['Taking advantage of the suitable weather condition in the coming 5 days, farmers can continue their '
             'farm operations like land preparation, sowing, transplanting.',
             'Postpone sowing of rice, jute, maize and vegetables.'],
            'What does the district agromet bulletin say about sowing?')
        answer = result['answer']
        self.assertIn('Opposing wording was found', answer)
        self.assertIn('does not separate the two by a weather condition', answer)
        self.assertEqual([flag['activity'] for flag in result['retrieval_coverage']['activity_conflicts_unresolved']],
                         ['sowing'])
        self.assertEqual(result['status'], 'partial')


if __name__ == '__main__':
    unittest.main()
