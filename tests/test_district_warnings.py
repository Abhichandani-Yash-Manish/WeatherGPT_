"""Official district warning applicability: day anchoring, place resolution and honesty.

These are component checks over synthetic records and the real hazard and colour
maps. They do not call the network and they are not an acceptance test of the
live official product.
"""
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from weathergpt_data import district_warnings as dw
from weathergpt_data import warning_tools as wt
from weathergpt_data import product_api
from weathergpt_data.adapters import COLOURS, HAZARDS

IST = ZoneInfo('Asia/Kolkata')
# The fixture bulletin is dated 14 Sep 2026; the clock is pinned so day-one-is-today
# assertions test the anchoring rule rather than the day the suite happens to run.
CLOCK = datetime(2026, 9, 14, 6, tzinfo=timezone.utc)


def record(days=None, issued='2026-09-14T06:00:00+00:00', label='PATNA', district_id='364'):
    return {
        'district_label': label,
        'source_district_id': district_id,
        'issued_at_utc': issued,
        'source_locator': '$.features[0]',
        'geometry': {'type': 'Polygon', 'coordinates': [[[85.0, 25.4], [85.4, 25.4], [85.4, 25.8], [85.0, 25.8], [85.0, 25.4]]]},
        'days': days if days is not None else [
            {'source_day': 1, 'hazard_codes': [1], 'hazards': ['No warning in this product'], 'colour': 'green', 'colour_code': 4, 'source_text': ''},
            {'source_day': 2, 'hazard_codes': [4], 'hazards': ['Thunderstorm/lightning/squall'], 'colour': 'yellow', 'colour_code': 3, 'source_text': ''},
        ],
    }


class DayAnchoringTests(unittest.TestCase):
    def test_day_one_is_the_bulletin_date_in_ist(self):
        rows, issued = dw.day_rows(record(), now=CLOCK)
        self.assertEqual(rows[0]['date_local'], '2026-09-14')
        self.assertEqual(issued.astimezone(IST).strftime('%Y-%m-%d %H:%M'), '2026-09-14 11:30')

    def test_each_day_window_is_one_ist_calendar_day(self):
        rows, _ = dw.day_rows(record(), now=CLOCK)
        for row in rows:
            opens = datetime.fromisoformat(row['starts_utc']).astimezone(IST)
            closes = datetime.fromisoformat(row['ends_utc']).astimezone(IST)
            self.assertEqual(opens.strftime('%H:%M'), '00:00')
            self.assertEqual((closes - opens), timedelta(days=1))
            self.assertEqual(opens.date().isoformat(), row['date_local'])

    def test_five_days_are_numbered_from_the_bulletin_date(self):
        days = [{'source_day': n, 'hazard_codes': [1], 'hazards': ['No warning in this product'],
                 'colour': 'green', 'colour_code': 4, 'source_text': ''} for n in range(1, 6)]
        rows, _ = dw.day_rows(record(days=days), now=CLOCK)
        self.assertEqual([row['date_local'] for row in rows],
                         ['2026-09-14', '2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18'])

    def test_today_and_past_flags_use_the_supplied_clock(self):
        days = [{'source_day': n, 'hazard_codes': [1], 'hazards': ['No warning in this product'],
                 'colour': 'green', 'colour_code': 4, 'source_text': ''} for n in range(1, 6)]
        rows, _ = dw.day_rows(record(days=days), now=datetime(2026, 9, 16, 6, tzinfo=timezone.utc))
        flags = {row['date_local']: (row['is_today'], row['is_past']) for row in rows}
        self.assertEqual(flags['2026-09-16'], (True, False))
        self.assertEqual(flags['2026-09-14'][1], True)
        self.assertEqual(flags['2026-09-15'][1], True)

    def test_a_record_without_an_issue_time_is_refused(self):
        with self.assertRaises(Exception):
            dw.day_rows({'days': []})


