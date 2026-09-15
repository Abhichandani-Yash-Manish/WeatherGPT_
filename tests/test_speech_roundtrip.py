"""The speech round-trip measurement reads presence, never equality or accuracy."""
import unittest

from scripts.measure_speech_roundtrip import PROBES, analyse


class AnalysisTests(unittest.TestCase):
    def test_digits_and_words_both_count_as_a_number(self):
        probe = PROBES['hi']
        with_digits = analyse('अहमदाबाद में 35 मिलीमीटर वर्षा, कोई चेतावनी नहीं', probe)
        self.assertTrue(with_digits['number_as_digits'])
        self.assertTrue(with_digits['place_present'])
        self.assertTrue(with_digits['unit_present'])
        self.assertTrue(with_digits['negation_marker_present'])
        as_words = analyse('अहमदाबाद में पैंतीस मिलीमीटर वर्षा, कोई चेतावनी नहीं', probe)
        self.assertFalse(as_words['number_as_digits'], 'A word form is not a digit failure')
        self.assertTrue(as_words['negation_marker_present'])

    def test_a_dropped_negation_is_visible_as_absence(self):
        probe = PROBES['gu']
        row = analyse('અમદાવાદમાં 35 મિલિમીટર વરસાદ', probe)
        self.assertTrue(row['place_present'])
        self.assertFalse(row['negation_marker_present'])


if __name__ == '__main__':
    unittest.main()
