"""Plan Watch vocabulary, parsing and store.

A plan is built from what a person already said. These checks pin how the words become
slots: which statements are requests to be kept informed, which activity and hazards they
imply, how a weekday becomes a calendar date, how a part of day becomes the product's own
window, and that the store keeps notifications once per deduplication key.
"""
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from weathergpt_data import plans

# Tuesday 15 September 2026, 10:00 IST.
NOW = datetime(2026, 9, 15, 4, 30, tzinfo=timezone.utc)


class IntentTests(unittest.TestCase):
    def test_requests_to_be_kept_informed_are_recognised(self):
        for text in ["I'm going to spray fertiliser on my cotton in Rajkot on Monday, let me know if anything changes.",
                     'Remind me about my wedding in Patna on Saturday',
                     'Notify me if a heavy rain warning is issued for Patna tomorrow',
                     'Keep an eye on my farm near Rajkot',
                     'Alert me when a thunderstorm warning comes for Surat']:
            self.assertTrue(plans.notify_intent(text), text)

    def test_ordinary_questions_are_not_plans(self):
        for text in ['Tell me if it will rain in Surat tomorrow?',
                     'Will it rain in Rajkot on Monday?',
                     'Is there an official flood warning for Patna right now?',
                     'What is the temperature in Delhi?']:
            self.assertFalse(plans.notify_intent(text), text)


class SlotTests(unittest.TestCase):
    def test_activity_and_label_come_from_the_persons_words(self):
        text = "I'm going to spray fertiliser on my cotton in Rajkot on Monday"
        self.assertEqual(plans.activity_of(text), 'spraying')
        self.assertEqual(plans.label_of(text), 'cotton')
        self.assertEqual(plans.activity_of('our wedding in Patna on Saturday'), 'outdoor_event')
        self.assertEqual(plans.label_of('our wedding in Patna on Saturday'), 'wedding')
        self.assertIsNone(plans.activity_of('keep me posted about Surat'))

    def test_activity_templates_name_official_categories_only(self):
        self.assertEqual(sorted(plans.ACTIVITIES['spraying']['codes']), [2, 4, 8, 16, 17])
        self.assertEqual(sorted(plans.ACTIVITIES['harvest']['codes']), [2, 4, 5, 16, 17])
        self.assertIn('not_connected', plans.ACTIVITIES['fishing'])
        for name, template in plans.ACTIVITIES.items():
            for code in template['codes']:
                self.assertIn(code, plans.HAZARDS, name)
                self.assertNotEqual(code, 1, name)

    def test_explicit_hazards_narrow_the_watch_and_unconnected_ones_are_named(self):
        self.assertEqual(plans.explicit_hazards('tell me if a heavy rain warning is issued'), ([2, 16, 17], None))
        self.assertEqual(plans.explicit_hazards('notify me about a heat wave'), ([9, 10, 11], None))
        self.assertEqual(plans.explicit_hazards('notify me if a flood warning is issued')[1], 'flood')
        self.assertEqual(plans.explicit_hazards('let me know if anything changes'), ([], None))

    def test_a_weekday_is_the_next_occurrence_and_prints_its_date(self):
        self.assertEqual(plans.parse_day('on Monday', NOW), {'kind': 'once', 'date': '2026-09-21', 'basis': 'monday'})
        self.assertEqual(plans.parse_day('on Tuesday', NOW)['date'], '2026-09-15')
        self.assertEqual(plans.parse_day('tomorrow', NOW)['date'], '2026-09-16')
        self.assertEqual(plans.parse_day('kal', NOW)['date'], '2026-09-16')
        self.assertEqual(plans.parse_day('on 21 Sep', NOW)['date'], '2026-09-21')
        self.assertEqual(plans.parse_day('on September 24', NOW)['date'], '2026-09-24')
        self.assertEqual(plans.parse_day('10 Sep', NOW)['kind'], 'past')
        self.assertEqual(plans.parse_day('keep an eye on my farm, always', NOW), {'kind': 'always'})
        self.assertIsNone(plans.parse_day('I will spray soon', NOW))

    def test_a_named_day_beats_a_standing_phrase(self):
        self.assertEqual(plans.parse_day('spraying on my farm on Monday', NOW)['kind'], 'once')

    def test_parts_of_day_use_the_products_own_windows(self):
        self.assertEqual(plans.parse_time('Morning')['start'], '09:30')
        self.assertEqual(plans.parse_time('in the afternoon')['end'], '18:30')
        self.assertEqual(plans.parse_time('all day')['label'], 'all day')
        four = plans.parse_time('after 4 pm')
        self.assertEqual((four['start'], four['end']), ('16:00', '19:00'))
        self.assertEqual(plans.parse_time('at 18:30')['start'], '18:30')
        self.assertIsNone(plans.parse_time('on Monday'))
        self.assertIsNone(plans.parse_time('on 21 Sep'))

    def test_windows_are_ist_and_a_whole_day_ends_the_next_morning(self):
        self.assertEqual(plans.window_of('2026-09-21', plans.parse_time('morning')),
                         ('2026-09-21T09:30:00+05:30', '2026-09-21T12:30:00+05:30'))
        self.assertEqual(plans.window_of('2026-09-21', plans.parse_time('all day')),
                         ('2026-09-21T00:30:00+05:30', '2026-09-22T00:30:00+05:30'))


