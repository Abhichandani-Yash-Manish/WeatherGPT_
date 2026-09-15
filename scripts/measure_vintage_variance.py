#!/usr/bin/env python3
"""Measure how stored forecast vintages differ for the same valid hour.

This is NOT forecast skill, calibration or a confidence score. The ingestion store does
not expose upstream model run identity, so two retrieved vintages can differ because the
model reran, because the horizon shortened, or both. What this reports is exactly what it
measured: for each requested point, parameter and valid hour, the change between the
earliest and latest stored retrieval that covers it, with the retrieval instants named.

    python3 scripts/measure_vintage_variance.py --output report.json
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.answers import ROOT as ANSWER_ROOT  # noqa: E402
from weathergpt_data.transport import stamp, utcnow  # noqa: E402

DEFAULT_DATABASE = ANSWER_ROOT / 'data/runtime/ingestion/ingestion.sqlite'


def instant(value):
    """Committed instants are stored as epoch floats."""
    return datetime.fromtimestamp(float(value), timezone.utc).isoformat()


def measure(database):
    connection = sqlite3.connect(Path(database).as_uri() + '?mode=ro', uri=True)
    try:
        rows = connection.execute(
            'SELECT v.committed,v.cycle,v.result,j.spec FROM versions v JOIN jobs j ON j.id=v.job_id '
            "WHERE json_extract(j.spec,'$.product') IN ('forecast','extended_forecast') ORDER BY v.committed").fetchall()
    finally:
        connection.close()
    series = {}
    points = {}
    for committed, cycle, result, spec in rows:
        try:
            spec_data = json.loads(spec); payload = json.loads(result)
        except (TypeError, ValueError):
            continue
        key_point = (spec_data.get('latitude'), spec_data.get('longitude'))
        points.setdefault(key_point, {'latitude': key_point[0], 'longitude': key_point[1], 'vintages': 0,
                                      'first_retrieved': None, 'last_retrieved': None})
        points[key_point]['vintages'] += 1
        retrieved = instant(committed)
        points[key_point]['first_retrieved'] = points[key_point]['first_retrieved'] or retrieved
        points[key_point]['last_retrieved'] = retrieved
        for record in payload.get('records') or []:
            if record.get('value') is None:
                continue
            key = (key_point, record.get('parameter'), record.get('valid_time_utc'))
            series.setdefault(key, []).append((committed, record.get('value')))
    per_parameter = {}
    samples = 0
    for (point, parameter, valid_time), values in series.items():
        unique = {}
        for committed, value in values:
            unique.setdefault(committed, value)
        if len(unique) < 2:
            continue
        ordered = [value for _, value in sorted(unique.items())]
        first, last = ordered[0], ordered[-1]
        change = abs(float(last) - float(first))
        entry = per_parameter.setdefault(parameter, {'valid_hours': 0, 'total_abs_change': 0.0, 'max_abs_change': 0.0,
                                                     'example': None})
        entry['valid_hours'] += 1
        entry['total_abs_change'] += change
        if change > entry['max_abs_change']:
            entry['max_abs_change'] = round(change, 4)
            entry['example'] = {'valid_time_utc': valid_time, 'first_value': first, 'last_value': last,
                                'first_committed_utc': instant(min(unique)), 'last_committed_utc': instant(max(unique))}
        samples += 1
    for entry in per_parameter.values():
        entry['mean_abs_change'] = round(entry['total_abs_change'] / entry['valid_hours'], 4)
        entry.pop('total_abs_change')
    return {'schema_version': 'vintage-variance-v1', 'measured_at_utc': stamp(utcnow()),
            'database': str(Path(database)), 'points': list(points.values()),
            'overlapping_valid_hours': samples, 'by_parameter': per_parameter,
            'not_established': ['forecast skill, calibration or accuracy: no observations or analysis are matched here',
                                'attribution of a change to a model run: upstream run identity is not exposed by the store',
                                'spatial representativeness: modelled grid values are not local measurements'],
            'limitations': ['Vintage changes conflate model updates with shorter horizons because run identity is unknown.',
                            'Only points and windows that were retrieved more than once can be compared.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    report = measure(args.database)
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps({k: report[k] for k in ('overlapping_valid_hours', 'by_parameter', 'points')}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
