#!/usr/bin/env python3
"""Write a dated briefing over named places, once or on a foreground interval.

    python3 scripts/briefing.py --place 'Ahmedabad, Gujarat' --place 'Kochi, Kerala' --day 1 --out research/implementation/briefing-20260915
    python3 scripts/briefing.py --place 'Ahmedabad, Gujarat' --every 20 --runs 2 --out /tmp/series

A briefing reads what the connected products publish for each place: the official district
warning day, the CAP relay reported separately, and the forecast window as retrieved. It is not a
warning, not an all-clear and not advice, and it is not delivered anywhere.

The --every interval is a foreground interval, not a service: the runner sleeps between runs
inside this process. Nothing here is a daemon, a push channel or a scheduler outside this command.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.briefing_run import (RUNNER_NOTE, compose, load_previous, markdown,  # noqa: E402
                                           resolve_place, summary_line)
from weathergpt_data.workspace import Workspace  # noqa: E402


def write_run(out, briefing, latency, seconds, index):
    out.mkdir(parents=True, exist_ok=True)
    stamp = briefing['generated_at_utc'].replace(':', '').replace('-', '').replace('+0000', 'Z')
    markdown_path = out / ('briefing-' + stamp + '.md')
    record_path = out / ('record-' + stamp + '.json')
    markdown_path.write_text(markdown(briefing), encoding='utf-8')
    record = {'runner': 'scripts/briefing.py', 'runner_note': RUNNER_NOTE, 'interval_seconds': seconds,
              'run_number': index + 1, 'latency_seconds': latency, 'markdown_path': str(markdown_path),
              'briefing': briefing}
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
    return markdown_path, record_path, stamp


def update_index(out, entry):
    index_path = out / 'index.json'
    rows = []
    if index_path.exists():
        try:
            rows = json.loads(index_path.read_text(encoding='utf-8')).get('runs') or []
        except ValueError:
            rows = []
    rows.append(entry)
    index_path.write_text(json.dumps({'schema_version': 'briefing-index-v1', 'runner_note': RUNNER_NOTE, 'runs': rows},
                                     indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
    return index_path

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--place', action='append', default=[], help='a place name, optionally with its state')
    parser.add_argument('--day', type=int, default=1, help='which published day of the district product to read')
    parser.add_argument('--forecast-days', type=int, default=3)
    parser.add_argument('--out', type=Path, required=True, help='the series directory')
    parser.add_argument('--every', type=int, default=0, help='seconds between runs; 0 runs once')
    parser.add_argument('--runs', type=int, default=1, help='how many runs in this invocation')
    parser.add_argument('--json', action='store_true')
    arguments = parser.parse_args()
    if not arguments.place:
        raise SystemExit('Name at least one place with --place. A briefing reads named places; it does not sweep the country.')
    if arguments.every < 0 or arguments.runs < 1:
        raise SystemExit('Give a non-negative interval and at least one run.')
    if arguments.every and arguments.runs < 2:
        raise SystemExit('An interval needs at least two runs to be measured as an interval; give --runs 2 or more.')
    out = arguments.out if arguments.out.is_absolute() else ROOT / arguments.out
    places = [resolve_place(place) for place in arguments.place]
    workspace = Workspace()
    index_path = None
    for number in range(arguments.runs):
        previous = None
        records = sorted(out.glob('record-*.json'))
        if records:
            previous = load_previous(records[-1])
        began = time.monotonic()
        briefing = compose(workspace.foundation(), places, day=arguments.day, forecast_days=arguments.forecast_days, previous=previous)
        latency = round(time.monotonic() - began, 3)
        markdown_path, record_path, _stamp = write_run(out, briefing, latency, arguments.every, number)
        entry = {'run': number + 1, 'generated_at_utc': briefing['generated_at_utc'], 'briefing_id': briefing['briefing_id'],
                 'place_count': briefing['place_count'], 'latency_seconds': latency, 'interval_seconds': arguments.every,
                 'markdown_path': str(markdown_path), 'record_path': str(record_path),
                 'change': (briefing.get('change_since_previous') or {}).get('reading'),
                 'places': [{'label': record['label'], 'district': record.get('district'), 'state': record.get('state'),
                             'official_day': ((record.get('official_day') or {}).get('status_line')),
                             'unavailable': [item['part'] for item in record.get('unavailable') or []]}
                            for record in briefing['places']]}
        index_path = update_index(out, entry)
        if arguments.json:
            print(json.dumps({'record': str(record_path), 'briefing': briefing}, indent=2, ensure_ascii=False))
        else:
            print('run %d/%d - %s - %s' % (number + 1, arguments.runs, str(record_path), summary_line(briefing)))
            print('  latency: %.3f s - change: %s - sources: %s'
                  % (latency, (briefing.get('change_since_previous') or {}).get('reading'), ', '.join(briefing['sources']) or 'none'))
        if number + 1 < arguments.runs:
            when = (datetime.now(timezone.utc) + timedelta(seconds=arguments.every)).replace(microsecond=0).isoformat()
            print('  next run at ' + when + ' (a foreground interval: the runner sleeps, nothing is scheduled outside this process)')
            time.sleep(arguments.every)
    print('series: ' + str(index_path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
