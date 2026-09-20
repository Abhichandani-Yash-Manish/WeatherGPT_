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

    def test_a_quiet_day_outside_the_returned_rows_is_not_called_quiet(self):
        # The bulletin's first two days carried hazards and are already past; the question asks
        # about the days that are still current. The statement must not claim every published
        # day is quiet, which is what the 17 September 2026 Patna answer did.
        days = [
            {'source_day': 1, 'hazard_codes': [4, 8], 'hazards': ['Thunderstorm/lightning/squall', 'Strong surface winds'],
             'colour': 'orange', 'colour_code': 2, 'source_text': ''},
            {'source_day': 2, 'hazard_codes': [3], 'hazards': ['Heavy rain'], 'colour': 'yellow',
             'colour_code': 3, 'source_text': ''},
        ] + [{'source_day': n, 'hazard_codes': [1], 'hazards': ['No warning in this product'],
              'colour': 'green', 'colour_code': 4, 'source_text': ''} for n in (3, 4, 5)]
        later = datetime(2026, 9, 17, 6, tzinfo=timezone.utc)
        rows, issued = dw.day_rows(record(days=days), now=later)
        current = [row for row in rows if not row['is_past']]
        self.assertEqual([row['day'] for row in current], [4, 5])
        text = dw.summary(record(days=days), current, issued, published=rows)
        self.assertNotIn('Every other published day', text)
        self.assertIn('day 1', text)
        self.assertIn('orange', text)
        self.assertIn('(already past)', text)

    def test_every_published_day_quiet_is_still_not_an_all_clear(self):
        days = [{'source_day': n, 'hazard_codes': [1], 'hazards': ['No warning in this product'],
                 'colour': 'green', 'colour_code': 4, 'source_text': ''} for n in range(1, 6)]
        rows, issued = dw.day_rows(record(days=days), now=CLOCK)
        current = [row for row in rows if not row['is_past']]
        text = dw.summary(record(days=days), current, issued, published=rows)
        self.assertIn('Every published day in this bulletin is also no warning in this product', text)
        self.assertIn('not an all-clear', text)

    def test_the_edition_age_is_stated_when_the_bulletin_predates_the_read(self):
        rows, issued = dw.day_rows(record(), now=CLOCK)
        text = dw.summary(record(), rows, issued, now=datetime(2026, 9, 17, 6, tzinfo=timezone.utc))
        self.assertIn('3 day(s) before this read', text)
        self.assertIn('no newer edition has been read here', text)

    def test_the_edition_age_is_absent_on_the_day_of_issue(self):
        rows, issued = dw.day_rows(record(), now=CLOCK)
        text = dw.summary(record(), rows, issued, now=CLOCK)
        self.assertNotIn('before this read', text)


class CitationStoreTests(unittest.TestCase):
    """A warning citation says where the bytes it was read from are kept.

    Measured 17 September 2026: both warning citations carried a response hash with no path to
    the stored blob, while every forecast citation carried one, so the warning chain could not be
    walked from the answer back to the bytes.
    """

    def test_both_warning_citations_carry_the_store_path(self):
        meta = {'url': 'https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml', 'sha256': 'a' * 64,
                'retrieved_at_utc': '2026-09-17T09:39:32+00:00', 'blob': 'blobs/' + 'a' * 64 + '.bin'}
        snapshot = {'url': 'https://reactjs.imd.gov.in/geoserver/wfs', 'sha256': 'b' * 64,
                    'retrieved_at_utc': '2026-09-17T09:40:01+00:00', 'blob': 'blobs/' + 'b' * 64 + '.bin'}
        citations = wt.warning_citations(meta, snapshot, True)
        self.assertEqual([c['id'] for c in citations], ['cap-feed', 'district-warning'])
        for citation in citations:
            with self.subTest(citation=citation['id']):
                self.assertEqual(citation['raw_store'], 'warning-evidence')
                self.assertTrue(citation['raw_relative_path'].startswith('blobs/'))
                self.assertEqual(citation['response_sha256'], citation['raw_relative_path'][6:-4])

    def test_a_response_with_no_recorded_blob_does_not_invent_a_path(self):
        meta = {'url': 'https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml', 'sha256': 'c' * 64,
                'retrieved_at_utc': '2026-09-17T09:39:32+00:00'}
        citations = wt.warning_citations(meta, None, False)
        self.assertEqual(citations[0], {'id': 'cap-feed', 'source_id': 'S06',
                                        'provider': 'IMD-labelled CAP relay; origin authentication unverified',
                                        'product': 'Retrieved CAP feed state', 'url': meta['url'],
                                        'response_sha256': meta['sha256'], 'retrieved_at_utc': meta['retrieved_at_utc']})


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


