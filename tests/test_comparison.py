"""Cross-product comparison: two products named, never ranked.

These are component checks over synthetic turn results. They take no measurement of any
publisher or model. What they pin is the behaviour the review asked for: an official warning
and a model forecast that speak about the same window are compared in plain terms, a quiet day
is not read as a forecast of no rain, unrelated hazards are reported as not comparable, and no
comparison ever becomes a score, a percentage or an all-clear.
"""
import json
import re
import unittest

from weathergpt_data.comparison import compare_products, summarise

NOTE_WORDS = ('not a score', 'neither is ranked')


def forecast_fact(value, start, end, parameter='precipitation', source_id='S21'):
    return {'id': 'f-' + str(abs(hash((value, start, end))) % 100000), 'parameter': parameter, 'value': value,
            'unit': 'mm', 'place': 'Patna, Patna, State of Bihar', 'source_id': source_id,
            'start': start, 'end': end, 'label': 'Forecast rainfall'}


def warning_day(colour='yellow', hazards=('Thunderstorm/lightning/squall',), quiet=False,
                starts='2026-09-15T18:30:00+00:00', ends='2026-09-16T18:30:00+00:00', label='16 Sep 2026'):
    return {'place': 'Patna, Patna, State of Bihar', 'district': 'PATNA', 'issued_at_utc': '2026-09-15T05:30:00+05:30',
            'days': [{'day': 2, 'label': label, 'colour': colour, 'colour_code': 3, 'quiet': quiet,
                      'hazards': list(hazards), 'starts_utc': starts, 'ends_utc': ends, 'source_text': None}]}


def turn(warning=None, facts=None, passages=None):
    result = {'facts': facts or [], 'passages': passages or [], 'warning_evidence': []}
    if warning:
        result['warning_evidence'].append({'records': [], 'district_warnings': [warning],
                                           'assessment': {'eligible_by_lifecycle': 0}, 'stale_districts': [],
                                           'points_outside_districts': []})
    return result


class ComparisonTests(unittest.TestCase):
    def test_a_warning_and_a_forecast_that_both_name_rain_are_consistent(self):
        items = compare_products(turn(warning=warning_day(),
                                      facts=[forecast_fact('0.5', '2026-09-16T00:30:00+05:30', '2026-09-16T23:30:00+05:30')]))
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item['kind'], 'official_warning_and_forecast')
        self.assertEqual(item['reading'], 'consistent')
        self.assertEqual([product['source_id'] for product in item['products']], ['S15', 'S21'])
        self.assertIn('Thunderstorm', json.dumps(item['products'], ensure_ascii=False))
        self.assertIn('0.5', json.dumps(item['products'], ensure_ascii=False))

    def test_a_rain_hazard_against_a_dry_forecast_is_reported_as_differing(self):
        items = compare_products(turn(warning=warning_day(),
                                      facts=[forecast_fact('0.0', '2026-09-16T00:30:00+05:30', '2026-09-16T23:30:00+05:30')]))
        self.assertEqual(items[0]['reading'], 'differ')
        self.assertIn('neither product is a measurement of the other', items[0]['why'])

    def test_a_quiet_day_is_not_compared_as_no_rain(self):
        items = compare_products(turn(warning=warning_day(colour='green', hazards=('No warning in this product',), quiet=True),
                                      facts=[forecast_fact('0.0', '2026-09-16T00:30:00+05:30', '2026-09-16T23:30:00+05:30')]))
        self.assertEqual(items, [], 'a quiet day is not a forecast and must not be compared as one')

    def test_a_hazard_the_forecast_does_not_measure_is_not_comparable(self):
        items = compare_products(turn(warning=warning_day(hazards=('Heat wave',)),
                                      facts=[forecast_fact('0.5', '2026-09-16T00:30:00+05:30', '2026-09-16T23:30:00+05:30')]))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['reading'], 'not_comparable')
        self.assertIn('does not measure', items[0]['why'])

    def test_windows_that_do_not_overlap_are_not_compared(self):
        items = compare_products(turn(warning=warning_day(starts='2026-09-20T18:30:00+00:00', ends='2026-09-21T18:30:00+00:00'),
                                      facts=[forecast_fact('0.5', '2026-09-16T00:30:00+05:30', '2026-09-16T23:30:00+05:30')]))
        self.assertEqual(items, [])

    def test_a_published_rain_statement_is_compared_with_the_forecast_too(self):
        passage = {'text': 'Heavy rainfall is likely over Bihar during the next 24 hours.', 'physical_page': '4',
                   'source_id': 'S64', 'family': 'national_bulletin', 'issue_date': '2026-09-14'}
        items = compare_products(turn(facts=[forecast_fact('0.0', '2026-09-16T00:30:00+05:30', '2026-09-16T23:30:00+05:30')],
                                      passages=[passage]))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['kind'], 'bulletin_and_forecast')
        self.assertEqual(items[0]['reading'], 'differ')
        self.assertIn('page 4', json.dumps(items[0]['products'], ensure_ascii=False))

    def test_at_most_four_items_and_every_note_refuses_to_rank(self):
        days = [warning_day(label='day %d' % number,
                            starts='2026-09-%02dT18:30:00+00:00' % (15 + number),
                            ends='2026-09-%02dT18:30:00+00:00' % (16 + number)) for number in range(1, 7)]
        result = {'facts': [forecast_fact('0.5', '2026-09-16T00:30:00+05:30', '2026-09-30T23:30:00+05:30')],
                  'passages': [], 'warning_evidence': [{'district_warnings': days}]}
        items = compare_products(result)
        self.assertEqual(len(items), 4, 'the comparison is bounded')
        for item in items:
            for word in NOTE_WORDS:
                self.assertIn(word, item['note'])

    def test_no_comparison_carries_a_score_confidence_or_all_clear(self):
        items = compare_products(turn(warning=warning_day(),
                                      facts=[forecast_fact('0.5', '2026-09-16T00:30:00+05:30', '2026-09-16T23:30:00+05:30')]))
        text = json.dumps(items, ensure_ascii=False).lower()
        for forbidden in ('confidence', 'score:', '%', 'probability of warning', 'all-clear meaning'):
            self.assertNotIn(forbidden, text)
        sentence = summarise(items)
        self.assertIn('neither is ranked', sentence)
        self.assertIn('not a score', sentence)
        self.assertIn('not an all-clear', sentence)
        self.assertLess(len(sentence), 600)

    def test_a_turn_with_one_product_has_nothing_to_compare(self):
        self.assertEqual(compare_products(turn(facts=[forecast_fact('0.5', '2026-09-16T00:30:00+05:30', '2026-09-16T23:30:00+05:30')])), [])
        self.assertEqual(compare_products(turn(warning=warning_day())), [])
        self.assertIsNone(summarise([]))


if __name__ == '__main__':
    unittest.main()
