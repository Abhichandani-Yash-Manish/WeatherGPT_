"""The reviewed settlement crosswalk: the names people use, not the ones the catalogue indexes.

Every entry here is a measured failure, not a guess at what is famous. Thirty-five well-known Indian
cities and towns were asked about on 20 September 2026; thirty-one resolved without help.
"""
import unittest

from weathergpt_data import settlement_aliases as aliases
from weathergpt_data.gazetteer import norm


class TableTests(unittest.TestCase):
    def test_every_entry_states_its_basis_and_confidence(self):
        """An unexplained crosswalk entry is the thing this project refuses to ship."""
        for entry in aliases.RENAMES + aliases.PREFERENCES:
            with self.subTest(entry=entry.get('was') or entry.get('name')):
                self.assertTrue(entry['basis'].strip())
                self.assertIn(entry['confidence'], {'high', 'medium'})

    def test_no_name_is_both_renamed_and_preferred(self):
        """The two mechanisms differ: one retries a search, the other picks from its results."""
        renamed = {aliases._norm(e['was']) for e in aliases.RENAMES}
        preferred = {aliases._norm(e['name']) for e in aliases.PREFERENCES}
        self.assertFalse(renamed & preferred)

    def test_a_diacritic_spelling_still_matches_its_entry(self):
        """The catalogue spells the Himachal town "Manāli".

        Folding case alone left "man li" once the macron fell to the punctuation class, so the entry
        never matched the place it names and Manali kept asking.
        """
        self.assertIsNotNone(aliases.preference_for('Manāli'))
        self.assertIsNotNone(aliases.preference_for('MANALI'))
        self.assertIsNotNone(aliases.preference_for('  manali '))

    def test_a_rename_resolves_only_the_names_it_lists(self):
        self.assertEqual(aliases.rename_for('Calicut')[0], 'Kozhikode')
        self.assertEqual(aliases.rename_for('gurgaon')[0], 'Gurugram')
        self.assertIsNone(aliases.rename_for('Kozhikode'))
        self.assertIsNone(aliases.rename_for('Mumbai'))
        self.assertIsNone(aliases.rename_for(''))


class PreferenceTests(unittest.TestCase):
    def match(self, admin1, admin2, name='Kochi'):
        return {'name': name, 'admin1': admin1, 'admin2': admin2, 'id': admin1 + admin2}

    def test_it_chooses_the_one_candidate_the_entry_names(self):
        matches = [self.match('State of Mahārāshtra', 'Yavatmal'),
                   self.match('State of Kerala', 'Ernākulam')]
        chosen, why = aliases.prefer('Kochi', matches, norm)
        self.assertEqual(chosen['admin1'], 'State of Kerala')
        self.assertIn('settlement-crosswalk-v1', why)

    def test_it_introduces_nothing_when_the_named_place_is_absent(self):
        """A preference is a choice among candidates, never a new place."""
        matches = [self.match('State of Mahārāshtra', 'Yavatmal'),
                   self.match('State of Mahārāshtra', 'Bhandara')]
        self.assertEqual(aliases.prefer('Kochi', matches, norm), (None, None))

    def test_it_decides_nothing_when_two_candidates_match_the_entry(self):
        """Ambiguity inside the entry's own scope is still ambiguity."""
        matches = [self.match('State of Kerala', 'Ernākulam'),
                   self.match('State of Kerala', 'Ernākulam')]
        self.assertEqual(aliases.prefer('Kochi', matches, norm), (None, None))

    def test_an_unlisted_name_is_never_decided_here(self):
        matches = [self.match('State of Kerala', 'Ernākulam', name='Ramnagar')]
        self.assertEqual(aliases.prefer('Ramnagar', matches, norm), (None, None))


class CatalogueTests(unittest.TestCase):
    """The table is only true while the catalogue agrees with it."""

    def gazetteer(self):
        from weathergpt_data.workspace import Workspace
        from weathergpt_data.conversation import ConversationEngine
        return ConversationEngine(Workspace()).gazetteer

    def test_every_rename_target_is_a_place_the_catalogue_holds(self):
        """A rename pointing at a name the catalogue does not index would silently do nothing."""
        gazetteer = self.gazetteer()
        for entry in aliases.RENAMES:
            with self.subTest(now=entry['now']):
                self.assertTrue(gazetteer.search(entry['now']), entry['now'] + ' is not in the catalogue')

    def test_every_preference_names_a_place_the_catalogue_holds(self):
        gazetteer = self.gazetteer()
        for entry in aliases.PREFERENCES:
            with self.subTest(name=entry['name']):
                chosen, _why = aliases.prefer(entry['name'], gazetteer.search(entry['name']), norm)
                self.assertIsNotNone(chosen, entry['name'] + ' no longer resolves through its entry')


if __name__ == '__main__':
    unittest.main()


class AliasDisclosureTests(unittest.TestCase):
    """A place read under a name other than the one asked for says so.

    Measured 21 September 2026: "What is the weather in London tomorrow?" answered "The forecast for
    Ban Sarkāri, Hoshiarpur, State of Punjab ..." with no mention of London anywhere in it. The
    catalogue records "London" as an alternative name for that hamlet, and a single exact alias match
    was accepted in silence.

    Accepting it is right - "Bombay" is Mumbai and a reader should not be interrogated about it. Doing
    so silently is not, because the catalogue also holds aliases nobody would predict. Read under
    another name, and quiet about it, is the one combination that cannot stand.
    """

    def engine(self):
        from weathergpt_data.workspace import Workspace
        from weathergpt_data.conversation import ConversationEngine
        return ConversationEngine(Workspace())

    def test_the_catalogue_really_does_hold_this_alias(self):
        """The premise of the test above, asserted rather than assumed."""
        rows = self.engine().gazetteer.search('London')
        self.assertEqual(len(rows), 1, 'London is a single exact alias match, which is why it was silent')
        self.assertNotIn('london', rows[0]['name'].lower())

    def test_a_place_read_under_another_name_is_disclosed(self):
        result = self.engine().ask({'question': 'What is the weather in London tomorrow?'})
        disclosed = [note for note in result['notes'] if '"London" is read as' in note]
        self.assertTrue(disclosed, 'the reader must be told: %r' % (result['notes'],))
        self.assertIn('Say which place you meant', disclosed[0])

    def test_a_familiar_former_name_is_still_accepted(self):
        """The disclosure must not turn every alias into an interrogation."""
        result = self.engine().ask({'question': 'Will it rain in Bombay tomorrow?'})
        self.assertNotEqual(result['status'], 'needs_selection')
        self.assertTrue([note for note in result['notes'] if 'Mumbai' in note])
