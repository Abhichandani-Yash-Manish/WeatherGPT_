"""Opposing activity wording that the edition's own weather condition reconciles.

The check these cover used to report any restriction beside any permission as an unresolved conflict.
Measured against this machine's indexed corpus (7,372 passages, 590 documents) it fired on 7 of 595
document-regions, and two of those were not conflicts: the Tumakuru (11 September 2026) and Keonjhar
(12 September 2026) district agromet editions each state one spraying rule twice — restricted in rain,
permitted in dry weather. The answer was marked partial for wording the document itself had already
qualified.

Every sentence quoted below is copied from those indexed passages. These are component checks over the
wording rule, not acceptance of any advisory: nothing here decides whether a condition holds at a field,
and the reconciliation resolves wording, never agronomy.
"""
import unittest

from weathergpt_data.bulletin_context import qualification_flags, unresolved_conflicts


def passage(identifier, text):
    return {'id': identifier, 'text': text}


# Copied from the Tumakuru edition indexed on this machine, issue 2026-09-11.
TUMAKURU = [
    passage('tk-1', 'The limited rainfall forecast suggests that most farm operations can continue, but '
                    'crop-protection and spraying activities should be undertaken only during rain-free periods '
                    'with clear skies, preferably after dew has dried in the morning.'),
    passage('tk-2', 'Avoid spraying during rainfall or strong winds.'),
]

# Copied from the Keonjhar edition indexed on this machine, issue 2026-09-12.
KEONJHAR = [
    passage('kj-1', 'In case of urgency, spraying of pesticides can be done in dry weather only.'),
    passage('kj-2', 'Do not spray if rain is about to happen.'),
    passage('kj-3', 'Do not spray in rainy condition.'),
]


class ReconciliationTests(unittest.TestCase):
    def test_tumakuru_states_one_rule_twice_and_is_not_an_unresolved_conflict(self):
        flags = qualification_flags(TUMAKURU, [])
        self.assertEqual([flag['kind'] for flag in flags], ['activity_conditional_guidance'])
        self.assertEqual(flags[0]['activity'], 'spraying')
        self.assertEqual(unresolved_conflicts(flags), [])

    def test_keonjhar_reconciles_too_and_keeps_every_passage_id(self):
        flags = qualification_flags(KEONJHAR, [])
        self.assertEqual([flag['kind'] for flag in flags], ['activity_conditional_guidance'])
        self.assertEqual(flags[0]['passage_ids'], ['kj-1', 'kj-2', 'kj-3'])
        self.assertEqual(unresolved_conflicts(flags), [])

    def test_the_reconciliation_names_both_states_rather_than_asserting_one(self):
        """A reconciled flag has to say what the edition restricts and what it permits. A flag that only
        said 'reconciled' would be the product deciding something it has not shown the reader."""
        flag = qualification_flags(KEONJHAR, [])[0]
        self.assertIn('rain', flag['restricted_when'])
        self.assertIn('dry', flag['permitted_when'])
        self.assertTrue(all(clause for clause in flag['clauses']))

    def test_opposing_wording_with_no_condition_still_stands_unresolved(self):
        """The Dibrugarh shape, which is a real tension: a general permission to continue farm operations
        beside a specific instruction to postpone sowing of named crops. Neither clause names a weather
        state, so nothing here separates them and the flag must not be cleared."""
        evidence = [
            passage('db-1', 'Taking advantage of the suitable weather condition in the coming 5 days, farmers can '
                            'continue their farm operations like land preparation, sowing, transplanting.'),
            passage('db-2', 'Postpone sowing of rice, jute, maize and vegetables.'),
        ]
        flags = qualification_flags(evidence, [])
        self.assertEqual([flag['kind'] for flag in flags], ['potential_activity_conflict'])
        self.assertEqual(len(unresolved_conflicts(flags)), 1)

    def test_a_restriction_on_a_weather_state_beside_an_unqualified_permission_is_not_reconciled(self):
        """Half a condition is not a separation. "Avoid spraying during rain" beside a flat "spraying can
        be done" leaves the reader with a real question, so the conflict stands."""
        evidence = [
            passage('x-1', 'Avoid spraying during rainfall or strong winds.'),
            passage('x-2', 'Spraying of pesticides can be done.'),
        ]
        flags = qualification_flags(evidence, [])
        self.assertEqual([flag['kind'] for flag in flags], ['potential_activity_conflict'])

    def test_an_unclassifiable_condition_never_counts_as_a_distinguishing_one(self):
        """The qualifier reader is bounded to the weather states these editions name. A condition it does
        not recognise leaves the clause unqualified, which keeps the conflict rather than clearing it on a
        condition nobody checked."""
        evidence = [
            passage('y-1', 'Avoid spraying when the market price is low.'),
            passage('y-2', 'Spraying can be done after consulting the block officer.'),
        ]
        flags = qualification_flags(evidence, [])
        self.assertEqual([flag['kind'] for flag in flags], ['potential_activity_conflict'])

    def test_wording_that_was_never_a_conflict_is_still_not_one(self):
        self.assertEqual(qualification_flags([passage('a', 'To stop the movement of pests, spray the bunds.'),
                                              passage('b', 'Farmers can continue spraying.')], []), [])

    def test_each_activity_is_judged_on_its_own_wording(self):
        """A reconciled spraying rule must not clear an unresolved sowing conflict in the same edition."""
        flags = qualification_flags(TUMAKURU + [
            passage('mix-1', 'Postpone sowing of rice, jute, maize and vegetables.'),
            passage('mix-2', 'Continue sowing in the main field.'),
        ], [])
        kinds = {flag['activity']: flag['kind'] for flag in flags}
        self.assertEqual(kinds['spraying'], 'activity_conditional_guidance')
        self.assertEqual(kinds['sowing'], 'potential_activity_conflict')
        self.assertEqual([flag['activity'] for flag in unresolved_conflicts(flags)], ['sowing'])


if __name__ == '__main__':
    unittest.main()
