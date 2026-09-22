"""The place a reader set for themselves, and what an answer may call it.

Measured 22 September 2026. With Ahmedabad held in the workspace, "are there any warnings in place for
my region?" was answered about ARWAL - a district in Bihar, 1,100 km away - because the held place was
never sent to the engine on an ordinary turn, so the model had nothing to resolve "my region" against
and the warning tool ran unconstrained. The place now travels with every question as `home`.

`home` is deliberately not `place`. `place` is the "Change the place" control: an instruction to answer
about somewhere, which overrides the question. `home` is context handed to the planner, which decides
whether the question is about it - so a question naming another place is unaffected.
"""
import unittest

from weathergpt_data.conversation import ConversationEngine


class Local:
    pass


class ReaderOwnPlaceTests(unittest.TestCase):
    """Whether an answer may say "your district" instead of naming the place."""

    def engine(self, home):
        engine = ConversationEngine.__new__(ConversationEngine)
        engine._local = Local()
        engine._local.reader_home = home
        return engine

    AHMEDABAD = {'label': 'Ahmedabad, Ahmadābād, State of Gujarāt', 'name': 'Ahmedabad',
                 'state': 'Gujarat', 'district': 'Ahmadābād'}

    def test_a_possessive_reference_to_the_readers_own_place_is_accepted(self):
        """They set it, it is on screen in the rail while they read, and the claim names it in full."""
        engine = self.engine(self.AHMEDABAD)
        self.assertTrue(engine._reader_own_place('Ahmedabad', 'No warning is in force for your district today.'))
        self.assertTrue(engine._reader_own_place('Ahmedabad', 'There is nothing published for your region.'))

    def test_a_place_that_is_not_the_readers_own_must_still_be_named(self):
        """The whole risk this guards is an answer about one place reading as another."""
        engine = self.engine(self.AHMEDABAD)
        self.assertFalse(engine._reader_own_place('Arwal', 'No warning is in force for your district today.'))
        self.assertFalse(engine._reader_own_place('Mumbai', 'Rain is expected in your area.'))

    def test_prose_that_points_at_nothing_is_still_refused(self):
        """Both halves are required: the reader's own place AND a possessive reference to it."""
        engine = self.engine(self.AHMEDABAD)
        self.assertFalse(engine._reader_own_place('Ahmedabad', 'No warning is in force today.'))
        self.assertFalse(engine._reader_own_place('Ahmedabad', 'The district carries no warning.'))

    def test_nothing_is_relaxed_when_the_reader_has_set_no_place(self):
        engine = self.engine(None)
        self.assertFalse(engine._reader_own_place('Ahmedabad', 'No warning is in force for your district.'))

    def test_the_district_spelling_counts_as_the_same_place(self):
        """The fact's place is the district's own spelling, which is not always the settlement's."""
        engine = self.engine(self.AHMEDABAD)
        self.assertTrue(engine._reader_own_place('Ahmadābād', 'Nothing is published for your district today.'))

    def test_the_warning_products_own_spelling_is_the_same_place(self):
        """Measured: the fact carries "AHMADABAD" as the IMD product prints it, while the held place
        carries the catalogue's "Ahmadābād". Compared without folding, those are two different places -
        which is exactly why this allowance did nothing on its first run against the live engine."""
        engine = self.engine(self.AHMEDABAD)
        self.assertTrue(engine._reader_own_place('AHMADABAD', 'No warning is in force for your district today.'))


if __name__ == '__main__':
    unittest.main()


