"""The rendering gate: quotations held, sentences independent, repeats cached.

Measured 15 September 2026 on a Gujarati district question: the answer took 27.4 s, of which
about 22 s was sentence-by-sentence translation of a composed answer that was mostly quoted
passages. Three changes later it is 11.2 s cold and 1.2 s for the same question again.

Nothing here measures translation quality. What it pins is that a quotation is never translated,
that independent sentences render in the order the answer wrote them, that a repeated sentence is
served from the local cache rather than the service, and that a transient service failure is tried
once more while a damaged value is never retried.
"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from weathergpt_data import rendering, speech  # noqa: E402


class FakeTranslator:
    """A translator that answers in Devanagari and records what it was asked to render.

    It returns the protected-value sentinels it was given, because the gate requires every value
    to come back exactly once, and a rendering in another script is refused by design.
    """

    def __init__(self, answer='यह एक अनुवादित वाक्य है जो हिंदी में लिखा गया है'):
        self.calls = []
        self.answer = answer

    def __call__(self, text, target, source='en-IN'):
        self.calls.append(text)
        sentinels = ' '.join(m.group(0) for m in rendering.SENTINEL_PATTERN.finditer(text))
        return (self.answer + ' ' + sentinels + ' और यह अनुवाद भी हिंदी में है').strip()


class QuotationTests(unittest.TestCase):
    def test_a_source_quotation_is_never_translated(self):
        answer = ('Indexed published document: the bulletin for Nashik. · page 3 · “Grapes limestone content ranges '
                  'from 3 percent to 22 percent.” These are original source excerpts.')
        translator = FakeTranslator()
        text, report = rendering.render(answer, 'hi', translator)
        self.assertEqual(report['held_quotations'], 1)
        self.assertIn('“Grapes limestone content ranges from 3 percent to 22 percent.”', text)
        self.assertTrue(all('Grapes limestone' not in call for call in translator.calls),
                        'the quotation must not reach the translator')
        self.assertEqual(report['ok'], True)

    def test_an_answer_that_is_only_a_quotation_keeps_the_previous_behaviour(self):
        answer = '· page 1 · “Grapes limestone content in the Nashik district vineyards.”'
        translator = FakeTranslator()
        text, report = rendering.render(answer, 'hi', translator)
        self.assertEqual(report['held_quotations'], 0)
        self.assertTrue(translator.calls, 'a quotation-only answer is rendered as before')


class OrderTests(unittest.TestCase):
    def test_sentences_are_rendered_in_the_order_the_answer_wrote_them(self):
        answer = 'First sentence about rain. Second sentence about wind. Third sentence about humidity.'
        translator = FakeTranslator()
        text, report = rendering.render(answer, 'hi', translator)
        self.assertEqual(report['ok'], True)
        # The pool preserves the order it was given, and the answer is rebuilt in that order.
        self.assertEqual(len(translator.calls), 3)
        self.assertIn('rain', translator.calls[0])
        self.assertIn('wind', translator.calls[1])
        self.assertIn('humidity', translator.calls[2])
        self.assertEqual(text.count('अनुवादित वाक्य'), 3, 'every sentence is rendered exactly once')


class RetryTests(unittest.TestCase):
    def test_a_transient_failure_is_tried_once_more(self):
        translator = FakeTranslator()
        calls = {'count': 0}
        original = translator.__call__

        def flaky(text, target, source='en-IN'):
            calls['count'] += 1
            if calls['count'] == 1:
                raise rendering.SourceError('the language service could not be reached')
            return original(text, target, source)

        text, report = rendering.render('Will it rain in Ahmedabad tomorrow?', 'hi', flaky)
        self.assertEqual(report['ok'], True)
        self.assertEqual(calls['count'], 2)

    def test_a_damaged_value_is_never_retried(self):
        answer = 'Rainfall of 35 mm was recorded in Ahmedabad.'
        calls = {'count': 0}

        def damaging(text, target, source='en-IN'):
            calls['count'] += 1
            return 'अनुवाद जो मान बदल देता है'

        text, report = rendering.render(answer, 'hi', damaging)
        self.assertEqual(report['ok'], False)
        self.assertEqual(calls['count'], 1, 'a value failure is a content failure, not a transient one')
        self.assertIn('35 mm', text)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_root = speech.CACHE_ROOT
        self.original_json_call = speech._json_call
        speech.CACHE_ROOT = Path(self.tmp.name)
        self.calls = []

        def stub(path, payload, deadline=None):
            self.calls.append(payload.get('input'))
            return {'translated_text': 'अनुवाद ' + str(payload.get('input'))}, 1.0

        speech._json_call = stub

    def tearDown(self):
        speech.CACHE_ROOT = self.original_root
        speech._json_call = self.original_json_call
        self.tmp.cleanup()

    def test_a_repeated_sentence_is_served_from_the_cache(self):
        first, meta = speech.translate('These are original source excerpts.', 'hi', 'en-IN', cache=True)
        self.assertEqual(meta.get('cache'), None)
        self.assertEqual(len(self.calls), 1)
        second, meta = speech.translate('These are original source excerpts.', 'hi', 'en-IN', cache=True)
        self.assertEqual(second, first)
        self.assertEqual(meta.get('cache'), 'hit')
        self.assertEqual(len(self.calls), 1, 'the second call must not reach the service')

    def test_the_cache_is_keyed_by_text_target_and_source(self):
        speech.translate('These are original source excerpts.', 'hi', 'en-IN', cache=True)
        speech.translate('These are original source excerpts.', 'gu', 'en-IN', cache=True)
        self.assertEqual(len(self.calls), 2, 'a different target language is a different rendering')

    def test_a_stored_entry_can_be_read_back_from_disk(self):
        speech.translate('Wind speeds are likely to increase along the coast.', 'hi', 'en-IN', cache=True)
        stored = list(Path(self.tmp.name).glob('*.json'))
        self.assertEqual(len(stored), 1)
        payload = json.loads(stored[0].read_text())
        self.assertTrue(payload['rendered'].startswith('अनुवाद'), 'the rendered text is stored')
        self.assertIn('created_at_utc', payload)

    def test_a_cache_miss_is_counted_separately_from_a_hit(self):
        before = speech.cache_hits()
        speech.translate('A sentence that was never rendered before.', 'hi', 'en-IN', cache=True)
        self.assertEqual(speech.cache_hits(), before)
        speech.translate('A sentence that was never rendered before.', 'hi', 'en-IN', cache=True)
        self.assertEqual(speech.cache_hits(), before + 1)


if __name__ == '__main__':
    unittest.main()
