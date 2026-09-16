"""Choosing the output language, and delivering an answer in it without overclaiming.

Offline, against stub translators. The behaviour these hold is the floor the project
already had — an answer that could not be written in the requested language says so
and is downgraded — plus the new tier above it, where a rendering is presented only
when every protected value survived.
"""
import unittest

from weathergpt_data import answer_language
from weathergpt_data.transport import SourceError

HINDI = ('अहमदाबाद में कल '
         'वर्षा होने का '
         'पूर्वानुमान है '
         'और यह एक मॉडल पूर्वानुमान है')


def result(answer='Rainfall of 35 mm is forecast for Ahmedabad tomorrow.', status='answered', **extra):
    packet = {'answer': answer, 'status': status, 'notes': [], 'facts': [],
              'trace': {'generation': None}}
    packet.update(extra)
    return packet


def devanagari(text, target, source):
    """A stub that returns Devanagari prose and keeps every placeholder."""
    from weathergpt_data.rendering import SENTINEL_PATTERN
    kept = SENTINEL_PATTERN.findall(text)
    body = 'अनुवादित वाक्य यहाँ है और सभी मान अपने मूल अक्षरों में हैं'
    return body + ' ' + ' '.join('#V%d#' % int(number) for number in kept)


def lossy(text, target, source):
    from weathergpt_data.rendering import SENTINEL_PATTERN
    return SENTINEL_PATTERN.sub('', text) + ' अनुवाद'


class SelectionTests(unittest.TestCase):
    def test_an_explicit_choice_wins_over_what_the_planner_read(self):
        state = {}
        target, reason = answer_language.target_language(
            {'output_language': 'hi'}, state, {'language': 'gu'})
        self.assertEqual((target, reason), ('hi', 'user_selected'))

    def test_an_explicit_choice_is_remembered_for_later_turns(self):
        state = {}
        answer_language.target_language({'output_language': 'gu'}, state, {})
        target, reason = answer_language.target_language({}, state, {'language': 'en'})
        self.assertEqual((target, reason), ('gu', 'remembered_user_selection'))

    def test_an_empty_choice_clears_the_selection(self):
        state = {'output_language': 'gu'}
        target, reason = answer_language.target_language(
            {'output_language': ''}, state, {'language': 'hi'})
        self.assertEqual((target, reason), ('hi', 'inferred_from_question'))
        self.assertNotIn('output_language', state)

    def test_the_planner_reading_is_used_when_nothing_was_chosen(self):
        target, reason = answer_language.target_language({}, {}, {'language': 'ta'})
        self.assertEqual((target, reason), ('ta', 'inferred_from_question'))

    def test_no_language_anywhere_is_not_invented(self):
        self.assertEqual(answer_language.target_language({}, {}, {}), (None, 'none'))

    def test_an_unsupported_choice_is_refused_rather_than_ignored(self):
        with self.assertRaises(SourceError):
            answer_language.target_language({'output_language': 'zz'}, {}, {})

    def test_a_sarvam_style_code_is_accepted(self):
        target, _ = answer_language.target_language({'output_language': 'mr-IN'}, {}, {})
        self.assertEqual(target, 'mr')


