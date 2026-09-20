"""A reader says "Delhi airport", not "VIDP".

Measured 20 September 2026 against the scenario atlas: "What is the current weather at Delhi
airport?" and "TAF for Bengaluru airport" both came back asking for a four-letter ICAO code.
Demanding the code turned an answerable question into a quiz, and gave the same unhelpful reply
whether or not the airport was one this workspace can actually reach.

The city list is closed and hand-checked rather than a fuzzy search. Attaching one airport's report
to another city is the same class of error as attaching a warning to the wrong district: a miss
stays a miss, and the reply names the six stations that do exist.
"""
import unittest

from weathergpt_data.airport_tools import AIRPORT_CITIES, airport_code


class AirportNamingTests(unittest.TestCase):
    def test_a_city_name_resolves_to_the_station_that_serves_it(self):
        self.assertEqual(airport_code('Delhi'), 'VIDP')
        self.assertEqual(airport_code('Delhi airport'), 'VIDP')
        self.assertEqual(airport_code('Chennai International Airport'), 'VOMM')
        self.assertEqual(airport_code('the airport at Kolkata'), 'VECC')

    def test_the_name_a_city_was_called_before_it_was_renamed_still_works(self):
        self.assertEqual(airport_code('Bombay'), 'VABB')
        self.assertEqual(airport_code('Madras'), 'VOMM')
        self.assertEqual(airport_code('Calcutta'), 'VECC')

    def test_a_code_is_taken_as_itself(self):
        self.assertEqual(airport_code('VIDP'), 'VIDP')
        self.assertEqual(airport_code('vidp'), 'VIDP')

    def test_an_airport_that_is_not_connected_is_not_guessed_at(self):
        self.assertIsNone(airport_code('Bengaluru airport'))
        self.assertIsNone(airport_code('Pune'))
        self.assertIsNone(airport_code(''))
        self.assertIsNone(airport_code(None))

    def test_every_listed_station_is_reachable_by_its_own_city_name(self):
        """The table is only useful if each entry answers to the name it advertises."""
        for code, (city, aliases) in AIRPORT_CITIES.items():
            with self.subTest(code=code):
                self.assertEqual(airport_code(city), code)
                for alias in aliases:
                    self.assertEqual(airport_code(alias), code, alias)

    def test_no_two_stations_claim_the_same_city_name(self):
        """An ambiguous alias would silently attach one city's report to another."""
        seen = {}
        for code, (_city, aliases) in AIRPORT_CITIES.items():
            for alias in aliases:
                self.assertNotIn(alias, seen, alias + ' is claimed by both ' + str(seen.get(alias)) + ' and ' + code)
                seen[alias] = code


if __name__ == '__main__':
    unittest.main()
