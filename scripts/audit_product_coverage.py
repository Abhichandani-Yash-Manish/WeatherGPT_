#!/usr/bin/env python3
"""Validate data/registry/product-coverage.json against the code and registries it describes.

    python3 scripts/audit_product_coverage.py

Coverage is stated per product (F1d), which means the statement must agree with the code that enforces
it: the forecast horizon in the registry must equal the constant the engine raises, the agromet
directory size must equal the tracked directory snapshot, and every served source must sit inside some
product's coverage row. A coverage claim that drifted from the code would be exactly the "implied
nationwide" this file exists to prevent.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(problems, message):
    problems.append(message)


def main():
    problems = []
    coverage = json.loads((ROOT / 'data/registry/product-coverage.json').read_text())
    rows = coverage.get('products') or []
    if coverage.get('schema_version') != 'product-coverage-v1':
        fail(problems, 'schema_version is not product-coverage-v1')
    if not coverage.get('as_of'):
        fail(problems, 'as_of is missing')
    if not rows:
        fail(problems, 'no product rows')

    # Every row is complete and never silent about what it does not cover.
    for row in rows:
        for field in ('id', 'sources', 'kind', 'geography', 'time', 'granularity', 'cadence'):
            if not row.get(field):
                fail(problems, '%s: %s is missing or empty' % (row.get('id', '?'), field))
        if not row.get('not_covered'):
            fail(problems, '%s: not_covered is empty - a coverage statement names its limits' % row.get('id', '?'))

    by_id = {row['id']: row for row in rows}

    # Every source a capability serves sits inside some coverage row, and no row names an unknown source.
    from weathergpt_data.capabilities import CAPABILITIES
    served = {source for capability in CAPABILITIES for source in capability['sources']}
    covered = {source for row in rows for source in row['sources']}
    for source in sorted(served - covered):
        fail(problems, 'source %s is served by a capability but covered by no row' % source)
    registry = {entry['id'] for entry in json.loads((ROOT / 'data/registry/sources.json').read_text())['products']}
    for source in sorted(covered - registry):
        fail(problems, 'row names source %s, which is not in the source registry' % source)

    # The constants the rows state are the constants the code enforces.
    from weathergpt_data import adapters, capabilities, verification_tasks
    checks = [
        ('gfs_exact_window', 'horizon_days', adapters.FORECAST_HORIZON_DAYS),
        ('hourly_best_match', 'horizon_hours', capabilities.HOURLY_HORIZON_HOURS),
        ('era5_daily_reanalysis', 'delay_days', adapters.REANALYSIS_DELAY_DAYS),
        ('forecast_verification', 'delay_days', verification_tasks.DELAY_DAYS),
        ('forecast_verification', 'max_days', verification_tasks.MAX_DAYS),
    ]
    for row_id, key, actual in checks:
        row = by_id.get(row_id)
        stated = ((row or {}).get('constants') or {}).get(key)
        if stated != actual:
            fail(problems, '%s.constants.%s says %r but the code enforces %r' % (row_id, key, stated, actual))
    if by_id.get('era5_daily_reanalysis', {}).get('constants', {}).get('min_year') != min(adapters.REANALYSIS_MIN_YEAR.values()):
        fail(problems, 'era5_daily_reanalysis.constants.min_year disagrees with REANALYSIS_MIN_YEAR')

    # The marine/river guard the rows state exists as the guard sentence in the tool.
    specialist = (ROOT / 'weathergpt_data/specialist_tasks.py').read_text()
    for row_id in ('marine_waves', 'river_discharge'):
        stated = by_id.get(row_id, {}).get('constants', {}).get('cell_guard_km')
        if stated != 50 or '50 km sampling guard' not in specialist:
            fail(problems, '%s: the 50 km cell guard is stated but not found in specialist_tasks.py' % row_id)

    # The agromet directory size the row states is the tracked directory snapshot's own count.
    directory = json.loads((ROOT / 'data/processed/foundation/advisory-directory.json').read_text())
    stated = by_id.get('agromet_advisories', {}).get('constants', {}).get('directory_entries')
    if stated != directory.get('listed_district_entries'):
        fail(problems, 'agromet directory entries: registry says %r, the tracked directory lists %r'
             % (stated, directory.get('listed_district_entries')))

    # The published national table's years agree with the climate build's own audit.
    national = by_id.get('published_national_history', {}).get('constants', {})
    climate_src = (ROOT / 'weathergpt_data/climate.py').read_text()
    years = re.search(r"'years':\[(\d+),(\d+)\]", climate_src)
    if years and (national.get('first_year') != int(years.group(1)) or national.get('last_year') != int(years.group(2))):
        fail(problems, 'national history years %r disagree with the climate build audit %s'
             % (national, years.group(0)))

    if problems:
        print('product coverage audit: %d problem(s)' % len(problems))
        for problem in problems:
            print(' -', problem)
        return 1
    print('product coverage audit: %d product(s), all statements agree with the code' % len(rows))
    return 0


if __name__ == '__main__':
    sys.exit(main())