class NationalSweepTests(unittest.TestCase):
    """"Which districts are under a red warning today?" names no place, and is still a real question.

    Added 20 September 2026. The per-place path had nothing to resolve, so the turn fell through to a
    CAP-relay refusal that spoke about "this place" - a place the reader never mentioned - and never
    mentioned the 742-district store it was holding at the time. The district product is national by
    construction, so this question is answered from it.
    """

    class Engine:
        def __init__(self, clock):
            self.workspace = type('W', (), {'clock': staticmethod(lambda: clock)})()

    def sweep(self, records, colours, clock=CLOCK):
        result = {'facts': [], 'notes': [], 'citations': [], 'trace': {'tools': []}}
        cap = {'records': [], 'assessment': {'eligible_by_lifecycle': 0}, 'latest_sent': None,
               'coverage': {}, 'meta': {'url': 'https://example.invalid/rss.xml', 'sha256': 'a' * 64,
                                        'retrieved_at_utc': '2026-09-14T06:00:00+00:00', 'delivery': 'live'}}
        return wt.national_sweep(self.Engine(clock), result, {'places': [], 'requested_outcome': ''},
                                 {}, records, {'url': 'u', 'sha256': 'b' * 64, 'retrieved_at_utc': 'r'}, cap, colours)

    def red(self, label, day=1):
        return record(label=label, days=[{'source_day': day, 'hazard_codes': [4],
                                          'hazards': ['Thunderstorm/lightning/squall'], 'colour': 'red',
                                          'colour_code': 1, 'source_text': ''}])

    def test_the_colour_is_read_from_the_readers_own_words(self):
        self.assertEqual(wt.requested_colours('Which districts are under a red warning today?'), ['red'])
        self.assertEqual(wt.requested_colours('any amber alerts?'), ['orange'])
        self.assertEqual(wt.requested_colours('red and orange districts'), ['orange', 'red'])
        # No colour named is not a colour guessed: it means every hazard colour.
        self.assertIsNone(wt.requested_colours('which districts have a warning?'))

    def test_matching_districts_are_named_with_a_fact_each(self):
        out = self.sweep([self.red('KACHCHH'), self.red('PATNA'), record(label='SURAT')], ['red'])
        self.assertEqual(out['status'], 'answered')
        self.assertIn('2 districts carry red', out['answer'])
        self.assertIn('KACHCHH', out['answer'])
        self.assertIn('PATNA', out['answer'])
        self.assertNotIn('SURAT', out['answer'], 'a green district is not reported as a warning')
        self.assertTrue(out['facts'], 'each matching district carries its own fact')
        self.assertTrue(all(f['value'] == 'red' for f in out['facts']))
        swept = out['warning_evidence']['national_sweep']
        self.assertEqual(swept['districts_in_store'], 3)
        self.assertEqual(len(swept['matched_districts']), 2)

    def test_none_today_is_an_answer_when_the_bulletin_is_current(self):
        """A current bulletin with no red district answers the question; it does not fail it."""
        out = self.sweep([record(label='SURAT'), record(label='PATNA')], ['red'])
        self.assertEqual(out['status'], 'answered')
        self.assertIn('No district carries red', out['answer'])
        self.assertIn('2 districts have a day that has not yet passed', out['answer'])
        self.assertIn('not a statement that nothing will happen', out['answer'])
        self.assertFalse(out['facts'])

    def test_a_wholly_lapsed_store_is_stale_and_never_an_all_clear(self):
        """Measured 20 September 2026 against the live store: 742 districts, newest edition 15 Sep,
        every published day passed. The reader is told the edition and its date, not 'no warnings'."""
        late = CLOCK + timedelta(days=9)
        out = self.sweep([self.red('KACHCHH'), record(label='SURAT')], ['red'], clock=late)
        self.assertEqual(out['status'], 'stale')
        self.assertIn('newest stored edition is dated 2026-09-14', out['answer'])
        self.assertIn('covers 2 districts', out['answer'])
        self.assertIn('not an all-clear', out['answer'])
        # The lapsed red is reported as a past bulletin state, explicitly and without facts.
        self.assertIn('KACHCHH', out['answer'])
        self.assertIn('has now passed', out['answer'])
        self.assertFalse(out['facts'], 'a lapsed bulletin contributes no current fact')

    def test_an_unnamed_colour_sweeps_every_hazard_but_not_green(self):
        # The default fixture record carries yellow on day 2, so a genuinely quiet district is
        # spelled out here rather than assumed.
        quiet = record(label='SURAT', days=[{'source_day': 1, 'hazard_codes': [1],
                                             'hazards': ['No warning in this product'], 'colour': 'green',
                                             'colour_code': 4, 'source_text': ''}])
        out = self.sweep([quiet, self.red('KACHCHH')], None)
        self.assertEqual(out['status'], 'answered')
        self.assertIn('KACHCHH', out['answer'])
        self.assertNotIn('SURAT', out['answer'])
        self.assertEqual(out['warning_evidence']['national_sweep']['colours'], ['red', 'orange', 'yellow'])
        self.assertFalse(out['warning_evidence']['national_sweep']['colours_named_by_reader'])

    def test_a_nationwide_match_is_capped_and_says_that_it_is(self):
        out = self.sweep([self.red('D%03d' % i) for i in range(wt.FACT_CAP + 7)], ['red'])
        self.assertEqual(out['status'], 'answered')
        self.assertIn('and 7 more', out['answer'])
        self.assertIn('capped at ' + str(wt.FACT_CAP), out['answer'])
        self.assertEqual(len(out['facts']), wt.FACT_CAP)
        # The cap is a display limit, never a measurement limit: the evidence keeps every match.
        self.assertEqual(len(out['warning_evidence']['national_sweep']['matched_districts']), wt.FACT_CAP + 7)


