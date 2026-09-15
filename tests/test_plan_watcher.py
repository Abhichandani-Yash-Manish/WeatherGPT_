"""Plan Watch watcher: what counts as a change, and what is never said.

Every edition here is a synthetic test fixture in the district warning attribute shape,
not recorded IMD output. The checks pin the rules from docs/63: a plan beyond the product's
five days waits; only the plan's watched categories count; the first reading is a baseline,
not an alert; an identical edition says nothing; a removal is not an all-clear; a missing
colour is never a level; a check-in is written once; a long read failure is reported once;
quiet hours hold what is not orange or red; not-connected and paused plans are not checked.
"""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weathergpt_data import plan_watcher as pw
from weathergpt_data.plans import PlanStore
from weathergpt_data.transport import SourceError

IST = timezone(timedelta(hours=5, minutes=30))


def ist(day, hour, minute=0):
    return datetime(2026, 9, day, hour, minute, tzinfo=IST).astimezone(timezone.utc)


def payload(days, bulletin='2026-09-15', colours=None, district='RAJKOT'):
    """A one-district attribute collection: days is five hazard-code lists."""
    colours = colours or [4 if codes == [1] else 3 for codes in days]
    properties = {'District': district, 'Obj_id': 1, 'Date': bulletin, 'UTC': 6, 'updated_at': bulletin + ' 11:30'}
    for index, codes in enumerate(days, start=1):
        properties['Day_%d' % index] = ','.join(str(code) for code in codes)
        properties['Day%d_Color' % index] = colours[index - 1]
    return {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': properties}]}


def edition(days, sha, **kwargs):
    return pw.rows_from_payload(payload(days, **kwargs), {'sha256': sha, 'retrieved_at_utc': '2026-09-15T06:10:00+00:00'})


QUIET = [[1], [1], [1], [1], [1]]


class Source:
    def __init__(self, *items):
        self.items = list(items)

    def read(self):
        item = self.items[0] if len(self.items) == 1 else self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class WatcherBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PlanStore(Path(self.tmp.name) / 'plans.sqlite')

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, date='2026-09-17', **extra):
        fields = {'question': 'spray cotton', 'label': 'cotton', 'activity': 'spraying', 'hazard_codes': [2, 4, 8, 16, 17],
                  'place': {'label': 'Rajkot, Gujarat', 'district_key': 'RAJKOT', 'district': 'RAJKOT'},
                  'kind': 'once', 'date_local': date, 'window_start': date + 'T09:30:00+05:30',
                  'window_end': date + 'T12:30:00+05:30', 'part_label': 'morning', 'check_in': True,
                  'state': 'watching', 'created_at': ist(15, 10).isoformat(), 'saved_at': ist(15, 10).isoformat()}
        fields.update(extra)
        return self.store.create(fields)


class SnapshotTests(WatcherBase):
    def test_a_plan_beyond_the_five_published_days_waits_for_coverage(self):
        snap = pw.snapshot(self.plan('2026-09-21'), edition(QUIET, 'a'), ist(15, 12))
        self.assertEqual(snap['coverage'], 'waiting')
        self.assertEqual(snap['available_from'], '2026-09-17')
        self.assertEqual(snap['days'], {})

    def test_only_the_watched_categories_of_the_plan_day_count(self):
        storm = edition([[1], [1], [4], [1], [1]], 'a')
        snap = pw.snapshot(self.plan(), storm, ist(15, 12))
        self.assertEqual(snap['coverage'], 'covered')
        entry = snap['days']['2026-09-17']
        self.assertEqual((entry['day'], entry['matched_codes'], entry['colour']), (3, [4], 'yellow'))
        fog = pw.snapshot(self.plan(), edition([[1], [1], [15], [1], [1]], 'b'), ist(15, 12))
        self.assertEqual(fog['days']['2026-09-17']['matched_codes'], [])

    def test_a_district_absent_from_the_edition_is_not_read_as_quiet(self):
        snap = pw.snapshot(self.plan(), edition(QUIET, 'a', district='SURAT'), ist(15, 12))
        self.assertEqual(snap['coverage'], 'no_district_row')