class PlaceResolutionTests(unittest.TestCase):
    def test_a_point_inside_the_polygon_selects_the_district(self):
        hits = dw.select([record()], 25.6, 85.2)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]['district_label'], 'PATNA')

    def test_a_point_outside_every_polygon_selects_nothing(self):
        self.assertEqual(dw.select([record()], 19.0, 72.9), [])

    def test_a_bounding_box_is_not_treated_as_the_district(self):
        # Inside the bounding box of the ring, but outside the ring itself.
        ring = {'type': 'Polygon', 'coordinates': [[[0.0, 0.0], [2.0, 0.0], [0.0, 2.0], [0.0, 0.0]]]}
        item = record()
        item['geometry'] = ring
        self.assertEqual(dw.select([item], 1.8, 1.8), [])

    def test_coordinates_are_required(self):
        with self.assertRaises(Exception):
            dw.select([record()], None, None)


class MapFidelityTests(unittest.TestCase):
    """The maps are the reading of IMD's product. Drift here would invent a hazard."""

    def test_hazard_codes_match_the_official_names(self):
        self.assertEqual(HAZARDS[1], 'No warning in this product')
        self.assertEqual(HAZARDS[4], 'Thunderstorm/lightning/squall')
        self.assertEqual(HAZARDS[8], 'Strong surface winds')
        self.assertEqual(HAZARDS[16], 'Very heavy rain')
        self.assertEqual(HAZARDS[17], 'Extremely heavy rain')
        self.assertEqual(sorted(HAZARDS), list(range(1, 18)))

    def test_colour_codes_match_the_validated_mapping(self):
        self.assertEqual(COLOURS, {1: 'red', 2: 'orange', 3: 'yellow', 4: 'green'})
        self.assertNotIn(0, COLOURS, 'An unset colour code must never resolve to a level')


class HonestyTests(unittest.TestCase):
    def test_a_quiet_day_is_not_an_all_clear(self):
        rows, issued = dw.day_rows(record(), now=CLOCK)
        text = dw.summary(record(), rows, issued)
        self.assertIn('no warning in this product', text)
        self.assertIn('not an all-clear', text)
        self.assertNotIn('there are no warnings', text)

    def test_a_hazard_day_names_the_official_hazard(self):
        rows, _ = dw.day_rows(record(), now=CLOCK)
        self.assertIn('Thunderstorm/lightning/squall', dw.summary(record(), rows, dw.anchor(record())[1]))

    def test_source_text_is_used_verbatim_when_present(self):
        days = [{'source_day': 1, 'hazard_codes': [2], 'hazards': ['Heavy rain'], 'colour': 'yellow',
                 'colour_code': 3, 'source_text': 'Heavy rain likely over the district'}]
        rows, _ = dw.day_rows(record(days=days), now=CLOCK)
        self.assertFalse(rows[0]['quiet'])
        self.assertEqual(dw.hazard_text(rows[0]), 'Heavy rain likely over the district')

    def test_severity_takes_the_most_severe_colour(self):
        rows, _ = dw.day_rows(record(), now=CLOCK)
        self.assertEqual(dw.severity(rows)[0], 'yellow')

    def test_an_unknown_colour_is_not_converted_into_a_level(self):
        days = [{'source_day': 1, 'hazard_codes': [1], 'hazards': ['No warning in this product'],
                 'colour': None, 'colour_code': 0, 'source_text': ''}]
        rows, issued = dw.day_rows(record(days=days), now=CLOCK)
        self.assertIsNone(dw.severity(rows)[0])
        self.assertIn('colour not supplied', dw.summary(record(), rows, issued))

    def test_facts_carry_the_entity_window_and_source(self):
        rows, issued = dw.day_rows(record(), now=CLOCK)
        facts = dw.facts(record(), rows, issued, 't1-c1', 'Patna')
        self.assertEqual(len(facts), 2)
        first = facts[0]
        self.assertEqual(first['source_id'], 'S15')
        self.assertEqual(first['entity_id'], 'imd-district:364')
        self.assertEqual(first['start'], '2026-09-13T18:30:00+00:00')
        self.assertEqual(first['citation_ids'], ['t1-c1'])
        self.assertEqual(first['parameter'], 'official_district_warning')

    def test_a_stale_bulletin_reports_no_current_fact(self):
        rows, _ = dw.day_rows(record(), now=datetime(2026, 12, 1, tzinfo=timezone.utc))
        self.assertTrue(all(row['is_past'] for row in rows))
        self.assertEqual([row for row in rows if not row['is_past']], [])


