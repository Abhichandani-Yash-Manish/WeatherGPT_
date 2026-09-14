"""Language rendering: value protection, the translation gate, and per-direction support.

These run offline against a stub translator. They measure nothing about any
translation service and prove nothing about translation quality. What they hold is
narrower and more important: a value that reaches the reader is the same characters
the evidence produced, a sentence that states a limit or a negation is never handed
to a translation model, and a render that loses a value is refused rather than shown.

The failure these exist to prevent was measured, not imagined: a probe rewrote
`35 mm` as `35 मि.मी.` and a speech round trip turned `35` into `पैंतीस`.
"""
import unittest

from weathergpt_data import languages, rendering
from weathergpt_data.transport import SourceError

ANSWER = ('Rainfall of 35 mm is forecast for Ahmedabad, Gujarat between 09:30 and 12:30 IST '
          'on 2026-09-16. The answering grid cell is 11.243 km from the requested point. '
          'Source S21 was read at 2026-09-15T01:40:00+00:00. '
          'No warning is in force for this district, and this is not an all-clear.')


def echo(text, target, source):
    """A translator that returns the masked text untouched."""
    return text


def reordering(text, target, source):
    """Sentinels are reordered by real translation; that must remain acceptable."""
    parts = rendering.SENTINEL_PATTERN.findall(text)
    return ' '.join(['अनुवाद'] + [rendering.SENTINEL % int(p) for p in reversed(parts)])


class ProtectionTests(unittest.TestCase):
    def captured(self, text, extra=()):
        _, tokens = rendering.protect(text, extra)
        return [token['original'] for token in tokens.values()]

    def test_a_value_and_its_unit_are_protected_together(self):
        self.assertIn('35 mm', self.captured('Rainfall of 35 mm is forecast'))
        self.assertIn('11.243 km', self.captured('The cell is 11.243 km away'))
        self.assertIn('34.0 °C', self.captured('Maximum 34.0 °C tomorrow'))
        self.assertIn('10.56–11.19 m³/s', self.captured('Discharge of 10.56–11.19 m³/s'))

    def test_a_day_and_month_without_a_year_is_protected(self):
        # Found live: the project writes forecast windows as "16 Sep". Unprotected, the
        # day survived as a bare number and the month was translated away, so a reader
        # saw "16" with no month at all.
        captured = self.captured('Ahmedabad · 16 Sep, 06:30–16 Sep, 12:30 IST')
        self.assertEqual(captured.count('16 Sep'), 2)
        self.assertNotIn('16', captured)

    def test_model_and_authority_names_keep_their_identity(self):
        # Found live: GFS was transliterated to जी.एफ.एस., which no longer names the model
        # a value came from.
        for name in ('GFS', 'ECMWF', 'ERA5', 'METAR', 'IMD', 'GloFAS'):
            self.assertIn(name, self.captured('Source: ' + name + ' forecast'), name)

    def test_a_whole_forecast_line_restores_exactly(self):
        line = ('Ahmedabad · 16 Sep, 06:30–16 Sep, 12:30 IST: Forecast precipitation: 0.1 mm. '
                'Source: GFS forecast; conditions can change.')
        masked, tokens = rendering.protect(line, ('Ahmedabad',))
        self.assertEqual(rendering.restore(masked, tokens), line)
        self.assertNotIn('Ahmedabad', masked)
        self.assertNotIn('GFS', masked)

    def test_a_date_is_never_split_into_bare_numbers(self):
        captured = self.captured('Issued on 2026-09-16 at 11:30 IST')
        self.assertIn('2026-09-16', captured)
        self.assertIn('11:30 IST', captured)
        self.assertNotIn('2026', captured)
        self.assertNotIn('09', captured)

    def test_a_timestamp_does_not_swallow_the_sentence_end(self):
        masked, tokens = rendering.protect('Read at 2026-09-15T01:40:00+00:00. No warning.')
        self.assertIn('2026-09-15T01:40:00+00:00', [t['original'] for t in tokens.values()])
        self.assertTrue(masked.rstrip().endswith('No warning.'))
        self.assertEqual(len(rendering.split_sentences(masked)), 2)

    def test_identifiers_links_and_saved_documents_are_protected(self):
        captured = self.captured('Source S21 and S57, see /api/documents/' + 'a' * 64)
        self.assertIn('S21', captured)
        self.assertIn('S57', captured)
        self.assertTrue(any(value.startswith('/api/documents/') for value in captured))

    def test_supplied_identities_are_protected(self):
        captured = self.captured('Rain over Ahmedabad in Gujarat', ('Ahmedabad', 'Gujarat'))
        self.assertIn('Ahmedabad', captured)
        self.assertIn('Gujarat', captured)

    def test_every_protected_value_restores_to_the_original_characters(self):
        masked, tokens = rendering.protect(ANSWER, ('Ahmedabad', 'Gujarat'))
        self.assertEqual(rendering.restore(masked, tokens), ANSWER)

    def test_restoring_an_unknown_placeholder_is_refused(self):
        with self.assertRaises(SourceError):
            rendering.restore('value #V9# here', {})