class ChangeTests(WatcherBase):
    def test_the_first_reading_is_a_baseline_and_a_real_change_is_written_once(self):
        plan = self.plan()
        snap = pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        self.assertEqual(snap['coverage'], 'covered')
        self.assertEqual(self.store.notifications(), [])
        storm = edition([[1], [1], [4], [1], [1]], 'b')
        pw.run_cycle(self.store, Source(storm), ist(15, 13))
        notes = self.store.notifications()
        self.assertEqual([note['kind'] for note in notes], ['change'])
        self.assertIn('no warning for your watched hazards', notes[0]['text'])
        self.assertIn('Thunderstorm', notes[0]['text'])
        self.assertIn('yellow', notes[0]['text'])
        self.assertIn('Thursday 17 Sep', notes[0]['text'])
        self.assertIn('cotton spraying', notes[0]['text'])
        self.assertEqual(notes[0]['receipt']['origin_authentication'], 'unverified')
        self.assertEqual(notes[0]['receipt']['hazard_codes'], [4])
        pw.run_cycle(self.store, Source(storm), ist(15, 13, 30))
        self.assertEqual(len(self.store.notifications()), 1)

    def test_a_removed_warning_is_reported_and_is_not_an_all_clear(self):
        plan = self.plan()
        pw.baseline(self.store, plan, Source(edition([[1], [1], [4], [1], [1]], 'a')), ist(15, 12))
        pw.run_cycle(self.store, Source(edition(QUIET, 'b')), ist(15, 13))
        notes = self.store.notifications()
        self.assertEqual(len(notes), 1)
        self.assertIn('not an all-clear', notes[0]['text'])

    def test_an_unrelated_category_changing_says_nothing(self):
        plan = self.plan()
        pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        pw.run_cycle(self.store, Source(edition([[1], [1], [15], [1], [1]], 'b')), ist(15, 13))
        self.assertEqual(self.store.notifications(), [])

    def test_a_missing_colour_is_never_a_level(self):
        plan = self.plan()
        pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        pw.run_cycle(self.store, Source(edition([[1], [1], [4], [1], [1]], 'b', colours=[4, 4, 0, 4, 4])), ist(15, 13))
        text = self.store.notifications()[0]['text']
        self.assertIn('colour not supplied', text)
        self.assertNotIn('yellow', text)

    def test_a_plan_entering_coverage_with_a_warning_is_reported(self):
        plan = self.plan('2026-09-21')
        pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        self.assertEqual(self.store.get(plan['id'])['state'], 'waiting_for_coverage')
        later = edition([[1], [1], [1], [1], [16]], 'b', bulletin='2026-09-17', colours=[4, 4, 4, 4, 2])
        pw.run_cycle(self.store, Source(later), ist(17, 12))
        notes = self.store.notifications()
        self.assertEqual(len(notes), 1)
        self.assertIn('orange', notes[0]['text'])
        self.assertEqual(self.store.get(plan['id'])['state'], 'watching')

    def test_a_standing_plan_watches_every_published_day(self):
        plan = self.plan(kind='always', date_local=None, window_start=None, window_end=None, check_in=False,
                         hazard_codes=list(range(2, 18)), activity='home', label='farm')
        pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        self.assertEqual(len(self.store.get(plan['id'])['last_snapshot']['days']), 5)
        pw.run_cycle(self.store, Source(edition([[1], [9], [1], [1], [1]], 'b')), ist(15, 13))
        notes = self.store.notifications()
        self.assertEqual(len(notes), 1)
        self.assertIn('Heat wave', notes[0]['text'])


