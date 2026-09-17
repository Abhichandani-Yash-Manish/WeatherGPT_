"""The agriculture repairs: quotes that answer the question, label text that is not advice, and the
holdings the advisories surface never showed.

Offline component checks. They assert the discipline, not a publisher measurement: a quote is taken
from the sentence the asked word is in, page furniture is removed, a dose table is labelled rather
than quoted as advice, a word cut mid-way is not served as a quote, and the holdings inventory counts
the regions this machine holds with their own printed dates and a measured age where one exists.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from weathergpt_data import corpus_overview
from weathergpt_data.bulletin_index import EXTRACTION_VERSION
from weathergpt_data.corpus_tools import clean_quoted, label_text_only, on_topic_excerpt

SCHEMA = ('CREATE TABLE documents (sha TEXT PRIMARY KEY, payload TEXT, payload_hash TEXT);'
          'CREATE TABLE passages (id TEXT PRIMARY KEY, document_sha TEXT, family TEXT, scope TEXT,'
          ' region TEXT, payload TEXT, payload_hash TEXT, embedding TEXT, embedding_hash TEXT,'
          ' model_revision TEXT);')

BLOCK = ('3 | P a g e water.  Udder of milking animals must be properly clean with zinc oxide or boric powder. '
         'AMFU Arnej: AHMEDABAD Advisory General advice Undertake interculturing and weeding operations to conserve '
         'moisture in standing monsoon crops and apply need based light irrigation by considering weather and soil '
         'moisture condition in standing crops.')
DOSE = ('Cotton: Apply 18.5 SC 3 ml in 10 litres of water. Flubendiamide 480 SC 3 ml in 10 litres. '
        'Spinosad 45 SC 3 ml per 10 litres of water.')
ADVICE = ('If irrigation facilities are available then apply need based irrigation through drip irrigation by '
          'considering soil moisture condition in standing crop.')


class QuoteTests(unittest.TestCase):
    def test_the_quote_is_taken_from_the_sentence_the_asked_word_is_in(self):
        quoted = on_topic_excerpt(BLOCK, ['irrigation'])
        self.assertIn('apply need based light irrigation', quoted)
        # The sentence before it belongs to another subject, so it is not pulled in as context.
        self.assertNotIn('Udder of milking animals', quoted)

    def test_page_furniture_is_removed_and_a_word_is_never_cut_mid_way(self):
        self.assertNotIn('P a g e', clean_quoted(BLOCK))
        long_text = 'Irrigation advice ' + ('word ' * 200)
        quoted = on_topic_excerpt(long_text, ['irrigation'])
        self.assertNotIn('wor …', quoted)
        self.assertTrue(quoted.endswith('[excerpt; the full passage is retained in evidence]'))

    def test_a_dose_table_is_label_text_and_an_advisory_sentence_is_not(self):
        self.assertTrue(label_text_only(DOSE))
        self.assertFalse(label_text_only(ADVICE))

    def test_a_passage_without_the_asked_word_is_quoted_from_its_head_and_says_so(self):
        quoted = on_topic_excerpt(ADVICE, ['harvest'])
        self.assertIn('If irrigation facilities are available', quoted)


class HoldingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        path = self.root / 'ingestion' / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite'
        path.parent.mkdir(parents=True)
        self.path = path
        with sqlite3.connect(path) as db:
            db.executescript(SCHEMA)
            for sha, region, state, issue, retrieved, passages in (
                    ('a' * 64, 'Ahmedabad', 'Gujarat', '2026-09-11', '2026-09-12T06:00:00+00:00', 2),
                    ('b' * 64, 'Surguja', 'Chhattisgarh', '2026-09-13', '2026-09-14T06:00:00+00:00', 1),
                    ('c' * 64, 'Undated', None, None, '2026-09-14T06:00:00+00:00', 1)):
                payload = {'sha256': sha, 'family': 'district_agromet', 'issue_date': issue, 'state': state,
                           'district': region, 'quarantined_passages': [],
                           'provenance': {'source_id': 'S57', 'retrieved_at_utc': retrieved}}
                db.execute('INSERT INTO documents VALUES (?,?,?)', (sha, json.dumps(payload), 'h'))
                for index in range(passages):
                    row = {'document_sha256': sha, 'family': 'district_agromet', 'scope': 'district', 'region': region,
                           'physical_page': index + 1, 'issue_date': issue, 'passage_index': index, 'source_id': 'S57',
                           'text': 'Passage ' + str(index)}
                    db.execute('INSERT INTO passages VALUES (?,?,?,?,?,?,?,?,?,?)',
                               ('p' + str(index) + sha[:4], sha, 'district_agromet', 'district', region,
                                json.dumps(row), 'ph', '{}', 'eh', 'v2'))
        self.now = None

    def test_holdings_count_the_regions_held_with_their_own_dates(self):
        packet = corpus_overview.holdings(self.root, family='district_agromet')
        self.assertEqual(packet['status'], 'ok')
        self.assertEqual(packet['counts']['regions'], 3)
        self.assertEqual(packet['counts']['documents'], 3)
        self.assertEqual(packet['counts']['passages'], 4)
        self.assertEqual(packet['counts']['states_named'], 2)
        self.assertEqual(packet['counts']['regions_without_a_printed_issue_date'], 1)
        by_region = {row['region']: row for row in packet['regions']}
        self.assertEqual(by_region['Ahmedabad']['newest_issue_date'], '2026-09-11')
        self.assertEqual(by_region['Ahmedabad']['age_days'], 1)
        # A region whose edition states no printed date keeps that unknown rather than borrowing a date.
        self.assertIsNone(by_region['Undated']['newest_issue_date'])
        self.assertIsNone(by_region['Undated']['age_days'])

    def test_holdings_filter_by_state_and_name_without_changing_the_counts(self):
        packet = corpus_overview.holdings(self.root, family='district_agromet', state='gujarat')
        self.assertEqual([row['region'] for row in packet['regions']], ['Ahmedabad'])
        self.assertEqual(packet['filters']['state'], 'gujarat')
        self.assertEqual(packet['counts']['regions'], 3)
        named = corpus_overview.holdings(self.root, family='district_agromet', query='surg')
        self.assertEqual([row['region'] for row in named['regions']], ['Surguja'])

    def test_a_missing_index_is_reported_rather_than_answered_empty(self):
        packet = corpus_overview.holdings(self.root / 'nothing-here')
        self.assertEqual(packet['status'], 'unavailable')
        self.assertTrue(packet['reason'])
        self.assertEqual(packet['regions'], [])


class FarmAnswerTests(unittest.TestCase):
    """The four repairs that made a farming question answerable: the spoken hour range, the multi-day
    window, the daily product for a window beyond the hourly horizon, and the district's own seat."""

    def test_a_spoken_hour_range_is_read_as_a_window(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from weathergpt_data.rule_planner import window_for
        now = datetime(2026, 9, 18, 20, 0, tzinfo=ZoneInfo('Asia/Kolkata'))
        for question in ('Kal 6 se 9 AM ka rain chance aur wind speed batao', 'tomorrow 6 to 9 am rain',
                         'kal 6-9 am baarish'):
            start, end, explicit, basis = window_for(question, now)
            self.assertTrue(start.startswith('2026-09-19T06:00'), question + ' -> ' + start)
            self.assertTrue(end.startswith('2026-09-19T09:00'), question + ' -> ' + end)
            self.assertTrue(explicit)
        # The single-hour reading is unchanged.
        start, end, explicit, _ = window_for('Will it rain tomorrow at 9 am?', now)
        self.assertTrue(start.startswith('2026-09-19T09:00') and end.startswith('2026-09-19T10:00'))

    def test_a_multi_day_window_is_aligned_to_the_source_days(self):
        from weathergpt_data.transport import align_source_day
        start, end, note = align_source_day('2026-09-19T00:00:00+05:30', '2026-09-22T00:00:00+05:30')
        self.assertEqual(start.strftime('%d %H:%M'), '19 00:30')
        self.assertEqual(end.strftime('%d %H:%M'), '22 00:30')
        self.assertIn('source hours start at :30', note)
        # A clock window is not touched.
        start, end, note = align_source_day('2026-09-19T06:00:00+05:30', '2026-09-19T09:00:00+05:30')
        self.assertEqual(note, None)
        self.assertEqual(start.strftime('%H:%M'), '06:00')

    def test_a_window_beyond_the_hourly_horizon_goes_to_the_daily_product(self):
        from weathergpt_data.capabilities import forecast_tool, hourly_horizon_exceeded
        three_days = {'operation': 'lookup', 'parameters': ['precipitation'],
                      'start_local': '2026-09-19T00:00:00+05:30', 'end_local': '2026-09-22T00:00:00+05:30'}
        self.assertTrue(hourly_horizon_exceeded(three_days))
        self.assertEqual(forecast_tool(three_days), 'forecast_summary')
        clocked = {'operation': 'lookup', 'parameters': ['precipitation_probability'],
                   'start_local': '2026-09-19T06:00:00+05:30', 'end_local': '2026-09-19T09:00:00+05:30',
                   'explicit_times': True}
        self.assertFalse(hourly_horizon_exceeded(clocked))
        self.assertEqual(forecast_tool(clocked), 'hourly_forecast')

    def test_equal_clock_times_are_one_whole_source_day(self):
        from datetime import datetime, timezone
        from weathergpt_data.answers import understand
        now = datetime(2026, 9, 12, 6, tzinfo=timezone.utc)
        request = understand('How much rain is forecast for Ahmedabad on 2026-09-13 from 00:30 to 00:30?', now, 'Asia/Kolkata')
        self.assertEqual(request['start_local'], '2026-09-13T00:30:00+05:30')
        self.assertEqual(request['end_local'], '2026-09-14T00:30:00+05:30')

    def test_a_district_reads_at_the_catalogue_seat_it_records(self):
        from weathergpt_data.gazetteer import Gazetteer, norm
        seat, why = Gazetteer().district_seat('Chhindwara', 'Madhya Pradesh')
        self.assertIsNotNone(seat)
        # The catalogue spells the seat with a macron; the match is normalised, and the row is returned as it is.
        self.assertEqual(norm(seat['admin2']), norm('Chhindwara'))
        self.assertIn('administrative centre', why)
        # A catalogue that holds no such row returns nothing rather than substituting a town.
        seat, why = Gazetteer().district_seat('Nowhereland', '')
        self.assertIsNone(seat)
        self.assertTrue(why)

    def test_a_dose_instruction_is_label_text_even_in_one_sentence(self):
        instruction = ('If fall army worm is observed in field Spray Spinosad 45 SC 0.3 ml or Emamectin '
                       'benzoate 5 SG@ 0.4 gm/lit of water to protect the crop at early stage.')
        guidance = ('Inspect plants for fall armyworm and stem/ear borers. Give preference to field scouting '
                    'and need-based control rather than calendar-based spraying.')
        self.assertTrue(label_text_only(instruction))
        self.assertFalse(label_text_only(guidance))


if __name__ == '__main__':
    unittest.main()
