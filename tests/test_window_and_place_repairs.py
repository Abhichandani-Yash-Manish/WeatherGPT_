"""Two repairs from the Hindi and Gujarati journeys of 15 September 2026.

Reproduced live: the Hinglish question "Ahmedabad, Gujarat mein kal subah barish hogi?" was
planned as the place "Gujarat" alone, and the gazetteer then offered twenty villages called
Gujar in Saharanpur. A comma pair is one place with its state, and the state is what
disambiguates the name, so it is kept as the state rather than resolved as a second place.

Reproduced live in the same journey: the note explaining how a midnight-to-midnight IST day is
read for source hours said "it is read as 00:30 to 00:30 IST", which names no date and reads as
a zero-length window. The note now names both resolved bounds.
"""
import unittest

from weathergpt_data.rule_planner import places_of
from weathergpt_data.transport import align_source_day


class CommaPairPlaceTests(unittest.TestCase):
    def test_a_hinglish_place_written_with_its_state_is_one_place(self):
        found = places_of('Ahmedabad, Gujarat mein kal subah barish hogi?')
        self.assertEqual([item['name'] for item in found], ['Ahmedabad'])
        self.assertEqual(found[0]['state'], 'Gujarat')

    def test_the_english_form_is_read_the_same_way(self):
        found = places_of('Will it rain in Ahmedabad, Gujarat tomorrow morning?')
        self.assertEqual([item['name'] for item in found], ['Ahmedabad'])
        self.assertEqual(found[0]['state'], 'Gujarat')

    def test_a_place_without_a_state_is_unchanged(self):
        found = places_of('Kal Ahmedabad me barish hogi?')
        self.assertEqual([item['name'] for item in found], ['Ahmedabad'])
        self.assertEqual(found[0]['state'], '')

    def test_a_compound_admin_unit_is_not_split_into_a_state(self):
        found = places_of('Kal Ahmedabad, District Saharanpur mein barish hogi?')
        self.assertEqual(found[0]['name'], 'Ahmedabad')
        self.assertEqual(found[0]['state'], 'District Saharanpur')


class BoundaryNoteTests(unittest.TestCase):
    def test_the_aligned_day_names_both_resolved_bounds(self):
        start, end, note = align_source_day('2026-09-16T00:00+05:30', '2026-09-17T00:00+05:30')
        self.assertIn('16 Sep 2026 00:30 to 17 Sep 2026 00:30 IST', note)
        self.assertIn('source hours start at :30 IST', note)
        self.assertEqual(start.isoformat(), '2026-09-16T00:30:00+05:30')
        self.assertEqual(end.isoformat(), '2026-09-17T00:30:00+05:30')

    def test_a_window_the_source_serves_is_untouched_and_says_nothing(self):
        start, end, note = align_source_day('2026-09-16T09:30+05:30', '2026-09-16T12:30+05:30')
        self.assertIsNone(note)
        self.assertEqual(start.isoformat(), '2026-09-16T09:30:00+05:30')
        self.assertEqual(end.isoformat(), '2026-09-16T12:30:00+05:30')


if __name__ == '__main__':
    unittest.main()