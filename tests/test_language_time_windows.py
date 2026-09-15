"""Day, part-of-day and measure words, audited per language rather than trusted as a flat list.

Measured on 15 September 2026: "કલ અમદાવાદ, ગુજરાતમાં વરસાદ પડશે?" ("will it rain in Ahmedabad,
Gujarat tomorrow?") read no day word at all, because the Gujarati table held only the formal
આવતીકાલે, so the turn asked for a date instead of answering. Eleven of the twenty-three
writable languages had no day word and no part-of-day word. These checks ask each language for
the same tomorrow question and require either a window or a declared, named absence; a wrong
day word would answer for the wrong day, so an unread language is recorded, never guessed.
"""
import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from weathergpt_data.languages import LANGUAGES
from weathergpt_data.rule_planner import (CORE_MEASURES, DAY_WORDS, MEASURE_WORDS, PART_WINDOWS, TIME_WORDS,
                                          UNREAD_MEASURE_WORDS, UNREAD_TIME_WORDS, WINDOWS, boundary_pattern,
                                          rule_request, variables_of, window_for)

IST = ZoneInfo('Asia/Kolkata')
# 04:00 IST, before every part-of-day window, so "the coming morning" is today.
EARLY = datetime(2026, 9, 15, 4, 0, tzinfo=IST)
# 14:00 IST, after the morning window has begun, so the coming morning is tomorrow's.
LATE = datetime(2026, 9, 15, 14, 0, tzinfo=IST)


class CoverageTests(unittest.TestCase):
    def test_every_writable_language_is_either_covered_or_declared_unread(self):
        missing = sorted(set(LANGUAGES) - {'en'} - set(TIME_WORDS) - set(UNREAD_TIME_WORDS))
        self.assertEqual(missing, [], 'A writable language is neither covered nor declared unread')
        self.assertEqual(sorted(set(TIME_WORDS) & set(UNREAD_TIME_WORDS)), [],
                         'A language cannot be both covered and declared unread')

    def test_a_covered_language_carries_a_today_word_a_tomorrow_word_and_every_part(self):
        for code, words in TIME_WORDS.items():
            with self.subTest(language=code):
                self.assertTrue(words.get('today'), code + ' has no today word')
                self.assertTrue(words.get('tomorrow'), code + ' has no tomorrow word')
                self.assertEqual(sorted(words.get('parts', {})), sorted(PART_WINDOWS), code + ' is missing a part of day')

    def test_a_declared_unread_language_says_what_it_is_missing(self):
        for code, name in UNREAD_TIME_WORDS.items():
            with self.subTest(language=code):
                self.assertIn(code, LANGUAGES)
                self.assertTrue(name)

    def test_every_word_can_match_itself_whole(self):
        # A word whose own boundary pattern cannot match it is a word the planner can never read;
        # the Indic parts of day were exactly this defect before boundary_pattern.
        for word in list(DAY_WORDS) + list(WINDOWS):
            with self.subTest(word=word):
                self.assertTrue(boundary_pattern(word).search(word), word + ' cannot match itself')

    def test_each_language_reads_its_own_tomorrow_word(self):
        for code, words in TIME_WORDS.items():
            start, end, explicit, basis = window_for(words['tomorrow'][0] + ' Ahmedabad', EARLY)
            with self.subTest(language=code, word=words['tomorrow'][0]):
                self.assertEqual((start[:10], start[11:16], end[11:16]), ('2026-09-16', '00:30', '00:30'))
                self.assertFalse(explicit)
                self.assertIn(words['tomorrow'][0], basis)

    def test_each_language_reads_every_part_window(self):
        for code, words in TIME_WORDS.items():
            for part, variants in words['parts'].items():
                for variant in variants:
                    with self.subTest(language=code, part=part, word=variant):
                        start, end, explicit, basis = window_for(variant + ' Ahmedabad', EARLY)
                        self.assertEqual((start[11:16], end[11:16]), PART_WINDOWS[part])
                        self.assertIn(variant, basis)


