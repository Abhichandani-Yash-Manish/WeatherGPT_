"""Native-script place names with their locative marker removed, per language.

Measured on 15 September 2026: "কাল সকালে কলকাতায় বৃষ্টি হবে?", "آج شام دلی میں بارش ہوگی؟",
"ਨਾਲ਼ੇ ਅੰਮ੍ਰਿਤਸਰ ਵਿੱਚ ਮੀਂਹ", "നാളെ രാവിലെ കൊച്ചിയിൽ" and "ನಾಳೆ ಅಹಮದಾಬಾದ್‌ನಲ್ಲಿ" each read no place
at all, so a question that named its own city was answered by asking which city was meant.
Bengali, Gurmukhi, Odia and the Arabic script were missing from the character class, the marker
list held only the forms four languages happen to use, and a marker that is a prefix of another
took precedence over the longer one.

Two limits are recorded here rather than papered over: Marathi (पुण्यात for पुणे) and Tamil
(அகமதாபாத்தில் for அகமதாபாத்) inflect the stem before the marker, so the extracted name is a stem
the catalogue may not hold. Those two are asked for by confirmation, not answered for the wrong
place.
"""
import unittest

from weathergpt_data.rule_planner import places_of


def extracted(question):
    return [place['name'] for place in places_of(question)]


class NativeScriptPlaceTests(unittest.TestCase):
    def test_every_measured_script_yields_the_name_it_was_given(self):
        cases = (
            ('ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಅಹಮದಾಬಾದ್‌ನಲ್ಲಿ ಮಳೆ ಬರುತ್ತದೆಯೇ?', 'ಅಹಮದಾಬಾದ್'),
            ('কাল সকালে কলকাতায় বৃষ্টি হবে?', 'কলকাতা'),
            ('আজি ৰাতিপুৱা গুৱাহাটীত বৰষুণ হব?', 'গুৱাহাটী'),
            ('آج شام دلی میں بارش ہوگی؟', 'دلی'),
            ('ਕੱਲ੍ਹ ਅੰਮ੍ਰਿਤਸਰ ਵਿੱਚ ਮੀਂਹ ਪਵੇਗਾ?', 'ਅੰਮ੍ਰਿਤਸਰ'),
            ('రేపు ఉదయం హైదరాబాద్‌లో వర్షం పడుతుందా?', 'హైదరాబాద్'),
            ('നാളെ രാവിലെ കൊച്ചിയിൽ മഴ പെയ്യുമോ?', 'കൊച്ചി'),
            ('कल सुबह वडोदरा में मौसम कैसा रहेगा?', 'वडोदरा'),
            ('ଆଜି ଭୁବନେଶ୍ୱରରେ ବର୍ଷା ହେବ?', 'ଭୁବନେଶ୍ୱର'),
        )
        for question, expected in cases:
            with self.subTest(question=question):
                self.assertIn(expected, extracted(question))

    def test_a_city_and_its_state_stay_one_place_with_a_state(self):
        places = places_of('કલ અમદાવાદ, ગુજરાતમાં વરસાદ પડશે?')
        self.assertEqual([place['name'] for place in places], ['અમદાવાદ'])
        self.assertEqual(places[0]['state'], 'ગુજરાત')

    def test_a_marker_that_is_a_prefix_of_another_does_not_win(self):
        # The capture is greedy, so with 'ൽ' listed before 'യിൽ' this read കൊച്ചിയ instead of കൊച്ചി.
        self.assertIn('കൊച്ചി', extracted('നാളെ കൊച്ചിയിൽ മഴ പെയ്യുമോ?'))
        self.assertNotIn('കൊച്ചിയ', extracted('നാളെ കൊച്ചിയിൽ മഴ പെയ്യുമോ?'))

    def test_an_inflected_stem_is_recorded_as_a_limit_not_answered_silently(self):
        # Marathi and Tamil change the stem before the marker; the extracted name is a stem, and
        # the engine asks for confirmation rather than answering for a place nobody named.
        self.assertEqual(extracted('उद्या सकाळी पुण्यात पाऊस पडेल का?'), ['पुण्या'])
        self.assertEqual(extracted('நாளை காலை அகமதாபாத்தில் மழை பெய்யுமா?'), ['அகமதாபாத்த'])

    def test_a_question_with_no_place_extracts_nothing(self):
        # The English extractor handles a Latin place name; this check is about a question that
        # names no place at all, in a script and in plain English.
        self.assertEqual(extracted('कल मौसम कैसा रहेगा?'), [])
        self.assertEqual(extracted('Will it rain tomorrow morning?'), [])


if __name__ == '__main__':
    unittest.main()
