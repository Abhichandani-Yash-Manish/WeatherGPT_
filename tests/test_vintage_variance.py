"""Vintage variance reads stored retrieval vintages; it is not a skill measure."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.measure_vintage_variance import measure


def database(path, rows):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY,spec TEXT)')
        db.execute('CREATE TABLE versions (job_id TEXT,stream TEXT,cycle REAL,committed REAL,sha256 TEXT,result TEXT,coverage TEXT)')
        for index, (spec, committed, records) in enumerate(rows):
            job = 'job%d' % index
            db.execute('INSERT INTO jobs VALUES (?,?)', (job, json.dumps(spec)))
            db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?,?)',
                       (job, 'stream', 0, committed, 'sha', json.dumps({'records': records}), '{}'))
    return path


class VarianceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'ingestion.sqlite'

    def tearDown(self):
        self.tmp.cleanup()

    def test_overlapping_valid_hours_are_compared_and_gaps_ignored(self):
        spec = {'product': 'forecast', 'latitude': 23.0, 'longitude': 72.5}
        first = {'parameter': 'temperature_2m', 'valid_time_utc': '2026-09-13T10:00:00+00:00', 'value': 29.1}
        second = {'parameter': 'temperature_2m', 'valid_time_utc': '2026-09-13T10:00:00+00:00', 'value': 24.3}
        only = {'parameter': 'temperature_2m', 'valid_time_utc': '2026-09-13T11:00:00+00:00', 'value': 30.0}
        database(self.path, [(spec, 100.0, [first, only]), (spec, 200.0, [second])])
        report = measure(self.path)
        self.assertEqual(report['overlapping_valid_hours'], 1)
        entry = report['by_parameter']['temperature_2m']
        self.assertEqual(entry['max_abs_change'], 4.8)
        self.assertEqual(entry['valid_hours'], 1)
        self.assertEqual(report['points'][0]['vintages'], 2)

    def test_a_single_vintage_reports_no_change_and_says_what_is_not_established(self):
        spec = {'product': 'forecast', 'latitude': 10.0, 'longitude': 76.0}
        row = {'parameter': 'precipitation', 'valid_time_utc': '2026-09-13T10:00:00+00:00', 'value': 1.0}
        database(self.path, [(spec, 100.0, [row])])
        report = measure(self.path)
        self.assertEqual(report['overlapping_valid_hours'], 0)
        self.assertEqual(report['by_parameter'], {})
        self.assertIn('forecast skill', ' '.join(report['not_established']))
        self.assertIn('run identity', ' '.join(report['limitations']))


if __name__ == '__main__':
    unittest.main()
