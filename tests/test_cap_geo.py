"""Phase 5: CAP geometric applicability, reviewed aliases, sea/no-land matrix.

Sea/no-land decision matrix (pinned here, implemented across cap_geo +
warning_tools + district_warnings):
  land point + district polygon      -> district guidance (existing select)
  land point + CAP polygon covering  -> applicable
  land point + CAP polygon elsewhere -> not_applicable (never borrowed)
  sea/coast name, no district point  -> needs_clarification (existing, untouched)
  CAP record with no areas           -> held (never a no)
  CAP geocode only                   -> held with codes listed (never guessed)
  malformed polygon/circle           -> held with reason (never guessed)
  alias with state scope match       -> disclosed canonical read
  alias ambiguous / wrong state      -> unresolved (keep asking)
"""
import unittest

from weathergpt_data import cap_geo
from weathergpt_data.cap_geo import assess_records, match_area
from weathergpt_data.district_aliases import CROSSWALK_VERSION, describe, resolve


def area(polygons=None, circles=None, geocodes=None):
    return {'polygons': polygons or [], 'circles': circles or [],
            'geocodes': geocodes or []}


def record(identifier, areas, sender='sender@example.in'):
    return {'identifier': identifier, 'sender': sender,
            'info': [{'areas': areas}]}


# A unit square around (lat 10, lon 76): CAP order is lat,lon.
SQUARE = '10.0,76.0 10.0,77.0 11.0,77.0 11.0,76.0 10.0,76.0'
CIRCLE = '10.5,76.5 60000'


class PolygonTests(unittest.TestCase):
    def test_inside_is_applicable_boundary_counts(self):
        verdict, _ = cap_geo.match_polygon(10.5, 76.5, SQUARE)
        self.assertEqual(verdict, 'applicable')
        verdict, _ = cap_geo.match_polygon(10.0, 76.5, SQUARE)
        self.assertEqual(verdict, 'applicable')

    def test_outside_is_not_applicable_never_borrowed(self):
        verdict, reason = cap_geo.match_polygon(20.0, 76.5, SQUARE)
        self.assertEqual(verdict, 'not_applicable')
        self.assertIn('outside', reason)

    def test_cap_order_is_lat_lon_not_geojson(self):
        # (76, 10) as lat,lon would be an invalid latitude: must hold, not match.
        verdict, _ = cap_geo.match_polygon(76.0, 10.0, SQUARE)
        self.assertEqual(verdict, 'not_applicable')

    def test_malformed_polygons_hold(self):
        for bad in ('', '10.0,76.0', 'a,b c,d e,f g,h', '10.0,76.0 200.0,76.0 11.0,77.0 10.0,76.0',
                    '10.0 76.0 11.0 77.0', None):
            verdict, reason = cap_geo.match_polygon(10.5, 76.5, bad)
            self.assertEqual(verdict, 'held', bad)
            self.assertTrue(reason)


class CircleTests(unittest.TestCase):
    def test_inside_and_outside_by_geodesic_distance(self):
        verdict, _ = cap_geo.match_circle(10.5, 76.5, CIRCLE)
        self.assertEqual(verdict, 'applicable')
        verdict, _ = cap_geo.match_circle(12.0, 78.0, CIRCLE)
        self.assertEqual(verdict, 'not_applicable')

    def test_malformed_circles_hold(self):
        for bad in ('', '10.5,76.5', '10.5,76.5 -5', 'x,y 100', None):
            self.assertEqual(cap_geo.match_circle(10.5, 76.5, bad)[0], 'held', bad)


class AreaPrecedenceTests(unittest.TestCase):
    def test_applicable_beats_held_beats_not_applicable(self):
        applicable = match_area(10.5, 76.5, area(polygons=[SQUARE],
                                                 geocodes=[{'U': 'X'}]))
        self.assertEqual(applicable[0], 'applicable')
        held = match_area(20.0, 76.5, area(polygons=['20.0,70.0 20.0,71.0 21.0,71.0 21.0,70.0 20.0,70.0'],
                                            geocodes=[{'U': 'X'}]))
        self.assertEqual(held[0], 'held')
        self.assertIn('X', held[1])
        outside = match_area(20.0, 76.5, area(polygons=['20.0,70.0 20.0,71.0 21.0,71.0 21.0,70.0 20.0,70.0']))
        self.assertEqual(outside[0], 'not_applicable')

    def test_empty_area_and_missing_point_hold(self):
        self.assertEqual(match_area(10.5, 76.5, area())[0], 'held')
        self.assertEqual(match_area(None, None, area(polygons=[SQUARE]))[0], 'held')


class AssessRecordsTests(unittest.TestCase):
    def test_per_record_verdicts_with_precedence(self):
        records = [record('a', [area(polygons=[SQUARE])]),
                   record('b', [area(polygons=['20.0,70.0 20.0,71.0 21.0,71.0 21.0,70.0 20.0,70.0'])]),
                   record('c', [area(geocodes=[{'SAME': '123'}])]),
                   record('d', [])]
        assessed = assess_records(records, 10.5, 76.5)
        by_id = {row['identifier']: row['verdict'] for row in assessed}
        self.assertEqual(by_id, {'a': 'applicable', 'b': 'not_applicable',
                                 'c': 'held', 'd': 'held'})

    def test_unusable_point_holds_every_record(self):
        assessed = assess_records([record('a', [area(polygons=[SQUARE])])], None, None)
        self.assertEqual(assessed[0]['verdict'], 'held')

    def test_never_raises_on_garbage(self):
        assessed = assess_records([None, {}, {'info': [{'areas': [None, 42]}]}], 10.5, 76.5)
        self.assertEqual(len(assessed), 3)
        self.assertTrue(all(row['verdict'] == 'held' for row in assessed))


class AliasTests(unittest.TestCase):
    def test_reviewed_alias_resolves_with_provenance(self):
        canonical, entry = resolve('Ahmadabad', 'Gujarat')
        self.assertEqual(canonical, 'AHMEDABAD')
        self.assertEqual(entry['confidence'], 'high')
        self.assertIn('basis', entry)

    def test_wrong_state_and_ambiguity_resolve_to_nothing(self):
        canonical, reason = resolve('Ahmadabad', 'Karnataka')
        self.assertIsNone(canonical)
        self.assertIn('another state', reason)
        self.assertIsNone(resolve('Nowhere District')[0])

    def test_balrampur_twins_need_state(self):
        self.assertIsNone(resolve('BalrampurCG', 'Uttar Pradesh')[0])
        canonical, _ = resolve('BalrampurCG', 'Chhattisgarh')
        self.assertEqual(canonical, 'BALRAMPUR')

    def test_table_describes_itself(self):
        info = describe()
        self.assertEqual(info['version'], CROSSWALK_VERSION)
        self.assertGreaterEqual(info['entries'], 7)
        self.assertIn('not an LGD', info['note'])


if __name__ == '__main__':
    unittest.main()
