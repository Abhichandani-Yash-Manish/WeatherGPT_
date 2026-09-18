"""The column covering today, kept apart from the five-day tally.

Offline component checks over synthetic rows. They pin one distinction the surfaces depend on and
which the live read makes easy to get wrong: `tally` spans every non-quiet day in the table, including
days already past, so it cannot answer "what does today look like". Measured against this machine's
national read on 18 September 2026, `tally` carried one red and 26 orange district-days while every
one of those days was in the past and the column covering today held only green and yellow. A front
door that printed the red from `tally` would be announcing a hazard that is over.

These are not acceptance of the warning product or of any district's edition.
"""
import unittest

from weathergpt_data.product_api import today_tally


def day(colour, is_today=False, is_past=False, quiet=False):
    return {'colour': colour, 'is_today': is_today, 'is_past': is_past, 'quiet': quiet}


def row(days, district='TEST'):
    return {'district': district, 'days': days}


class TodayTallyTests(unittest.TestCase):
    def test_counts_only_the_day_covering_today(self):
        rows = [
            row([day('red', is_past=True), day('yellow', is_today=True), day('green')]),
            row([day('orange', is_past=True), day('green', is_today=True), day('green')]),
        ]
        result = today_tally(rows)
        self.assertEqual(result['counts'], {'yellow': 1, 'green': 1})
        self.assertNotIn('red', result['counts'])
        self.assertNotIn('orange', result['counts'])

    def test_a_quiet_day_still_publishes_its_colour(self):
        """The five-day tally drops a quiet day; today's column may not. A quiet green is the source
        saying green for today, and a reader asking about today is entitled to that answer."""
        rows = [row([day('green', is_today=True, quiet=True)])]
        self.assertEqual(today_tally(rows)['counts'], {'green': 1})

    def test_a_district_with_no_day_covering_today_is_counted_not_dropped(self):
        rows = [
            row([day('yellow', is_today=True)]),
            row([day('yellow', is_past=True), day('green')], district='STALE'),
        ]
        result = today_tally(rows)
        self.assertEqual(result['counts'], {'yellow': 1})
        self.assertEqual(result['districts_with_no_day_covering_today'], 1)

    def test_a_day_with_no_colour_is_unset_rather_than_absent(self):
        rows = [row([day(None, is_today=True)])]
        self.assertEqual(today_tally(rows)['counts'], {'unset': 1})

    def test_no_rows_is_an_empty_reading_not_an_error(self):
        self.assertEqual(today_tally([]), {'counts': {}, 'districts_with_no_day_covering_today': 0})


if __name__ == '__main__':
    unittest.main()