class PlaceNamingTests(unittest.TestCase):
    """Which spellings of a place count as naming it.

    Measured 22 September 2026. The IMD district product spells the district AHMADABAD. Asked about
    warnings, the model wrote "No - for Ahmedabad, the IMD district warning colour is ...", naming the
    place three times. The check compared "ahmadabad" against prose containing "ahmedabad", found one
    vowel different, discarded the answer and printed the tool floor instead. That was never specific to
    warnings: any place whose published spelling differs from the one people write loses its answer the
    same way, which across Indian place names is constant.
    """

    def engine(self, home=None):
        engine = ConversationEngine.__new__(ConversationEngine)
        engine._local = Local()
        engine._local.reader_home = home
        return engine

    def result(self, place, **extra):
        return {'facts': [{'place': place}], **extra}

    def test_the_product_spelling_alone_does_not_match_another_spelling(self):
        """And it must not. AHMADABAD and Ahmedabad differ by one vowel; so do plenty of genuinely
        different places, and a matcher loose enough to join these two would join those as well."""
        engine = self.engine()
        prose = 'No — for Ahmedabad, the IMD district warning colour is "No warning in this product".'
        self.assertFalse(engine._names_the_place('AHMADABAD', prose, self.result('AHMADABAD')))

    def test_the_turn_knows_both_spellings_because_the_reader_supplied_one(self):
        """This is how the live case actually passes, and it is the honest mechanism rather than a
        fuzzy match: the fact carries the product's AHMADABAD, and the place the reader set carries
        'Ahmedabad, Ahmadābād, State of Gujarāt'. The turn therefore knows the place by both names, and
        the model naming either one has named the place."""
        engine = self.engine({'label': 'Ahmedabad, Ahmadābād, State of Gujarāt', 'name': 'Ahmedabad',
                              'state': 'Gujarat', 'district': 'Ahmadābād'})
        prose = 'No — for Ahmedabad, the IMD district warning colour is "No warning in this product".'
        self.assertTrue(engine._names_the_place('AHMADABAD', prose, self.result('AHMADABAD')))

    def test_a_bare_plan_name_does_not_vouch_for_a_different_spelling(self):
        """A plan place is just a string the reader typed. On its own it cannot establish that
        'Ahmedabad' and 'AHMADABAD' are one place - only a label carrying BOTH can, which is why the
        link is the reader's held place or a resolved point rather than any name in the turn."""
        engine = self.engine()
        result = self.result('AHMADABAD', plan={'places': [{'name': 'Ahmedabad'}]})
        self.assertFalse(engine._names_the_place('AHMADABAD', 'Rain is likely in Ahmedabad tonight.', result))

    def test_a_resolved_point_carrying_both_spellings_does_vouch(self):
        """The resolved point is the catalogue's own row, and it carries the full label - which is
        where the two spellings are recorded as one place."""
        engine = self.engine()
        result = self.result('AHMADABAD', resolved_points={
            'Ahmedabad': {'label': 'Ahmedabad, Ahmadābād, State of Gujarāt'}})
        self.assertTrue(engine._names_the_place('AHMADABAD', 'Rain is likely in Ahmedabad tonight.', result))

    def test_a_different_place_is_still_refused(self):
        """The rule this guards: an answer about one place must not read as another."""
        engine = self.engine()
        self.assertFalse(engine._names_the_place('AHMADABAD', 'Rain is likely in Mumbai tonight.', self.result('AHMADABAD')))
        self.assertFalse(engine._names_the_place('AHMADABAD', 'Rain is likely tonight.', self.result('AHMADABAD')))

    def test_a_place_name_too_short_to_be_one_does_not_refuse_every_answer(self):
        """Fragments under three characters are dropped so a stray 'st' or 'of' cannot pass a draft by
        accident. When that leaves nothing to check at all, the answer is not refused: a degenerate
        place name is a data problem, and refusing every sentence written about it reports the wrong
        fault to the reader."""
        engine = self.engine()
        self.assertTrue(engine._names_the_place('Of', 'It is of no concern.', self.result('Of')))

    def test_a_stray_fragment_does_not_let_a_wrong_place_through(self):
        engine = self.engine()
        self.assertFalse(engine._names_the_place('Ahmedabad', 'Rain is likely in Delhi tonight.',
                                                 self.result('Ahmedabad')))
