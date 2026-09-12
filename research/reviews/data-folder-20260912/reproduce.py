"""Offline review probes; production data is read-only and all mutations are temporary."""
import json
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from test_ingestion import NOW, Response, payload
from weathergpt_data.ingestion import IngestionDB, restore, run_one


def main():
    findings = {}
    with tempfile.TemporaryDirectory(prefix='weathergpt-review-') as temporary:
        temp = Path(temporary)
        current = [NOW]
        db = IngestionDB(temp / 'jobs.sqlite', clock=lambda: current[0])
        try:
            first = db.enqueue('forecast', 23., 72.5, 3, NOW.isoformat())
            result = run_one(db, temp / 'raw', lambda *a, **k: Response(json.dumps(payload()).encode()))
            assert result['state'] == 'succeeded'
            stream = db.db.execute('SELECT stream FROM jobs WHERE id=?', (first,)).fetchone()[0]
            published = db.latest(stream)
            rain = [r for r in published['result']['records'] if r['parameter'] == 'precipitation']
            findings['rainfall_coverage'] = {
                'receipt_start': published['coverage']['window_start'],
                'receipt_end': published['coverage']['window_end'],
                'actual_first_rain_interval_start': rain[0]['interval_start_utc'],
                'actual_last_rain_interval_end': rain[-1]['interval_end_utc'],
                'explanation': 'The shared receipt window describes sample labels; preceding-hour rain starts and ends one hour earlier. It cannot certify complete rain accumulation over that window.',
            }
            current[0] += timedelta(minutes=1)
            db.enqueue('forecast', 23., 72.5, 3, current[0].isoformat())
            assert run_one(db, temp / 'raw', lambda *a, **k: Response(b'{}'))['state'] == 'failed'
            before = db.latest(stream)
            assert before['status'] == 'refresh_failed_or_missed'
            db.enqueue('forecast', 23., 72.5, 3, (current[0] + timedelta(hours=1)).isoformat())
            after = db.latest(stream)
            assert after['status'] == 'prototype_snapshot'
            findings['future_job_masks_failed_refresh'] = {
                'before_future_enqueue': before['status'],
                'after_future_enqueue': after['status'],
                'reported_latest_state': after['latest_collection_job']['state'],
                'published_version_unchanged': before['job_id'] == after['job_id'],
            }
        finally:
            db.close()
        bundle = temp / 'incomplete-backup'
        bundle.mkdir()
        (bundle / 'backup-manifest.json').write_text(json.dumps({'files': {}}))
        restored = restore(bundle, temp / 'restored')
        with sqlite3.connect(restored['database']) as connection:
            tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        assert not tables
        findings['incomplete_backup_accepted'] = {'restore_returned_success': True, 'restored_tables': tables}

    district = ROOT / 'data/processed/districts/district-v1-c8b978172b77182e/districts.sqlite'
    with sqlite3.connect(district.as_uri() + '?mode=ro', uri=True) as con:
        assert con.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        series = {}
        flags = Counter()
        missing = Counter()
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        for sid, year, state, name, text in con.execute('SELECT series_id,year,state,district,payload FROM rainfall'):
            row = json.loads(text)
            entry = series.setdefault(sid, {'state': state, 'district': name, 'years': [], 'missing_months': 0})
            entry['years'].append(year)
            count = sum(row[m + '_mm'] == '' for m in months)
            entry['missing_months'] += count
            missing[state] += count
            flags.update(f for f in row['quality_flags'].split(';') if f)
        findings['district_profile'] = {
            'rows': sum(len(v['years']) for v in series.values()),
            'series': len(series),
            'min_year': min(min(v['years']) for v in series.values()),
            'max_year': max(max(v['years']) for v in series.values()),
            'missing_months': sum(missing.values()),
            'series_with_missing_months': sum(v['missing_months'] > 0 for v in series.values()),
            'series_with_internal_missing_years': sum(len(v['years']) != max(v['years']) - min(v['years']) + 1 for v in series.values()),
            'rows_by_quality_flag': dict(flags),
            'most_missing_months_by_source_state': missing.most_common(8),
        }
    files = [p for p in (ROOT / 'data').rglob('*') if p.is_file() and p.name != '.DS_Store']
    findings['inventory'] = {'files': len(files), 'logical_bytes': sum(p.stat().st_size for p in files),
                             'top_level_bytes': {d.name: sum(p.stat().st_size for p in files if d in p.parents)
                                                 for d in (ROOT / 'data').iterdir() if d.is_dir()}}
    return findings


if __name__ == '__main__':
    print(json.dumps(main(), indent=2))