class DeliveryTests(unittest.TestCase):
    def test_english_needs_no_rendering_and_claims_none(self):
        packet = answer_language.deliver(result(), 'en')
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'not_applicable')
        self.assertEqual(packet['status'], 'answered')

    def test_a_template_written_answer_is_recognised_and_left_alone(self):
        packet = answer_language.deliver(result(answer=HINDI), 'hi', translator=devanagari)
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'written_by_template')
        self.assertEqual(packet['answer'], HINDI)

    def test_without_a_service_the_answer_stays_and_the_response_is_downgraded(self):
        packet = answer_language.deliver(result(), 'hi', translator=None)
        self.assertEqual(packet['status'], 'partial')
        self.assertIn('35 mm', packet['answer'])
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'no_language_service')
        self.assertTrue(any('requested language' in note for note in packet['notes']))

    def test_a_successful_rendering_keeps_every_value_as_original_characters(self):
        packet = answer_language.deliver(result(), 'hi', translator=devanagari)
        self.assertEqual(packet['status'], 'answered')
        self.assertIn('35 mm', packet['answer'])
        self.assertEqual(packet['answered_language'], 'hi')
        self.assertEqual(packet['trace']['generation']['language_adherence'],
                         'rendered_with_protected_values')
        self.assertTrue(any('original characters' in note for note in packet['notes']))

    def test_a_rendering_that_loses_a_value_is_refused_and_the_source_kept(self):
        packet = answer_language.deliver(result(), 'hi', translator=lossy)
        self.assertEqual(packet['status'], 'partial')
        self.assertIn('35 mm', packet['answer'])
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'values_did_not_survive')

    def test_a_rendering_in_another_script_is_named_as_that_not_as_a_service_problem(self):
        # Measured need, 15 September 2026: a Tamil rendering that carried Telugu characters
        # was refused by the gate and then reported to the reader as an unreachable service.
        def telugu(text, target, source):
            from weathergpt_data.rendering import SENTINEL_PATTERN
            kept = SENTINEL_PATTERN.findall(text)
            body = 'అనువాదిత వాక్యం ఇక్కడ ఉంది మరియు విలువలు సురక్షితంగా ఉన్నాయి'
            return body + ' ' + ' '.join('#V%d#' % int(number) for number in kept)

        packet = answer_language.deliver(result(), 'hi', translator=telugu)
        self.assertEqual(packet['status'], 'partial')
        self.assertIn('35 mm', packet['answer'])
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'rendered_in_another_script')
        self.assertTrue(any('characters from another script' in note for note in packet['notes']))
    def test_a_service_that_cannot_be_reached_is_named_as_that(self):
        def unreachable(text, target, source):
            raise SourceError('The language service could not be reached')

        packet = answer_language.deliver(result(), 'hi', translator=unreachable)
        self.assertEqual(packet['trace']['generation']['language_adherence'],
                         'language_service_unavailable')
        self.assertEqual(packet['status'], 'partial')

    def test_a_held_safety_clause_is_disclosed_to_the_reader(self):
        packet = answer_language.deliver(
            result(answer='Rainfall of 35 mm is forecast. No warning is in force.'),
            'hi', translator=devanagari)
        self.assertTrue(any('source language on purpose' in note for note in packet['notes']))
        self.assertIn('No warning is in force.', packet['answer'])

    def test_a_latin_script_language_never_claims_a_verified_rendering(self):
        packet = answer_language.deliver(result(), 'hi-Latn', translator=devanagari)
        # Not "not applicable": the reader asked for romanised output, the rendering cannot be verified
        # by script, and the answer says so rather than passing English off as that language.
        self.assertEqual(packet['trace']['generation']['language_adherence'], 'unverifiable_script')
        self.assertTrue(any('cannot be verified here' in note for note in packet['notes']))

    def test_the_trace_always_records_what_was_asked_for_and_why(self):
        packet = answer_language.deliver(result(), 'hi', translator=devanagari,
                                         reason='user_selected')
        self.assertEqual(packet['trace']['generation']['requested_language'], 'hi')
        self.assertEqual(packet['trace']['generation']['language_selection'], 'user_selected')


class IdentityTests(unittest.TestCase):
    def test_place_names_from_the_answer_s_own_facts_are_protected(self):
        packet = result(facts=[{'place': 'Ahmedabad'}, {'place': 'Rajkot'}],
                        resolved_points={'Ahmedabad': {'label': 'Ahmedabad, Gujarat', 'admin1': 'Gujarat'}})
        found = answer_language.identities(packet)
        for name in ('Ahmedabad', 'Rajkot', 'Ahmedabad, Gujarat', 'Gujarat'):
            self.assertIn(name, found)

    def test_longer_names_are_protected_before_the_shorter_ones_inside_them(self):
        packet = result(resolved_points={'x': {'label': 'Ahmedabad, Gujarat', 'admin1': 'Gujarat'}})
        found = answer_language.identities(packet)
        self.assertLess(found.index('Ahmedabad, Gujarat'), found.index('Gujarat'))

    def test_district_names_from_retrieved_passages_are_protected(self):
        packet = result(passages=[{'district': 'Surat', 'state': 'Gujarat'}])
        self.assertIn('Surat', answer_language.identities(packet))


if __name__ == '__main__':
    unittest.main()
