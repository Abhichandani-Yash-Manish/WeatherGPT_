"""The shape of a written answer: what it states, what it repeats, and what it recites.

Measured 21 September 2026, on the live engine before any of this existed: a station reading was
answered with wind speed 0.0 and pressure 1009.0 while the same station's report held 26 °C, 94 %
humidity and mist; the fix for that made the answers right and long, and one of them named eleven
separate measures; and every answer about a model forecast said "not an observation or a district
average" and then had "not observed conditions or district averages" appended under it. Each repair
below is asserted from both sides - it must catch what it exists to catch, and it must not catch a
correct answer - because a check that refuses good prose is a worse defect than the one it fixes.
"""
import json
import unittest

from weathergpt_data.conversation import (composer_evidence, composer_fact, composer_floor,
                                          window_label)
from weathergpt_data.leadline import carried_by, prose_shape, series_recited


def fact(id_, parameter, value, unit=None, start='2026-09-21T00:30:00+05:30',
         end='2026-09-21T01:30:00+05:30', **extra):
    return {'id': id_, 'parameter': parameter, 'value': value, 'unit': unit, 'label': parameter,
            'place': 'Ahmedabad, Gujarat', 'start': start, 'end': end, 'sample_at': start,
            'observed_at': start, 'source_id': 'S21', 'evidence_kind': 'forecast',
            'source_locators': [], **extra}


class RepeatedClauseTests(unittest.TestCase):
    """A caveat the answer already carries is not appended under it a second time."""

    def test_the_caveat_a_forecast_answer_already_makes_is_not_repeated(self):
        clause = 'These are model forecasts for the selected points, not observed conditions or district averages.'
        answer = ('No rain is forecast for Ahmedabad tomorrow: 0.0 mm. That figure is a model forecast for '
                  'the place point, not an observation or a district average, and conditions can change.')
        self.assertTrue(carried_by(clause, answer))

    def test_a_rewritten_caveat_is_still_the_same_caveat(self):
        clause = ('Wave values are model output for the returned sea grid cell, not an official marine bulletin, '
                  'a named sea-area forecast, or a measured buoy observation.')
        answer = ('These are model values for the sea grid cell about 6 km from Kochi, not an official marine '
                  'bulletin or a measured buoy observation.')
        self.assertTrue(carried_by(clause, answer))

    def test_a_short_caveat_is_matched_when_the_answer_says_it(self):
        self.assertTrue(carried_by(' conditions can change.',
                                   '...and conditions can change. Source: GFS forecast.'))

    def test_a_caveat_the_answer_does_not_make_is_appended(self):
        clause = 'An absence of matching official guidance is not an all-clear.'
        answer = 'Yes - a yellow warning is in force for Patna today for thunderstorm and squall.'
        self.assertFalse(carried_by(clause, answer))

    def test_a_different_limit_on_the_same_subject_is_not_mistaken_for_a_repeat(self):
        clause = 'Each probability concerns its own hour (>0.1 mm), not the chance for the whole requested period.'
        self.assertFalse(carried_by(clause, 'The rain chance peaks at 40% at 15:00 IST.'))

    def test_a_clause_of_one_word_cannot_be_matched_by_accident(self):
        self.assertFalse(carried_by('Rainfall.', 'Rainfall of 0.0 mm is forecast tomorrow.'))


class RecitationTests(unittest.TestCase):
    """A retrieval is summarised, never recited."""

    def supplied(self, count):
        return {'facts': [{'id': 'f%d' % i, 'parameter': 'measure_%d' % i, 'value': str(10 + i)}
                          for i in range(count)]}

    def test_a_sentence_that_answers_is_not_a_recitation(self):
        text = ('Ahmedabad is 26 °C with 94% humidity and mist at the station 13 km away. '
                'The model keeps it near 25 °C with no rain for the next two hours.')
        self.assertFalse(series_recited(text, self.supplied(12)))

    def test_naming_every_measure_the_station_reported_is_a_recitation(self):
        text = ' '.join('%d' % (10 + i) for i in range(11))
        self.assertTrue(series_recited(text, self.supplied(12)))

    def test_writing_one_series_out_hour_by_hour_is_a_recitation(self):
        supplied = {'facts': [{'id': 'f%d' % i, 'parameter': 'temperature_2m', 'value': str(20 + i)}
                              for i in range(9)]}
        self.assertTrue(series_recited('Temperatures run 20 21 22 23 24 25 degrees.', supplied))

    def test_a_small_retrieval_cannot_be_recited(self):
        """Nothing to recite: the rule applies to a retrieval wider than the budget, not to every turn."""
        self.assertFalse(series_recited('26 °C, mist, 94% humidity.', self.supplied(3)))

    def test_the_shape_counts_measures_and_depth(self):
        shape = prose_shape('It is 26 °C with 94% humidity and mist, holding 25 °C for two hours.',
                            {'facts': [{'id': 'a', 'parameter': 't', 'value': '26'},
                                       {'id': 'b', 'parameter': 'h', 'value': '94'},
                                       {'id': 'c', 'parameter': 't2', 'value': '25'},
                                       {'id': 'd', 'parameter': 'w', 'value': '9'}]})
        self.assertEqual(shape['measures_stated'], 3)
        self.assertEqual(shape['measures_supplied'], 4)


