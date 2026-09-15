"""The alert brief: one place, one day, and only what the product published.

These are component checks over synthetic views. They take no measurement of any publisher.
What they pin is the discipline: the brief carries the bulletin identity and the retrieval
instant, states the day's status in the product's own terms, reports the CAP relay separately,
keeps a non-empty "not established" list, never becomes an all-clear or advice, and carries a
content hash so a saved brief can be identified.
"""
import json
import unittest

from weathergpt_data.alert_brief import compose, markdown, status_line


def day(number, colour='yellow', hazards=('Thunderstorm/lightning/squall',), quiet=False, wording=''):
    return {'day': number, 'label': '1%d Sep 2026' % number, 'date_local': '2026-09-1%d' % number,
            'colour': colour, 'colour_code': 3 if colour == 'yellow' else 4, 'hazards': list(hazards),
            'quiet': quiet, 'source_text': wording, 'starts_utc': '2026-09-1%dT18:30:00+00:00' % number,
            'ends_utc': '2026-09-1%dT18:30:00+00:00' % (number + 1)}


def view(days=None, district='PATNA', state='BIHAR'):
    return {'schema_version': 'product-view-v1', 'view': 'warnings.place', 'status': 'ok',
            'generated_at_utc': '2026-09-15T04:11:36+00:00',
            'data': {'district': district, 'state': state, 'issued_at_utc': '2026-09-15T00:00:00+00:00',
                     'day_boundary_basis': 'Day n is the nth IST calendar day counted from the bulletin date.',
                     'temporal_applicability': 'derived', 'source_locator': '$.features[605]',
                     'days': days if days is not None else [day(1), day(2)]},
            'sources': [{'source_id': 'S63', 'product': 'IMD district warning product', 'layer': 'imd:district_warnings_india',
                         'retrieved_at_utc': '2026-09-15T04:11:36+00:00'}],
            'limitations': ['Day windows are derived from the bulletin date.'],
            'not_established': ['This is district-level warning guidance, not a flood warning and not an all-clear.']}


def relay(messages=9, eligible=0):
    return {'data': {'messages': messages, 'eligible_by_lifecycle': eligible, 'latest_sent': '2026-09-09T12:54:34+05:30'},
            'sources': [{'source_id': 'S06', 'product': 'CAP relay'}]}


class CompositionTests(unittest.TestCase):
    def test_a_warning_day_carries_its_issuer_status_and_limits(self):
        brief = compose(view(), relay(), day_number=2)
        self.assertEqual(brief['status'], 'ok')
        self.assertEqual(brief['place'], {'district': 'PATNA', 'state': 'BIHAR'})
        self.assertEqual(brief['day']['day'], 2)
        self.assertIn('yellow', brief['status_line'])
        self.assertIn('Thunderstorm', brief['status_line'])
        self.assertEqual(brief['day_status']['hazards'], ['Thunderstorm/lightning/squall'])
        self.assertEqual(brief['issuer']['source_id'], 'S63')
        self.assertEqual(brief['issuer']['issued_at_utc'], '2026-09-15T00:00:00+00:00')
        self.assertEqual(brief['issuer']['retrieved_at_utc'], '2026-09-15T04:11:36+00:00')
        self.assertEqual(brief['relay']['messages'], 9)
        self.assertTrue(brief['not_established'])
        self.assertTrue(brief['what_would_change_this'])
        self.assertTrue(brief['brief_id'])

    def test_a_quiet_day_says_so_without_becoming_an_all_clear(self):
        quiet = day(5, colour='green', hazards=('No warning in this product',), quiet=True)
        brief = compose(view(days=[quiet]), relay(), day_number=5)
        self.assertEqual(brief['status'], 'ok')
        self.assertIn('No warning in this product', brief['status_line'])
        text = markdown(brief)
        self.assertIn('not an all-clear', text)
        self.assertIn('No warning in this product for this district-day', text)
        self.assertNotIn('safe', text.lower())

    def test_a_point_outside_every_district_is_refused_with_its_reason(self):
        brief = compose({'data': {'days': []}, 'generated_at_utc': '2026-09-15T04:00:00+00:00'}, relay())
        self.assertEqual(brief['status'], 'unavailable')
        self.assertIn('does not fall inside any district', brief['why'])
        self.assertIn('none was substituted', brief['why'])
        text = markdown(brief)
        self.assertIn('# Alert brief: not available', text)
        self.assertIn('not an all-clear', text)

    def test_a_day_the_product_does_not_publish_is_refused_and_the_days_are_named(self):
        brief = compose(view(), relay(), day_number=9)
        self.assertEqual(brief['status'], 'unavailable')
        self.assertIn('no day 9', brief['why'])
        self.assertEqual(brief['available_days'], [1, 2])

    def test_the_wording_note_is_used_when_the_product_publishes_no_free_text(self):
        brief = compose(view(), relay(), day_number=1)
        self.assertIsNone(brief['day_status']['official_wording'])
        self.assertIn('no free-text wording is recorded', brief['day_status']['wording_note'])
        self.assertIn('no free-text wording is recorded', markdown(brief))

    def test_the_brief_is_stable_and_identifiable(self):
        first = compose(view(), relay(), day_number=2)
        second = compose(view(), relay(), day_number=2)
        self.assertEqual(first['brief_id'], second['brief_id'], 'the same evidence gives the same brief identity')
        changed = compose(view(days=[day(1), day(2, hazards=('Heat wave',))]), relay(), day_number=2)
        self.assertNotEqual(first['brief_id'], changed['brief_id'])

    def test_no_advice_or_clearance_language_appears(self):
        text = markdown(compose(view(), relay(), day_number=2)).lower()
        for forbidden in ('you should', 'evacuate', 'safe to travel', 'all clear', 'all-clear: nothing', 'we advise'):
            self.assertNotIn(forbidden, text)
        self.assertIn('not a warning issued here', text)

    def test_status_line_reads_the_hazards_it_is_given(self):
        self.assertIn('orange', status_line(day(1, colour='orange', hazards=('Heavy rain',))).lower())
        self.assertIn('Heavy rain', status_line(day(1, colour='orange', hazards=('Heavy rain',))))
        self.assertIn('colour not supplied', status_line({'colour': None, 'hazards': ['Heavy rain']}))


if __name__ == '__main__':
    unittest.main()