class StateScopeTests(unittest.TestCase):
    """A state is a state, not a village spelled like one.

    Measured 20 September 2026 against the scenario atlas: "Are there any weather warnings in Kerala
    today?" answered "Which place do you mean? Kerla, Pali District, State of Rājasthān / ...". Seven
    atlas failures had this one cause - Kerala, Bihar, Punjab, Rajasthan, Gujarat, Uttarakhand - and
    it is the most embarrassing thing this product could do to someone who named their own state.
    """

    def directory(self):
        from weathergpt_data.workspace import Workspace
        from weathergpt_data.states import StateDirectory
        return StateDirectory(Workspace().service.geography_database)

    def test_the_thirty_six_states_are_read_from_the_source_backed_directory(self):
        states = self.directory().states()
        self.assertEqual(len(states), 36, 'twenty-eight states and eight union territories')
        for expected in ('Kerala', 'Bihar', 'Punjab', 'Rajasthan', 'Gujarat', 'Uttarakhand'):
            self.assertIn(expected, states)

    def test_a_state_resolves_through_its_official_alternates_but_a_hamlet_does_not(self):
        directory = self.directory()
        self.assertEqual(directory.resolve('Kerala'), 'Kerala')
        self.assertEqual(directory.resolve('the state of Gujarat'), 'Gujarat')
        # Renames and official alternates, not transliteration guesses.
        self.assertEqual(directory.resolve('Orissa'), 'Odisha')
        self.assertEqual(directory.resolve('J&K'), 'Jammu and Kashmir')
        # The hamlet that was being offered in Kerala's place is not a state, and neither is a city.
        self.assertIsNone(directory.resolve('Kerla'))
        self.assertIsNone(directory.resolve('Ahmedabad'))

    def test_attribution_reports_what_it_could_not_place(self):
        """The warning product publishes no state, so attribution is by name and is partial.

        A count that hides its own incompleteness is worse than no count: "27 districts in Gujarat"
        read as complete would be wrong.
        """
        directory = self.directory()
        records = [{'district_label': 'THRISSUR'}, {'district_label': 'ALAPPUZHA'},
                   {'district_label': 'SURAT'}, {'district_label': 'NOT A REAL DISTRICT AT ALL'}]
        matched, unattributed = directory.attribute(records, 'Kerala')
        self.assertEqual(sorted(r['district_label'] for r in matched), ['ALAPPUZHA', 'THRISSUR'])
        self.assertEqual(unattributed, 1, 'the unplaceable district is counted, not dropped')

    def test_the_coverage_note_is_silent_only_when_nothing_was_lost(self):
        from weathergpt_data.states import coverage_note
        self.assertEqual(coverage_note(0, 742), '')
        note = coverage_note(201, 742)
        self.assertIn('201 of the 742', note)
        self.assertIn('could be among them', note, 'the reader is told the count may be short')
