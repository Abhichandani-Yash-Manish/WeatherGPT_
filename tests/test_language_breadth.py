"""Language breadth: every language whose writing can be measured is measured, and nothing is claimed.

The script table behind the adherence check held only Hindi and Gujarati, so an answer promised in Tamil,
Bengali, Punjabi, Odia, Kannada, Telugu, Malayalam, Marathi or Urdu was never checked at all. These checks
pin the registry-derived table, the wrong-script detection for every measurable language, the rendered path
with protected values, and the two honest outcomes when a rendering cannot be verified.
"""
import re
import unittest

from weathergpt_data import answer_language
from weathergpt_data.dialogue import SCRIPTS, language_gap
from weathergpt_data.languages import LANGUAGES, script_pattern
from weathergpt_data.rendering import SENTINEL_PATTERN


def tamil(text, target, source):
    """A stub translator that answers in Tamil and keeps every placeholder."""
    kept = [match.group(0) for match in SENTINEL_PATTERN.finditer(text)]
    body = 'தமிழில் எழுதப்பட்ட வாக்கியம் இது'
    return body + ' ' + ' '.join(kept)


def result(answer='Rainfall of 35 mm is forecast for Ahmedabad tomorrow.', status='answered'):
    return {'answer': answer, 'status': status, 'notes': [], 'facts': [], 'trace': {'generation': None}}


class ScriptTableTests(unittest.TestCase):
    def test_every_language_whose_writing_can_be_measured_is_checked(self):
        expected = {code for code in LANGUAGES if script_pattern(code)}
        self.assertEqual(set(SCRIPTS), expected, 'the table is the registry, not a hand-picked pair')
        for code in ['ta', 'bn', 'pa', 'od', 'ml', 'kn', 'te', 'mr', 'ur', 'as', 'ne', 'sat']:
            with self.subTest(code=code):
                self.assertIn(code, SCRIPTS)
        for code in ['en', 'hi-Latn', 'hi-latn']:
            self.assertNotIn(code, SCRIPTS, 'a Latin-script language cannot be measured this way')

    def test_an_answer_in_the_wrong_script_is_flagged_for_every_measurable_language(self):
        english = 'Rainfall of 35 mm is forecast for Ahmedabad tomorrow morning, with light winds and 24 degrees.'
        for code, pattern in sorted(SCRIPTS.items()):
            with self.subTest(code=code):
                native = pattern.split('-')[0] * 40
                self.assertTrue(language_gap(english, code), 'an English answer is not the promised language')
                self.assertFalse(language_gap(native, code), 'a native-script answer is not flagged')


class DeliveryBreadthTests(unittest.TestCase):
    def test_tamil_is_rendered_with_its_values_kept(self):
        packet = answer_language.deliver(result(), 'ta', translator=tamil)
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'rendered_with_protected_values')
        self.assertIn('35', packet['answer'], 'the value reaches the reader as the original characters')
        self.assertTrue(re.search('[\u0B80-\u0BFF]', packet['answer']))

    def test_a_language_with_no_verifiable_script_is_reported_rather_than_claimed(self):
        packet = answer_language.deliver(result(), 'hi-Latn', translator=tamil)
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'unverifiable_script')
        self.assertTrue(any('cannot be verified here' in note for note in packet['notes']))

    def test_without_a_service_the_source_language_stays_and_the_answer_says_so(self):
        packet = answer_language.deliver(result(), 'ta', translator=None)
        self.assertEqual(packet['status'], 'partial')
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'no_language_service')
        self.assertIn('35 mm', packet['answer'])
        self.assertTrue(any('could not be written in the requested language' in note for note in packet['notes']))

    def test_a_rendering_that_drops_a_value_keeps_the_source_language(self):
        def lossy(text, target, source):
            return 'தமிழ் வாக்கியம் ' + SENTINEL_PATTERN.sub('', text)
        packet = answer_language.deliver(result(), 'ta', translator=lossy)
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'values_did_not_survive')
        self.assertIn('35 mm', packet['answer'])
        self.assertEqual(packet['status'], 'partial')


if __name__ == '__main__':
    unittest.main()