class ResolutionLadderTests(unittest.TestCase):
    class Engine(object):
        def __init__(self, answers):
            self.answers = answers
            self.calls = []
            outer = self

            class Gazetteer(object):
                def search(inner, name, state='', district=''):
                    outer.calls.append((name, state, district))
                    key = (state, district)
                    return outer.answers.get(key, [])
            self.gazetteer = Gazetteer()

    def test_a_single_confident_match_is_used(self):
        engine = self.Engine({('Bihar', 'Patna'): [{'label': 'Patna, Bihar', 'coordinates': {'latitude': 25.6, 'longitude': 85.1}, 'match_type': 'source_name_or_alias'}]})
        match, seen, candidates = wt._gazetteer_ladder(engine, {'name': 'Patna', 'state': 'Bihar', 'district': 'Patna'})
        self.assertIsNotNone(match)
        self.assertEqual(seen, 1)
        self.assertIsNone(candidates)

    def test_several_candidates_are_returned_instead_of_guessed(self):
        engine = self.Engine({('', ''): [{'label': 'A', 'coordinates': {'latitude': 1, 'longitude': 1}}, {'label': 'B', 'coordinates': {'latitude': 2, 'longitude': 2}}]})
        match, seen, candidates = wt._gazetteer_ladder(engine, {'name': 'Ambiguous', 'state': '', 'district': ''})
        self.assertIsNone(match)
        self.assertEqual(len(candidates), 2)

    def test_an_unused_hint_does_not_hide_a_match(self):
        engine = self.Engine({('', ''): [{'label': 'Only', 'coordinates': {'latitude': 1, 'longitude': 1}}]})
        match, seen, candidates = wt._gazetteer_ladder(engine, {'name': 'Only', 'state': '', 'district': 'WrongDistrict'})
        self.assertIsNotNone(match, 'The ladder must loosen the hint rather than accept no answer')
        # The third attempt would repeat the second filter pair, so the ladder drops it.
        self.assertEqual(len(engine.calls), 2)
        self.assertEqual(engine.calls[0][2], 'WrongDistrict')
        self.assertEqual(engine.calls[1][2], '')

    def test_a_name_with_no_match_reports_nothing(self):
        engine = self.Engine({})
        match, seen, candidates = wt._gazetteer_ladder(engine, {'name': 'Nowhere', 'state': '', 'district': ''})
        self.assertIsNone(match)
        self.assertIsNone(candidates)

    def test_normalisation_ignores_case_and_punctuation(self):
        self.assertEqual(wt.normalise('Ahmadabad, State of Gujar\u0101t'), 'AHMADABADSTATEOFGUJART')
        self.assertEqual(wt.normalise('AHMADABAD'), 'AHMADABAD')