class TimingTests(WatcherBase):
    def test_the_evening_before_check_in_is_written_once_and_not_before_19_ist(self):
        plan = self.plan()
        pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        pw.run_cycle(self.store, Source(edition(QUIET, 'a')), ist(16, 18, 30))
        self.assertEqual(self.store.notifications(), [])
        pw.run_cycle(self.store, Source(edition(QUIET, 'a')), ist(16, 19, 5))
        pw.run_cycle(self.store, Source(edition(QUIET, 'a')), ist(16, 19, 35))
        notes = self.store.notifications()
        self.assertEqual([note['kind'] for note in notes], ['check_in'])
        self.assertIn("Tomorrow's plan", notes[0]['text'])
        self.assertIn('not an all-clear', notes[0]['text'])

    def test_three_hours_without_a_good_read_is_reported_once_and_recovers(self):
        plan = self.plan()
        pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        failing = Source(SourceError('offline'))
        pw.run_cycle(self.store, failing, ist(15, 14))
        self.assertEqual(self.store.notifications(), [])
        pw.run_cycle(self.store, failing, ist(15, 15))
        pw.run_cycle(self.store, failing, ist(15, 15, 30))
        notes = self.store.notifications()
        self.assertEqual([note['kind'] for note in notes], ['degraded'])
        self.assertIn('is not being checked', notes[0]['text'])
        self.assertEqual(self.store.get(plan['id'])['state'], 'degraded')
        pw.run_cycle(self.store, Source(edition(QUIET, 'a')), ist(15, 16))
        self.assertEqual(self.store.get(plan['id'])['state'], 'watching')

    def test_quiet_hours_hold_a_yellow_change_and_release_an_orange_one(self):
        plan = self.plan()
        pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        pw.run_cycle(self.store, Source(edition([[1], [1], [4], [1], [1]], 'b')), ist(15, 23))
        held = self.store.notifications()[0]
        self.assertEqual(held['visible_at'], ist(16, 6).isoformat())
        other = self.plan()
        pw.baseline(self.store, other, Source(edition(QUIET, 'a')), ist(15, 12))
        pw.run_cycle(self.store, Source(edition([[1], [1], [16], [1], [1]], 'c', colours=[4, 4, 2, 4, 4])), ist(15, 23, 10))
        loud = [note for note in self.store.notifications() if note['plan_id'] == other['id']][0]
        self.assertEqual(loud['visible_at'], loud['created_at'])

    def test_plan_day_and_end_of_window_states(self):
        plan = self.plan()
        pw.baseline(self.store, plan, Source(edition(QUIET, 'a')), ist(15, 12))
        pw.run_cycle(self.store, Source(edition(QUIET, 'a')), ist(17, 8))
        self.assertEqual(self.store.get(plan['id'])['state'], 'plan_day')
        pw.run_cycle(self.store, Source(edition(QUIET, 'a')), ist(17, 13))
        self.assertEqual(self.store.get(plan['id'])['state'], 'ended')

    def test_not_connected_and_paused_plans_are_not_checked(self):
        fishing = self.plan(activity='fishing', hazard_codes=[], state='not_connected', not_connected='no sea-area product')
        paused = self.plan(state='paused')
        result = pw.run_cycle(self.store, Source(edition([[1], [1], [4], [1], [1]], 'b')), ist(15, 13))
        self.assertEqual(result['checked'], 0)
        self.assertIsNone(self.store.get(fishing['id']).get('last_snapshot'))
        self.assertIsNone(self.store.get(paused['id']).get('last_snapshot'))


class RecordedEditionTests(WatcherBase):
    def test_recorded_editions_replay_into_their_own_store_only(self):
        folder = Path(self.tmp.name) / 'editions'
        folder.mkdir()
        first, second = folder / 'a.json', folder / 'b.json'
        first.write_text(json.dumps({'schema_version': 'warning-edition-v1', 'meta': {'sha256': 'a', 'retrieved_at_utc': ist(15, 12).isoformat()},
                                     'body': payload(QUIET)}), encoding='utf-8')
        second.write_text(json.dumps({'schema_version': 'warning-edition-v1', 'meta': {'sha256': 'b', 'retrieved_at_utc': ist(15, 18).isoformat()},
                                      'body': payload([[1], [1], [4], [1], [1]])}), encoding='utf-8')
        self.plan()
        replay_store = PlanStore(Path(self.tmp.name) / 'plans-replay.sqlite')
        summary = pw.replay(self.store, replay_store, [first, second])
        self.assertEqual(summary['mode'], 'replay_of_recorded_editions')
        self.assertEqual(summary['notified'], 1)
        self.assertEqual(self.store.notifications(), [])
        self.assertEqual(len(replay_store.notifications()), 1)
        self.assertEqual(replay_store.notifications()[0]['receipt']['mode'], 'recorded')
        with self.assertRaises(SourceError):
            pw.replay(self.store, replay_store, [first])


