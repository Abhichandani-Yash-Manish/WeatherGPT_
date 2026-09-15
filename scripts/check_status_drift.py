#!/usr/bin/env python3
"""Fail when the current summary and the registries drift from the code and evidence.

docs/21 A07 recorded that nested current-evidence text could cite an old test count and
that no single summary pointed at the latest evidence. This check makes that drift loud:

  * README's recorded Python test count must equal what pytest collects.
  * Every batch document the registries name must exist.
  * Every evidence path a registry names must exist.
  * The source ledger's counts must equal its own rows.
  * Every finding carries a status from the declared vocabulary.

It reads files and collects tests; it changes nothing.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_VOCABULARY = {'open', 'partial', 'blocked', 'verified_scoped', 'verified', 'not_started', 'held'}


def read_json(relative):
    return json.loads((ROOT / relative).read_text())


def readme_test_count():
    match = re.search(r'#\s*(\d+)\s+Python tests', (ROOT / 'README.md').read_text())
    return int(match.group(1)) if match else None


def collected_test_count():
    result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '--collect-only', '-q'],
                            cwd=str(ROOT), capture_output=True, text=True)
    for line in reversed(result.stdout.strip().splitlines()):
        match = re.search(r'(\d+) tests? collected', line)
        if match:
            return int(match.group(1))
    return None


def main():
    problems = []
    readme_count = readme_test_count()
    actual_count = collected_test_count()
    if readme_count is None:
        problems.append('README does not record a Python test count')
    elif actual_count is None:
        problems.append('pytest collection did not report a test count')
    elif readme_count != actual_count:
        problems.append('README records %s Python tests but pytest collects %s' % (readme_count, actual_count))

    product = read_json('data/registry/product-progress.json')
    for key in ('latest_batch', 'critical_review', 'standing_instructions'):
        value = product.get(key)
        if value and not (ROOT / value).exists():
            problems.append('product-progress %s points at a missing file: %s' % (key, value))
    for path in (product.get('open_paths') or []):
        if path.get('plan') and not (ROOT / path['plan']).exists():
            problems.append('product-progress open path points at a missing plan: ' + str(path['plan']))
    for finding, entry in (product.get('findings') or {}).items():
        status = entry.get('status')
        if status not in STATUS_VOCABULARY:
            problems.append('product-progress %s has an undeclared status: %s' % (finding, status))
        for key in ('evidence', 'latest_evidence'):
            value = entry.get(key)
            if value and not value.startswith('http') and not (ROOT / value).exists():
                problems.append('product-progress %s %s points at a missing document: %s' % (finding, key, value))

    hardening = read_json('data/registry/hardening-progress.json')
    for section, value in hardening.items():
        if not isinstance(value, dict) or not section.endswith('_batch'):
            continue
        report = value.get('report')
        if report and not (ROOT / report).exists():
            problems.append('hardening-progress %s points at a missing report: %s' % (section, report))
        evidence = value.get('evidence_directory')
        if evidence and not (ROOT / evidence).exists():
            problems.append('hardening-progress %s points at a missing evidence directory: %s' % (section, evidence))

    ledger = read_json('data/registry/source-review.json')
    counts = ledger.get('counts') or {}
    actual = {}
    for row in ledger.get('sources', []):
        actual[row['status']] = actual.get(row['status'], 0) + 1
    if counts != actual:
        problems.append('source ledger counts disagree with its rows: recorded %s, rows %s' % (counts, actual))
    if not Path(ROOT / (ledger.get('evidence_directory') or '')).exists():
        problems.append('source ledger evidence_directory does not exist: ' + str(ledger.get('evidence_directory')))

    for name in ('data/registry/acceptance-benchmark.json', 'data/registry/language-support.json'):
        try:
            read_json(name)
        except (OSError, ValueError) as error:
            problems.append('%s does not parse: %s' % (name, error))

    for problem in problems:
        print('DRIFT: ' + problem)
    print('status drift: %d problem(s); collected tests %s, README %s' % (len(problems), actual_count, readme_count))
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
