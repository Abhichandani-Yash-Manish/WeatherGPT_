"""Spoken access: transcript handling, speech refusal, and what audio is allowed to claim.

Offline, against stubs. Nothing here measures recognition or synthesis quality.

Two behaviours matter more than the plumbing. A transcript is a claim about what was
said and must be confirmable before it becomes a question, because place names and
numbers are exactly what a recogniser gets wrong. And speech is offered only in a
language this project measured, not every language the provider accepts, because
unintelligible audio is worse than no audio.
"""
import base64
import unittest
from unittest.mock import patch

from weathergpt_data import languages, speech
from weathergpt_data.workspace import Workspace

AUDIO = base64.b64encode(b'RIFF....WAVEfmt ' + b'\x00' * 256).decode()


def workspace():
    return Workspace.__new__(Workspace)


def heard(transcript='कल बारिश होगी', probability=0.97):
    return {'transcript': transcript, 'detected_language_code': 'hi-IN',
            'recognition_probability': probability,
            'probability_meaning': 'recognition confidence only',
            'language_supplied': False,
            'trace': {'service': 'sarvam', 'operation': 'speech_to_text', 'elapsed_s': 1.0,
                      'is_evidence': False}}


class TranscriptTests(unittest.TestCase):
    def transcribe(self, body, result=None):
        with patch.object(speech, 'transcribe', return_value=result or heard()):
            return workspace().transcribe(body)

    def test_a_transcript_must_be_confirmed_before_it_becomes_a_question(self):
        packet = self.transcribe({'audio_base64': AUDIO})
        self.assertTrue(packet['confirm_before_asking'])
        self.assertIn('place names', packet['why_confirm'].lower())

    def test_a_transcript_is_never_evidence(self):
        self.assertFalse(self.transcribe({'audio_base64': AUDIO})['is_evidence'])

    def test_recognition_confidence_is_labelled_as_recognition_only(self):
        packet = self.transcribe({'audio_base64': AUDIO})
        self.assertEqual(packet['recognition_probability'], 0.97)
        self.assertIn('recognition', packet['probability_meaning'].lower())
        self.assertNotIn('confidence', packet)
        self.assertNotIn('answer_confidence', packet)

    def test_a_missing_or_undecodable_recording_is_refused(self):
        for body in ({}, {'audio_base64': ''}, {'audio_base64': 'not base64!!'}):
            with self.assertRaises(ValueError):
                self.transcribe(body)

    def test_an_oversized_recording_is_refused_before_it_is_sent(self):
        with self.assertRaises(ValueError):
            self.transcribe({'audio_base64': 'A' * (Workspace.MAX_AUDIO_UPLOAD + 1)})

    def test_an_unexpected_field_is_refused(self):
        with self.assertRaises(ValueError):
            self.transcribe({'audio_base64': AUDIO, 'model': 'something'})

    def test_a_non_audio_content_type_is_refused(self):
        with self.assertRaises(ValueError):
            self.transcribe({'audio_base64': AUDIO, 'content_type': 'text/html'})

    def test_an_unsupported_language_is_refused_rather_than_ignored(self):
        with self.assertRaises(ValueError):
            self.transcribe({'audio_base64': AUDIO, 'language': 'zz'})

    def test_the_detected_language_is_reported_as_the_recogniser_s_own_reading(self):
        packet = self.transcribe({'audio_base64': AUDIO})
        self.assertEqual(packet['detected_language_code'], 'hi-IN')
        self.assertFalse(packet['language_supplied'])


class SpeechTests(unittest.TestCase):
    def speak(self, body, verified=('hi',)):
        def supports(code, direction):
            return 'verified' if (code in verified and direction == 'speak') else 'unmeasured'

        with patch.object(languages, 'supports', supports), \
             patch.object(speech, 'speak', return_value=(b'RIFFaudio', {'codec': 'wav', 'model': 'bulbul:v3',
                                                                        'bytes': 9, 'elapsed_s': 1.0})):
            return workspace().speak(body)

    def test_a_verified_language_is_spoken(self):
        packet = self.speak({'text': 'Rainfall of 35 mm is forecast.', 'language': 'hi'})
        self.assertEqual(packet['language'], 'hi')
        self.assertEqual(packet['segment_count'], 1)
        self.assertTrue(packet['segments'][0])

    def test_a_language_this_project_has_not_verified_is_refused(self):
        with self.assertRaises(ValueError) as raised:
            self.speak({'text': 'Rainfall of 35 mm is forecast.', 'language': 'ta'})
        self.assertIn('not been verified', str(raised.exception))

    def test_spoken_audio_adds_no_claim_of_its_own(self):
        packet = self.speak({'text': 'Rainfall of 35 mm is forecast.', 'language': 'hi'})
        self.assertFalse(packet['is_evidence'])
        self.assertIn('adds no new claim', packet['note'])

    def test_long_text_is_split_into_segments_rather_than_cut(self):
        # Longer than the service's single-request limit, so it must be segmented rather
        # than refused: a long answer with its caveats is exactly what a listener needs.
        long_text = ' '.join(['Rainfall of 35 mm is forecast for this district.'] * 70)
        self.assertGreater(len(long_text), speech.TTS_CHARACTER_LIMIT)
        packet = self.speak({'text': long_text, 'language': 'hi'})
        self.assertGreater(packet['segment_count'], 1)

    def test_the_workspace_speaks_more_than_one_service_request_holds(self):
        self.assertGreater(Workspace.MAX_SPEAK_CHARACTERS, speech.TTS_CHARACTER_LIMIT,
                           'A cap below the service limit would make segmenting unreachable.')

    def test_text_beyond_the_workspace_limit_is_refused(self):
        with self.assertRaises(ValueError):
            self.speak({'text': 'x' * (Workspace.MAX_SPEAK_CHARACTERS + 1), 'language': 'hi'})

    def test_empty_text_or_a_missing_language_is_refused(self):
        for body in ({'text': '', 'language': 'hi'}, {'text': 'hello', 'language': 'zz'},
                     {'text': 'hello', 'language': ''}):
            with self.assertRaises(ValueError):
                self.speak(body)

    def test_an_unexpected_field_is_refused(self):
        with self.assertRaises(ValueError):
            self.speak({'text': 'hello', 'language': 'hi', 'speaker': 'anushka'})


