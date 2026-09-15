"""Two generalisation gaps the sealed holdout exposed, repaired and pinned.

Reproduced on 15 September 2026 from the sealed holdout's misses:

1. \"Will it rain in Ahmedbad, Gujrat tomorrow?\" was refused although the city matched, because a
   misspelt *state* name emptied the candidate list. The state is now resolved against the indexed
   names, bounded to a close and clearly-ahead match, disclosed in the answer, and never guessed
   into a different state.
2. \"the Kerala coast\" is a region, not a settlement. It used to be searched as one and offered
   twenty villages called Kerla in Rajasthan. A coast or sea word now marks the place as a sea area,
   the resolver leaves it for the tools, and the warning tool asks for a district or a port on it
   instead of attaching official guidance to the wrong place. A place named after a preposition
   with an article (\"in the Ahmedabad district\") is also read now, and 'off Kochi' is a place.
"""
import unittest
from datetime import datetime, timezone

from weathergpt_data.gazetteer import Gazetteer
from weathergpt_data.rule_planner import places_of

NOW = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)


class StateSpellingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = Gazetteer()

    def test_a_misspelt_state_still_finds_the_place_and_says_how_it_was_read(self):
        rows = self.index.search('Ahmedbad', 'Gujrat')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'Ahmedabad')
        self.assertIn('closest name to Gujrat', rows[0]['state_match_basis'])

    def test_an_exact_state_says_nothing_because_there_is_nothing_to_disclose(self):
        rows = self.index.search('Ahmedabad', 'Gujarat')
        self.assertEqual(rows[0]['state_match_basis'], '')

    def test_a_state_that_is_not_close_enough_is_refused_rather_than_swapped(self):
        self.assertEqual(self.index.search('Ahmedabad', 'Kerala'), [])
        self.assertEqual(self.index.search('Ahmedabad', 'Zzzzzz'), [])


class SeaAreaTests(unittest.TestCase):
    def test_a_coast_is_a_region_not_a_settlement(self):
        found = places_of('Are there warnings for the Kerala coast?')
        self.assertEqual([(item['name'], item['kind']) for item in found], [('Kerala', 'sea_area')])

    def test_a_sea_named_in_the_question_is_marked_but_keeps_its_region_name(self):
        found = places_of('What are the waves in the Arabian Sea?')
        self.assertEqual([(item['name'], item['kind']) for item in found], [('Arabian', 'sea_area')])

    def test_a_port_after_off_is_a_place(self):
        found = places_of('what are the waves off Kochi')
        self.assertEqual([(item['name'], item['kind']) for item in found], [('Kochi', 'unknown')])

    def test_a_compound_question_keeps_both_the_coast_and_the_port(self):
        found = places_of('Are there warnings for the Kerala coast and what are the waves off Kochi?')
        self.assertEqual([(item['name'], item['kind']) for item in found],
                         [('Kerala', 'sea_area'), ('Kochi', 'unknown')])

    def test_an_article_between_the_preposition_and_the_place_is_read(self):
        found = places_of('Will it rain in the Ahmedabad district tomorrow?')
        self.assertEqual(found[0]['name'], 'Ahmedabad')
        plain = places_of('Is there a warning for Patna, Bihar?')
        self.assertEqual((plain[0]['name'], plain[0]['state']), ('Patna', 'Bihar'))


if __name__ == '__main__':
    unittest.main()