class ReadModelDayTests(unittest.TestCase):
    """The read model must not date the days its own way.

    Measured 15 September 2026: product_api.decode_days stamped the bulletin date on all five rows
    while district_warnings.day_rows derived five IST days, so every national surface showed one date
    five times and the place strip showed no date at all. The read model now runs the same contract."""

    def properties(self, **overrides):
        values = {'District': 'PATNA', 'Date': '2026-09-14', 'UTC': 6,
                  'Day_1': '4', 'Day_2': '1', 'Day_3': '1', 'Day_4': '1', 'Day_5': '1',
                  'Day1_Color': 3, 'Day2_Color': 4, 'Day3_Color': 4, 'Day4_Color': 4, 'Day5_Color': 4}
        values.update(overrides)
        return values

    def test_five_rows_carry_five_dates_counted_from_the_bulletin_date(self):
        _, days = product_api.decode_days(self.properties())
        self.assertEqual([day['date_utc'] for day in days],
                         ['2026-09-14', '2026-09-15', '2026-09-16', '2026-09-17', '2026-09-18'])
        self.assertEqual(days[1]['label'], '15 Sep 2026')
        self.assertEqual([day['date_local'] for day in days], [day['date_utc'] for day in days])

    def test_every_row_carries_a_consecutive_ist_window(self):
        _, days = product_api.decode_days(self.properties())
        for day in days:
            opens = datetime.fromisoformat(day['starts_utc']).astimezone(IST)
            closes = datetime.fromisoformat(day['ends_utc']).astimezone(IST)
            self.assertEqual(opens.strftime('%H:%M'), '00:00')
            self.assertEqual(closes - opens, timedelta(days=1))
            self.assertEqual(opens.date().isoformat(), day['date_utc'])
        self.assertEqual(days[1]['starts_utc'], days[0]['ends_utc'])

    def test_the_read_model_and_the_contract_agree_on_every_date(self):
        issued, days = product_api.decode_days(self.properties())
        rows, _ = dw.day_rows({'issued_at_utc': issued.isoformat(),
                               'days': [{'source_day': index, 'hazard_codes': day['hazard_codes'],
                                         'hazards': day['hazards'], 'colour': day['colour'],
                                         'colour_code': day['colour_code'], 'source_text': day['source_text']}
                                        for index, day in enumerate(days, start=1)]})
        self.assertEqual([row['date_local'] for row in rows], [day['date_utc'] for day in days])

    def test_a_record_without_a_bulletin_date_invents_none(self):
        for value in ('', 'not a date'):
            _, days = product_api.decode_days(self.properties(Date=value))
            self.assertTrue(all(day['date_utc'] is None for day in days), value)
            self.assertTrue(all(day['starts_utc'] is None and day['ends_utc'] is None for day in days), value)
            self.assertEqual(days[0]['colour'], 'yellow', 'the colour still arrives without a date')
            self.assertEqual(days[0]['unknown_hazard_codes'], [])

    def test_colours_hazards_and_quiet_flags_are_unchanged_by_the_derivation(self):
        _, days = product_api.decode_days(self.properties(Day_2='99', Day2_Color=3))
        self.assertEqual(days[1]['colour'], 'yellow')
        self.assertEqual(days[1]['unknown_hazard_codes'], [99])
        self.assertEqual(days[1]['hazards'], [])
        self.assertTrue(days[2]['quiet'])
        self.assertFalse(days[0]['quiet'])

    def test_is_today_marks_one_day_for_a_current_bulletin_and_none_for_an_old_one(self):
        today = datetime.now(IST).date().isoformat()
        _, current = product_api.decode_days(self.properties(Date=today))
        self.assertEqual(sum(1 for day in current if day['is_today']), 1)
        _, old = product_api.decode_days(self.properties(Date='2020-01-01'))
        self.assertEqual(sum(1 for day in old if day['is_today']), 0)
        self.assertTrue(all(day['is_past'] for day in old))


class PlaceDayKeyTests(unittest.TestCase):
    """Both read paths publish the day date under the same key, so no surface can miss it."""

    class Foundation:
        def warning_snapshot(self, latitude, longitude, refresh=False):
            return {'records': [record()],
                    'provenance': {'source_id': 'S63', 'retrieved_at_utc': '2026-09-14T06:05:00+00:00'},
                    'coverage': {'features_returned': 1, 'districts_listed': 1}}

    def test_the_place_view_carries_date_utc_beside_date_local(self):
        view = product_api.warnings_place(self.Foundation(), 25.6, 85.1)
        days = view['data']['days']
        self.assertEqual([day['date_utc'] for day in days], [day['date_local'] for day in days])
        self.assertEqual([day['date_utc'] for day in days], ['2026-09-14', '2026-09-15'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
