#!/usr/bin/env python3
"""Measure which languages this workspace can read a day and a part of day from.

    python3 scripts/measure_language_time_reads.py

For every language in the language registry this asks the same question - "will it rain in
Ahmedabad tomorrow morning?", built from that language's own words - and records whether a
window was read, which window it was, and whether the planner produced a task at all. A
language with no word in the table is recorded as unread with the reason, never as covered.

This is a deterministic check of the workspace's own tables and planner. It measures no
translation quality, no fluent review and no publisher: a language can be readable here and
still have nothing able to render an answer in it, which the language registry records
separately and this measurement does not move.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.languages import LANGUAGES  # noqa: E402
from weathergpt_data.rule_planner import (PART_WINDOWS, TIME_WORDS, UNREAD_TIME_WORDS, window_for)  # noqa: E402
from weathergpt_data.transport import utcnow  # noqa: E402

IST = ZoneInfo('Asia/Kolkata')
# 04:00 IST: before every part-of-day window, so "the coming morning" is today's.
FIXED_NOW = datetime(2026, 9, 15, 4, 0, tzinfo=IST)
# A place the catalogue carries in every script, so the question is the same question.
PLACE = {'en': 'Ahmedabad', 'native': 'અમદાવાદ'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise SystemExit('Refusing to overwrite an existing measurement: ' + str(arguments.output))
    rows = []
    for code, entry in sorted(LANGUAGES.items()):
        words = TIME_WORDS.get(code)
        if not words:
            rows.append({'language': code, 'name': entry['english_name'], 'script': entry['script'],
                         'state': 'no_time_words_held',
                         'reason': 'declared unread: ' + str(UNREAD_TIME_WORDS.get(code, 'not in TIME_WORDS')),
                         'window_read': None})
            continue
        question = words['tomorrow'][0] + ' ' + words['parts']['morning'][0] + ' ' + PLACE['native']
        start, end, explicit, basis = window_for(question, FIXED_NOW)
        rows.append({'language': code, 'name': entry['english_name'], 'script': entry['script'],
                     'question_words': {'tomorrow': words['tomorrow'][0], 'morning': words['parts']['morning'][0]},
                     'state': 'read' if start else 'no_window_read',
                     'window_read': {'start_local': start or None, 'end_local': end or None,
                                     'basis': basis,
                                     'matches_the_product_morning': bool(start) and start[11:16] == PART_WINDOWS['morning'][0]},
                     'expected_start_local': '2026-09-16T' + PART_WINDOWS['morning'][0] + ':00+05:30'})
    summary = {'checked_at_utc': utcnow().isoformat(), 'languages_in_registry': len(LANGUAGES),
               'languages_with_time_words': len(TIME_WORDS),
               'languages_read': sum(1 for row in rows if row['state'] == 'read'),
               'languages_without_time_words': sum(1 for row in rows if row['state'] == 'no_time_words_held'),
               'wrong_window': [row['language'] for row in rows if row['state'] == 'read'
                                and not row['window_read']['matches_the_product_morning']],
               'romanised_variants_covered': sorted(set(TIME_WORDS) - set(LANGUAGES)),
               'parts_of_day_defined': sorted(PART_WINDOWS),
               'limits': ['A language that can be read here may still have nothing able to render an answer in it; '
                          'the language registry records speak, write and hear separately and this measurement does not move them.',
                          'This is the workspace\'s own tables and planner, not a translation or fluency review.',
                          'A part of day is read as the coming occurrence, and a day word as the whole source day.',
                          'Hinglish (hi-Latn) is a romanised variant with its own words; it is counted separately and is not a registry language.']}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps({'summary': summary, 'languages': rows}, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    for row in rows:
        if row['state'] != 'read':
            print(' not read:', row['language'], row['name'], '-', str(row.get('reason'))[:90])


if __name__ == '__main__':
    main()
