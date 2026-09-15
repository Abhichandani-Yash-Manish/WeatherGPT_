"""Five planner repairs the paraphrase measurement found, pinned.

Measured on 15 September 2026 with scripts/measure_paraphrases.py: the rules-first planner held 25 of
34 paraphrase variants of ten declared shapes. Each miss below was a shape a reader would ask for and
the planner would not recognise in that wording.
"""
import unittest
from datetime import datetime, timezone

from weathergpt_data.rule_planner import rule_request, station_code

NOW = datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc)


def shape(question):
    plan = rule_request(question, NOW)
    return None if plan is None else sorted((task['kind'], task['operation']) for task in plan['tasks'])


class AgrometBulletinTests(unittest.TestCase):
    def test_a_state_agromet_advisory_is_a_document_read(self):
        # "What does the Gujarat state agromet advisory say about irrigation?" was left to a model.
        for question in ('What does the Gujarat state agromet advisory say about irrigation?',
                         'Gujarat state agromet advisory me irrigation ke baare me kya likha hai?',
                         'For irrigation, what does the Gujarat state agromet advisory say?',
                         'Tell me what the Gujarat state agromet advisory says about irrigation.'):
            self.assertEqual(shape(question), [('document', 'lookup')], question)


class StationCodeTests(unittest.TestCase):
    def test_a_station_code_is_read_as_a_station_request(self):
        for question in ('What is the current weather at VOBL?',
                         'VOBL ka current weather kya hai?',
                         'Current weather at VOBL, please.'):
            self.assertEqual(shape(question), [('aviation', 'lookup')], question)

    def test_a_known_acronym_is_not_mistaken_for_a_station(self):
        # IMD, GFS and their siblings are product names, not stations.
        for acronym in ('IMD', 'GFS', 'WRF', 'AWS', 'CAP'):
            self.assertIsNone(station_code('What does ' + acronym + ' say about rainfall?'), acronym)
        self.assertEqual(station_code('What is the weather at VOBL?'), 'VOBL')

    def test_a_question_with_no_code_has_no_station(self):
        self.assertIsNone(station_code('Will it rain in Ahmedabad tomorrow?'))


class HinglishHistoryTests(unittest.TestCase):
    def test_a_hinglish_past_question_with_a_year_is_a_history_read(self):
        # "Chennai district, Tamil Nadu me 1995 me kitni barish hui thi?" was planned as a forecast.
        self.assertEqual(shape('Chennai district, Tamil Nadu me 1995 me kitni barish hui thi?'),
                         [('history', 'lookup')])
        self.assertEqual(shape('What was the rainfall in Chennai district, Tamil Nadu in 1995?'),
                         [('history', 'lookup')])

    def test_a_hinglish_present_question_without_a_year_stays_a_forecast(self):
        self.assertEqual(shape('Chennai me kal barish hogi?'), [('forecast', 'lookup')])


class TideTests(unittest.TestCase):
    def test_tide_is_out_of_scope_rather_than_a_guess(self):
        # No tide product is connected; the honest answer is the gap, not a marine lookup.
        for question in ('What is the tide at Kochi tomorrow?', 'Kochi me kal tide kya hai?',
                         'Tide timings for Kochi tomorrow?'):
            self.assertEqual(shape(question), [('research', 'lookup')], question)


class CrosscheckWordingTests(unittest.TestCase):
    def test_the_crosscheck_shape_survives_word_order_and_hinglish(self):
        # "Ahmedabad me kal barish ke liye models compare kijiye." was planned as a plain lookup.
        for question in ('Compare the models for rainfall in Ahmedabad tomorrow.',
                         'Ahmedabad me kal barish ke liye models compare kijiye.',
                         'Do the models agree on rainfall in Ahmedabad tomorrow?',
                         'Compare forecast sources for Ahmedabad rainfall tomorrow.'):
            self.assertEqual(shape(question), [('forecast', 'crosscheck')], question)

    def test_a_plain_forecast_is_not_a_crosscheck(self):
        self.assertEqual(shape('Will it rain in Ahmedabad tomorrow?'), [('forecast', 'lookup')])


class NativeScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from weathergpt_data.gazetteer import Gazetteer
        cls.index = Gazetteer()

    def test_a_devanagari_place_with_a_devanagari_state_resolves_on_the_name_alone(self):
        # Measured live: the place matched and the state filter then emptied the list, because
        # the catalogue's admin1 field is Latin. The reading is disclosed rather than silent.
        rows = self.index.search('अहमदाबाद', 'गुजरात')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'Ahmedabad')
        self.assertIn('another script', rows[0]['state_match_basis'])

    def test_a_wrong_latin_state_is_still_refused(self):
        self.assertEqual(self.index.search('Ahmedabad', 'Kerala'), [])

    def test_an_indic_question_is_planned_in_its_own_language(self):
        self.assertEqual(shape('कल अहमदाबाद, गुजरात में सुबह बारिश होगी?'), [('forecast', 'lookup')])
        self.assertEqual(shape('અમદાવાદમાં આવતીકાલે વરસાદ થશે?'), [('forecast', 'lookup')])

    def test_a_sea_area_is_a_valid_place_kind_for_both_planners(self):
        # The plan validator refused 'sea_area' until 15 September 2026, which quietly handed
        # every coastal question to a model instead of the rules floor.
        self.assertEqual(shape('What are the wave conditions off the Kerala coast tomorrow?'), [('marine', 'lookup')])


if __name__ == '__main__':
    unittest.main()