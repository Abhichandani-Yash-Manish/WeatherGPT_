"""Turning a browser's coordinates into a place this workspace can answer about.

Every tool here takes a NAMED place - the district a warning is published for, the station a reading
came from, the bulletin a district carries - so a latitude and longitude are not something the product
can answer about. They are resolved once against the catalogue, and the name is the reader's to see and
to correct.
"""
import unittest

from weathergpt_data.gazetteer import Gazetteer


class NearestPlaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.places = Gazetteer()

    def test_a_point_in_a_city_names_that_city(self):
        """Not the quarter of it the reader happens to be standing in.

        Measured 22 September 2026: the nearest row to central Ahmedabad is Lal Darwaja, 0.66 km away,
        and this extract marks Lal Darwaja, Ahmedabad and every neighbour around them as plain PPL - so
        seat order ties at 7 across the whole city and cannot separate them. The row whose own name
        matches its own district is the one the district is named after, and that is the answer.
        """
        for latitude, longitude, expected in [(23.0225, 72.5714, 'Ahmedabad'),
                                              (19.0760, 72.8777, 'Mumbai'),
                                              (21.1702, 72.8311, 'Surat'),
                                              (34.1526, 77.5771, 'Leh')]:
            with self.subTest(expected=expected):
                match = self.places.nearest(latitude, longitude)
                self.assertIsNotNone(match, 'nothing found near ' + expected)
                self.assertEqual(match['name'], expected)

    def test_it_does_not_reach_across_a_district_for_a_bigger_name(self):
        """Ranking on seat order alone sent a reader in Ahmedabad to GANDHINAGAR, a state capital 24 km
        away that outranks every row in the city they are standing in. Rank is credit against distance,
        never priority over it."""
        match = self.places.nearest(23.0225, 72.5714)
        self.assertNotEqual(match['name'], 'Gandhinagar')
        self.assertLess(match['distance_km'], 5)

    def test_a_point_the_catalogue_does_not_cover_returns_nothing(self):
        """Being told nothing was found is useful. Being quietly placed in a town 400 km away is not."""
        self.assertIsNone(self.places.nearest(15.0, 62.0), 'mid-Arabian Sea matched a place')
        self.assertIsNone(self.places.nearest(-40.0, 145.0), 'Tasmania matched an Indian place')

    def test_the_distance_is_reported_so_a_reader_can_judge_it(self):
        match = self.places.nearest(19.0760, 72.8777)
        self.assertIn('distance_km', match)
        self.assertGreaterEqual(match['distance_km'], 0)
        self.assertLess(match['distance_km'], 60)

    def test_a_point_off_the_globe_is_refused_rather_than_clamped(self):
        for latitude, longitude in [(91.0, 0.0), (0.0, 181.0)]:
            with self.subTest(point=(latitude, longitude)):
                with self.assertRaises(ValueError):
                    self.places.nearest(latitude, longitude)


if __name__ == '__main__':
    unittest.main()