class GateTests(unittest.TestCase):
    def tokens(self, text=ANSWER):
        return rendering.protect(text, ('Ahmedabad', 'Gujarat'))

    def test_an_untouched_rendering_passes(self):
        masked, tokens = self.tokens()
        self.assertTrue(rendering.verify(masked, tokens)['ok'])

    def test_a_dropped_value_fails_and_names_what_was_lost(self):
        masked, tokens = self.tokens()
        report = rendering.verify(masked.replace('#V1#', ''), tokens)
        self.assertFalse(report['ok'])
        self.assertEqual(report['missing'][0]['original'], '35 mm')

    def test_a_duplicated_value_fails(self):
        masked, tokens = self.tokens()
        report = rendering.verify(masked + ' #V1#', tokens)
        self.assertFalse(report['ok'])
        self.assertEqual(report['duplicated'][0]['times'], 2)

    def test_an_invented_placeholder_fails(self):
        masked, tokens = self.tokens()
        report = rendering.verify(masked + ' #V99#', tokens)
        self.assertFalse(report['ok'])
        self.assertEqual(report['unknown_placeholders'], ['#V99#'])

    def test_reordering_is_accepted_because_it_is_correct_grammar(self):
        masked, tokens = self.tokens('Rainfall of 35 mm is forecast for tomorrow.')
        self.assertTrue(rendering.verify(reordering(masked, 'hi', 'en-IN'), tokens)['ok'])


class SafetyClauseTests(unittest.TestCase):
    def test_a_negation_or_limit_is_recognised(self):
        for sentence in ('No warning is in force.',
                         'This is not an all-clear.',
                         'Colour not supplied for this day.',
                         'This workspace does not issue warnings.',
                         'An observation is not a forecast.',
                         'No verified sea cell lies near this place.'):
            self.assertTrue(rendering.safety_critical(sentence), sentence)

    def test_an_ordinary_statement_is_not_held(self):
        for sentence in ('Rainfall of 35 mm is forecast for tomorrow.',
                         'The bulletin was issued on 2026-09-14.'):
            self.assertFalse(rendering.safety_critical(sentence), sentence)

    def test_a_safety_clause_is_never_handed_to_the_translator(self):
        seen = []

        def spy(text, target, source):
            seen.append(text)
            return text

        _, report = rendering.render(ANSWER, 'hi', spy, identities=('Ahmedabad', 'Gujarat'))
        self.assertEqual(report['held_safety_critical'], 1)
        self.assertTrue(all('all-clear' not in text for text in seen),
                        'The clause stating this is not an all-clear reached the translation model.')

    def test_a_held_clause_survives_verbatim_in_the_rendering(self):
        text, report = rendering.render(ANSWER, 'hi', echo, identities=('Ahmedabad', 'Gujarat'))
        self.assertIn('No warning is in force for this district, and this is not an all-clear.', text)
        self.assertEqual(report['held_sentences'], [report['held_sentences'][0]])