class MeasuredCasesTests(unittest.TestCase):
    def test_the_gujarati_tomorrow_question_reads_tomorrow(self):
        start, end, explicit, basis = window_for('કલ અમદાવાદ, ગુજરાતમાં વરસાદ પડશે?', EARLY)
        self.assertEqual(start[:10], '2026-09-16')
        self.assertEqual(start[11:16], '00:30')
        self.assertEqual(end[11:16], '00:30')
        self.assertIn('કલ', basis)

    def test_a_part_of_day_with_no_day_word_is_the_coming_one(self):
        start, _, _, basis = window_for('Will it rain in the morning?', EARLY)
        self.assertEqual((start[:10], start[11:16]), ('2026-09-15', '09:30'))
        self.assertIn('coming', basis)
        # After the morning window has begun, the coming morning is tomorrow's.
        start, _, _, _ = window_for('Will it rain in the morning?', LATE)
        self.assertEqual((start[:10], start[11:16]), ('2026-09-16', '09:30'))
        # A named day still wins over the coming reading.
        start, _, _, _ = window_for('Will it rain tomorrow morning?', LATE)
        self.assertEqual((start[:10], start[11:16]), ('2026-09-16', '09:30'))

    def test_a_question_with_no_time_word_still_reads_no_window(self):
        self.assertEqual(window_for('Will it rain in Ahmedabad?', EARLY), ('', '', False, None))

    def test_an_unread_language_reads_no_window_rather_than_a_guessed_one(self):
        # Santali, Bodo, Manipuri and Kashmiri have no word in the tables, so the interval they
        # get is nothing and the engine asks for the date; recorded as a stated limit.
        for word in ('ᱛᱮᱦᱮᱸ', 'गाबोन', 'ꯍꯧꯖꯤꯛ'):
            with self.subTest(word=word):
                self.assertNotIn(word, DAY_WORDS)
                self.assertNotIn(word, WINDOWS)
        self.assertEqual(sorted(UNREAD_TIME_WORDS), ['brx', 'ks', 'mai', 'mni', 'sat'])


class MeasureCoverageTests(unittest.TestCase):
    """The four core measures, in every language the workspace can read a day word in.

    Measured on 15 September 2026: "آج شام دلی میں بارش ہوگی؟" had no rules plan at all, because
    the rain words held no Urdu; the same was true of Marathi पाऊस, Assamese বৰষুণ, Sindhi مينهن,
    Odia ବର୍ଷା and Nepali वर्षा, and those turns waited on a model that once failed validation.
    """

    def test_every_covered_language_has_a_word_for_each_core_measure(self):
        missing = [(code, measure) for code in LANGUAGES if code not in UNREAD_MEASURE_WORDS and code != 'en'
                   for measure in CORE_MEASURES if not MEASURE_WORDS[measure].get(code)]
        self.assertEqual(missing, [], 'A writable language has no word for a core measure')

    def test_every_measure_word_resolves_to_its_own_measure(self):
        for measure, by_language in MEASURE_WORDS.items():
            for code, words in by_language.items():
                for word in words:
                    with self.subTest(measure=measure, language=code, word=word):
                        self.assertTrue(boundary_pattern(word).search(word), word + ' cannot match itself')
                        self.assertIn(measure, variables_of(word))

    def test_a_declared_unread_language_is_named(self):
        self.assertEqual(sorted(UNREAD_MEASURE_WORDS), ['brx', 'ks', 'mai', 'mni', 'sat'])
        for code, name in UNREAD_MEASURE_WORDS.items():
            self.assertIn(code, LANGUAGES)
            self.assertTrue(name)

    def test_the_measured_questions_reach_the_rules_floor(self):
        cases = (
            ('آج شام دلی میں بارش ہوگی؟', 'precipitation'),
            ('उद्या सकाळी पुण्यात पाऊस पडेल का?', 'precipitation'),
            ('আজি বৰষুণ হব নেকি?', 'precipitation'),
            ('ڪالهه مينهن پوندو؟', 'precipitation'),
            ('ଆଜି ବର୍ଷା ହେବ?', 'precipitation'),
            ('आज वर्षा हुनेछ?', 'precipitation'),
            ('आज गर्मी कैसी रहेगी?', 'temperature_2m'),
            ('ನಾಳೆ ಗಾಳಿ ಹೇಗಿರುತ್ತದೆ?', 'wind_speed_10m'),
            ('இன்று மழை பெய்யுமா?', 'precipitation'),
        )
        for question, measure in cases:
            with self.subTest(question=question):
                self.assertIn(measure, variables_of(question))
                self.assertIsNotNone(rule_request(question, datetime(2026, 9, 15, 4, 0, tzinfo=timezone.utc), None),
                                     'the rules floor must plan this question, not a model')

    def test_a_general_weather_word_asks_for_the_whole_picture(self):
        # No single measure is named, so the rules floor reads the four parameters the planner
        # prompt already names for general weather, in the scripts the word is held in.
        for question in ('What will the weather be in Ahmedabad tomorrow morning?',
                         'અમદાવાદમાં હવામાન કેવું રહેશે?',
                         'कल सुबह वडोदरा में मौसम कैसा रहेगा?'):
            with self.subTest(question=question):
                plan = rule_request(question, datetime(2026, 9, 15, 4, 0, tzinfo=timezone.utc), None)
                self.assertIsNotNone(plan, 'the rules floor must plan a general weather question')
                self.assertEqual(sorted(plan['tasks'][0]['parameters']),
                                 sorted(['precipitation', 'temperature_2m', 'wind_speed_10m', 'relative_humidity_2m']))


if __name__ == '__main__':
    unittest.main()