class LabelTests(unittest.TestCase):
    def test_source_place_labels_are_made_readable(self):
        self.assertEqual(plans.plain_place_label('Rājkot, Rājkot, State of Gujarāt'), 'Rajkot, Gujarat')
        self.assertEqual(plans.plain_place_label('Patna, Patna, State of Bihār'), 'Patna, Bihar')
        self.assertEqual(plans.plain_place_label('New Delhi, New Delhi, National Capital Territory of Delhi'), 'New Delhi, Delhi')


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = plans.PlanStore(Path(self.tmp.name) / 'plans.sqlite')

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, **extra):
        fields = {'question': 'spray on Monday', 'label': 'cotton', 'activity': 'spraying',
                  'hazard_codes': [2, 4, 8, 16, 17], 'place': {'label': 'Rajkot, Gujarat', 'district_key': 'RAJKOT'},
                  'kind': 'once', 'date_local': '2026-09-21', 'window_start': '2026-09-21T09:30:00+05:30',
                  'window_end': '2026-09-21T12:30:00+05:30', 'part_label': 'morning', 'check_in': True,
                  'state': 'watching', 'inferred': {'activity': "from 'spray'"}, 'created_at': NOW.isoformat()}
        fields.update(extra)
        return self.store.create(fields)

    def test_a_plan_round_trips_updates_and_deletes(self):
        saved = self.plan()
        loaded = self.store.get(saved['id'])
        self.assertEqual(loaded['hazard_codes'], [2, 4, 8, 16, 17])
        self.assertEqual(loaded['place']['district_key'], 'RAJKOT')
        self.assertTrue(loaded['check_in'])
        self.store.update(saved['id'], state='paused', last_snapshot={'days': {}})
        self.assertEqual(self.store.get(saved['id'])['state'], 'paused')
        self.assertEqual(self.store.get(saved['id'])['last_snapshot'], {'days': {}})
        self.assertEqual(len(self.store.list()), 1)
        self.assertTrue(self.store.delete(saved['id']))
        self.assertFalse(self.store.delete(saved['id']))
        with self.assertRaises(ValueError):
            self.store.get(saved['id'])

    def test_a_notification_is_written_once_per_deduplication_key(self):
        saved = self.plan()
        first = self.store.add_notification(saved['id'], 'change', 'k1', 'Title', 'Text', {'district': 'RAJKOT'},
                                            NOW.isoformat(), NOW.isoformat())
        again = self.store.add_notification(saved['id'], 'change', 'k1', 'Title', 'Text', {}, NOW.isoformat(),
                                            NOW.isoformat())
        self.assertIsInstance(first, int)
        self.assertIsNone(again)
        rows = self.store.notifications()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['receipt'], {'district': 'RAJKOT'})

    def test_meta_values_round_trip(self):
        self.assertIsNone(self.store.meta_get('last_ok_at'))
        self.store.meta_set('last_ok_at', NOW.isoformat())
        self.assertEqual(self.store.meta_get('last_ok_at'), NOW.isoformat())


if __name__ == '__main__':
    unittest.main()