class ComposerEvidenceTests(unittest.TestCase):
    """The composer is handed the answer's material, not the database."""

    def result(self):
        return {'plan': {'tasks': [{'parameters': ['temperature_2m']}]},
                'facts': [fact('f1', 'mslp', '1009.0'), fact('f2', 'temperature_2m', '26'),
                          fact('f3', 'temperature_2m', '25.4'), fact('f4', 'temperature_2m', '25.1'),
                          fact('f5', 'temperature_2m', '24.8'), fact('f6', 'visibility', '3000'),
                          fact('f7', 'present_weather', 'mist')]}

    def test_the_named_measure_leads_and_pressure_does_not(self):
        material, further = composer_evidence(self.result())
        self.assertEqual(material[0]['parameter'], 'temperature_2m')

    def test_a_series_arrives_as_its_range_and_not_as_its_rows(self):
        material, _further = composer_evidence(self.result())
        temperatures = [row for row in material if row['parameter'] == 'temperature_2m']
        self.assertEqual(len(temperatures), 1)
        self.assertIn('–', temperatures[0]['value'])

    def test_a_long_series_keeps_the_rows_its_range_is_made_of(self):
        """A range answers "how much does this vary". It cannot answer "which year was the wettest".

        Measured 21 September 2026: that question retrieved all 110 published years, the collapse
        replaced them with "923.7–1488.8 mm", and the answer said the evidence did not identify the
        year. The highest and lowest rows now travel with the range - two rows out of a hundred and
        ten, each a real retrieved row carrying its own id and year.
        """
        from weathergpt_data.conversation import EXTREMES_WORTH_KEEPING_ABOVE
        rows = [fact('y%d' % year, 'rainfall', str(900 + year)) for year in range(1, 40)]
        material, _further = composer_evidence({**self.result(), 'facts': rows})
        rainfall = [row for row in material if row['parameter'] == 'rainfall']
        self.assertEqual(len(rainfall), 3, 'the range, the highest and the lowest')
        self.assertIn('–', rainfall[0]['value'])
        self.assertIn('highest', rainfall[1]['label'])
        self.assertIn('lowest', rainfall[2]['label'])
        self.assertEqual(rainfall[1]['value'], '939')
        self.assertEqual(rainfall[2]['value'], '901')
        self.assertGreater(len(rows), EXTREMES_WORTH_KEEPING_ABOVE)

    def test_a_short_series_does_not_get_them(self):
        """The highest and lowest of four hourly temperatures ARE most of those four."""
        material, _further = composer_evidence(self.result())
        self.assertEqual(len([r for r in material if r['parameter'] == 'temperature_2m']), 1)

    def test_the_rest_travels_with_the_answer_rather_than_being_withheld(self):
        """Nothing is silently dropped: every retrieved row is either material or named as further."""
        result = self.result()
        material, further = composer_evidence(result)
        material_ids = {row['id'] for row in material}
        # A range stands for the rows it summarised, so they count as material too.
        material_ids |= {row['id'] for row in result['facts'] if row['parameter'] == 'temperature_2m'}
        covered = material_ids | {row['id'] for row in further}
        self.assertEqual(covered, {row['id'] for row in result['facts']})
        self.assertTrue(all(row.get('id') for row in further))

    def test_the_composer_is_given_a_window_in_words_and_no_raw_instant(self):
        shown = composer_fact(fact('f1', 'temperature_2m', '26'))
        self.assertEqual(shown['window'], window_label('2026-09-21T00:30:00+05:30', '2026-09-21T01:30:00+05:30'))
        for key in ('start', 'end', 'sample_at', 'observed_at'):
            self.assertNotIn(key, shown)
        self.assertEqual(shown['value'], '26')

    def test_the_number_a_renderer_stated_is_repeatable(self):
        """A trend is "54.7 mm/decade" in the sentence and 54.654 in the calculation record."""
        result = {'tool_answer': 'Ahmedabad, Gujarat: descriptive rainfall trend 54.7 mm/decade over 1981–2010.',
                  'held_clauses': [], 'lead': 'unused'}
        self.assertIn('54.7', composer_floor(result))

    def test_a_held_clause_is_not_handed_to_the_model_to_echo(self):
        """Otherwise the model writes it, the engine sees it as carried, and the reader gets it anyway."""
        clause = 'These are model forecasts for the selected points, not observed conditions or district averages.'
        result = {'tool_answer': 'Precipitation: 0.0 mm. ' + clause, 'held_clauses': [clause]}
        self.assertNotIn(clause, composer_floor(result))
        self.assertIn('0.0 mm', composer_floor(result))

    def test_the_payload_carries_no_iso_instant(self):
        """The payload is what the composer sees; a timestamp it cannot see is one it cannot print."""
        material, _further = composer_evidence(self.result())
        for row in material:
            blob = json.dumps(composer_fact(row))
            self.assertNotIn('T00:30:00', blob)


if __name__ == '__main__':
    unittest.main()