class WorkspaceRouteTests(WatcherBase):
    def workspace(self):
        from types import SimpleNamespace
        from weathergpt_data.workspace import Workspace
        workspace = Workspace.__new__(Workspace)
        workspace.service = SimpleNamespace(ingestion_database=Path(self.tmp.name) / 'ingestion.sqlite')
        workspace.clock = lambda: ist(15, 13)
        workspace._foundation = object()
        workspace._plan_watcher = None
        return workspace

    def test_the_inbox_lists_plans_notifications_and_the_watcher_state(self):
        workspace = self.workspace()
        workspace.plan_store().create({'label': 'cotton', 'activity': 'spraying', 'hazard_codes': [4], 'kind': 'always',
                                       'place': {'label': 'Rajkot, Gujarat', 'district_key': 'RAJKOT'}, 'state': 'watching'})
        inbox = workspace.plans()
        self.assertEqual(inbox['mode'], 'live')
        self.assertEqual(len(inbox['plans']), 1)
        self.assertEqual(inbox['plans'][0]['place'], 'Rajkot, Gujarat')
        self.assertFalse(inbox['watcher']['running'])
        self.assertTrue(any('not an all-clear' in limit for limit in inbox['limits']))

    def test_update_pauses_ends_and_deletes_and_refuses_unknown_actions(self):
        workspace = self.workspace()
        plan = workspace.plan_store().create({'kind': 'always', 'place': {'district_key': 'RAJKOT'}, 'state': 'watching',
                                              'hazard_codes': [4]})
        self.assertEqual(workspace.update_plan({'id': plan['id'], 'action': 'pause'})['plan']['state'], 'paused')
        self.assertEqual(workspace.update_plan({'id': plan['id'], 'action': 'end'})['plan']['state'], 'ended')
        with self.assertRaises(ValueError):
            workspace.update_plan({'id': plan['id'], 'action': 'explode'})
        workspace.update_plan({'id': plan['id'], 'action': 'delete'})
        self.assertEqual(workspace.plan_store().list(), [])

    def test_check_now_runs_one_cycle_through_the_live_source(self):
        from unittest.mock import patch
        workspace = self.workspace()
        plan = workspace.plan_store().create({'kind': 'always', 'place': {'district_key': 'RAJKOT'}, 'state': 'watching',
                                              'hazard_codes': [4], 'saved_at': ist(15, 12).isoformat()})
        with patch('weathergpt_data.plan_watcher.LiveEditions', lambda foundation: Source(edition(QUIET, 'a'))):
            result = workspace.check_plans({})['result']
        self.assertEqual((result['checked'], result['read']), (1, True))
        self.assertIsNotNone(workspace.plan_store().get(plan['id'])['last_snapshot'])
        with self.assertRaises(ValueError):
            workspace.check_plans({'unexpected': 1})

    def test_a_replay_needs_two_recorded_editions(self):
        from unittest.mock import patch
        workspace = self.workspace()
        with patch('weathergpt_data.workspace.recorded_editions', lambda: []):
            with self.assertRaises(SourceError):
                workspace.replay_plans({})

    def test_backups_include_the_plan_store(self):
        from weathergpt_data.state_backup import default_sources
        self.assertIn('plans.sqlite', [path.name for path in default_sources(self.tmp.name)])


if __name__ == '__main__':
    unittest.main()