class ChunkingTests(unittest.TestCase):
    def test_a_value_is_never_split_from_its_unit(self):
        text = 'Rainfall of 35 mm is forecast. Wind reaches 24 km/h later. Humidity holds near 80 %.'
        for piece in speech.chunks(text, 45):
            self.assertFalse(piece.strip().endswith('35'), piece)
            self.assertFalse(piece.strip().endswith('24'), piece)

    def test_short_text_is_one_segment(self):
        self.assertEqual(speech.chunks('Rain tomorrow.', 100), ['Rain tomorrow.'])

    def test_a_clause_with_no_safe_split_point_is_reported_not_cut(self):
        from weathergpt_data.transport import SourceError
        with self.assertRaises(SourceError):
            speech.chunks('word ' * 200, 40)

    def test_nothing_to_speak_is_an_empty_list_not_an_error(self):
        self.assertEqual(speech.chunks('', 100), [])


class TranslationModelTests(unittest.TestCase):
    """The default translation model refuses a language; the service names the wider one."""

    def test_a_refused_language_is_retried_on_the_model_the_service_names(self):
        import json
        calls = []

        def request(path, data, headers, deadline=speech.TIMEOUT):
            body = json.loads(data)
            calls.append(body)
            if 'model' not in body:
                raise speech.LanguageServiceUnavailable(
                    "The language service refused the request (HTTP 400): {\"error\":{\"message\":"
                    "\"Language 'ta-IN' is not supported in mayura:v1. Please switch to sarvam-translate:v1\"}}")
            return {'translated_text': 'சோதனை', 'source_language_code': 'en-IN', 'request_id': 'r1'}, 0.2

        with patch.object(speech, '_request', request):
            text, meta = speech.translate('Rainfall of 35 mm is forecast.', 'ta')
        self.assertEqual(text, 'சோதனை')
        self.assertIsNone(calls[0].get('model'))
        self.assertEqual(calls[1]['model'], speech.WIDER_TRANSLATE_MODEL)
        self.assertEqual(meta['model'], speech.WIDER_TRANSLATE_MODEL)
        self.assertEqual(meta['model_selection'], 'wider_model_named_by_service_refusal')
        self.assertFalse(meta['is_evidence'])

    def test_a_refusal_that_does_not_name_the_model_is_not_retried(self):
        import json
        calls = []

        def request(path, data, headers, deadline=speech.TIMEOUT):
            calls.append(json.loads(data))
            raise speech.LanguageServiceUnavailable('The language service refused the request (HTTP 401): bad key')

        with patch.object(speech, '_request', request):
            with self.assertRaises(speech.LanguageServiceUnavailable):
                speech.translate('Rainfall of 35 mm is forecast.', 'ta')
        self.assertEqual(len(calls), 1)

    def test_the_default_model_is_recorded_as_the_provider_default(self):
        with patch.object(speech, '_request',
                          lambda *a, **k: ({'translated_text': 'अनुवाद', 'request_id': 'r2'}, 0.1)):
            _, meta = speech.translate('Rainfall of 35 mm is forecast.', 'hi')
        self.assertEqual(meta['model'], 'provider_default')
        self.assertEqual(meta['model_selection'], 'provider_default')


class LanguageViewTests(unittest.TestCase):
    def test_the_interface_is_told_measured_support_not_the_documented_claim(self):
        view = workspace().languages()
        self.assertIn('languages', view)
        for row in view['languages']:
            self.assertIn('declared', row)
            self.assertIn('measured', row)
        self.assertIn('unmeasured, not as available', view['note'])

    def test_whether_a_key_is_configured_is_reported_without_revealing_it(self):
        view = workspace().languages()
        self.assertIsInstance(view['service_configured'], bool)
        self.assertNotIn('key', json_keys(view))


def json_keys(value, found=None):
    found = found if found is not None else set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            json_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            json_keys(item, found)
    return found


if __name__ == '__main__':
    unittest.main()