class RenderTests(unittest.TestCase):
    def test_values_survive_a_reordering_translation(self):
        text, report = rendering.render(ANSWER, 'hi', reordering, identities=('Ahmedabad', 'Gujarat'))
        self.assertTrue(report['ok'])
        self.assertEqual(report['failed'], 0)
        for value in ('35 mm', '11.243 km', 'S21', '2026-09-16', 'Ahmedabad'):
            self.assertIn(value, text, value + ' did not survive the rendering')

    def test_a_translation_that_loses_a_value_is_refused_and_the_source_kept(self):
        def lossy(text, target, source):
            return rendering.SENTINEL_PATTERN.sub('', text)

        text, report = rendering.render(ANSWER, 'hi', lossy, identities=('Ahmedabad', 'Gujarat'))
        self.assertFalse(report['ok'])
        self.assertGreater(report['failed'], 0)
        self.assertIn('35 mm', text, 'The source sentence must be kept when its values are lost.')
        self.assertEqual(report['failures'][0]['reason'], 'protected values did not survive')

    def test_a_translator_failure_keeps_the_source_sentence(self):
        def broken(text, target, source):
            raise SourceError('the language service could not be reached')

        text, report = rendering.render(ANSWER, 'hi', broken)
        self.assertFalse(report['ok'])
        self.assertIn('Rainfall of 35 mm', text)
        self.assertIn('could not be reached', report['failures'][0]['reason'])

    def test_a_sentence_of_only_values_is_not_translated_at_all(self):
        seen = []
        rendering.render('35 mm. No warning.', 'hi', lambda t, l, s: seen.append(t) or t)
        self.assertEqual(seen, [], 'A sentence with no prose has nothing to translate.')

    def test_an_unsupported_language_is_refused(self):
        with self.assertRaises(SourceError):
            rendering.render(ANSWER, 'zz', echo)

    def test_the_report_states_that_values_were_withheld_rather_than_checked(self):
        _, report = rendering.render(ANSWER, 'hi', echo)
        self.assertTrue(report['values_are_original_characters'])
        self.assertIn('withheld from translation', report['note'])


class LanguageRegistryTests(unittest.TestCase):
    def test_codes_are_accepted_in_the_forms_the_interface_uses(self):
        self.assertEqual(languages.normalise('hi-IN'), 'hi')
        self.assertEqual(languages.normalise('HI'), 'hi')
        self.assertEqual(languages.normalise('  gu  '), 'gu')
        self.assertIsNone(languages.normalise('zz'))
        self.assertIsNone(languages.normalise(None))

    def test_a_romanised_code_is_not_treated_as_an_indian_script(self):
        self.assertEqual(languages.normalise('hi-Latn'), 'hi-latn')
        self.assertIsNone(languages.script_pattern('hi-Latn'))
        self.assertFalse(languages.written_in('kal barish hogi', 'hi-Latn'))
        with self.assertRaises(SourceError):
            languages.sarvam_code('hi-Latn')

    def test_writing_is_checked_against_the_language_s_own_script(self):
        hindi = 'अहमदाबाद में कल वर्षा होने का पूर्वानुमान है'
        self.assertTrue(languages.written_in(hindi, 'hi'))
        self.assertFalse(languages.written_in(hindi, 'ta'))
        self.assertFalse(languages.written_in('Rain is expected tomorrow in Ahmedabad', 'hi'))

    def test_english_cannot_be_script_checked_and_says_so(self):
        self.assertIsNone(languages.script_pattern('en'))
        self.assertFalse(languages.written_in('Rain is expected', 'en'))

    def test_indian_numerals_compare_as_numbers(self):
        self.assertEqual(languages.latin_digits('३५ मिमी'), '35 मिमी')
        self.assertEqual(languages.latin_digits('૫૦'), '50')

    def test_declared_support_is_never_reported_as_measured(self):
        for code in ('hi', 'gu', 'ta'):
            self.assertTrue(languages.LANGUAGES[code]['declared']['speak'])
            self.assertIn(languages.supports(code, 'speak'), {'verified', 'failed', 'unmeasured'})

    def test_every_language_carries_both_claims_separately(self):
        for row in languages.catalogue():
            self.assertIn('declared', row)
            self.assertIn('measured', row)
            for direction in ('hear', 'write', 'speak'):
                self.assertIn(row['measured'][direction], {'verified', 'failed', 'unmeasured'})

    def test_a_direction_must_be_named(self):
        with self.assertRaises(SourceError):
            languages.supports('hi', 'translate')


if __name__ == '__main__':
    unittest.main()
