#!/usr/bin/env python3
"""Capture real conversation packets from the running workspace.

The frontend overhaul must render the packet the engine actually returns, not
the packet the documentation implies. This drives the live loopback API and
stores each response beside the question that produced it, plus the accepted
request and the HTTP status, so a renderer can be built against real shapes.

Local model turns are slow and the workspace holds one conversation lock, so
requests run sequentially. Failures are recorded, not skipped.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUESTIONS = [
    ('forecast-simple', 'Will it rain in Ahmedabad, Gujarat tomorrow morning?'),
    ('multi-task', 'Compare the rain amount for tomorrow afternoon in Kochi, Kerala with GFS too, including the chance of rain.'),
    ('historical-chart', 'Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.'),
    ('clarification', 'Tell me about rainfall in Bhopal.'),
    ('warning', 'Is there any official flood warning for Patna right now?'),
    ('marine', 'What are the wave conditions near Kochi, Kerala tomorrow?'),
    ('airport', 'What is the current weather at VOBL?'),
    ('language-hindi', 'कल अहमदाबाद में बारिश होगी क्या?'),
]


def fetch(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:8765')
    parser.add_argument('--out', type=Path, default=ROOT / 'research/reviews/frontend-overhaul-20260914/packets')
    parser.add_argument('--timeout', type=float, default=240, help='seconds allowed per model turn')
    parser.add_argument('--only', nargs='*', help='capture only these case names')
    arguments = parser.parse_args()

    index = fetch(arguments.base + '/')
    token = re.search(r'name="workspace-token" content="([^"]+)"', index)
    if not token:
        raise SystemExit('The workspace page did not contain a session token. Is this the workspace server?')
    token = token.group(1)
    origin = arguments.base

    arguments.out.mkdir(parents=True, exist_ok=True)
    cases = [c for c in QUESTIONS if not arguments.only or c[0] in arguments.only]
    summary = []

    for name, question in cases:
        request = {'question': question}
        record = {'case': name, 'request': request, 'base': arguments.base}
        began = time.monotonic()
        try:
            body = json.dumps(request).encode('utf-8')
            http = urllib.request.Request(
                arguments.base + '/api/chat', data=body,
                headers={'Content-Type': 'application/json', 'X-WeatherGPT-Token': token, 'Origin': origin},
            )
            with urllib.request.urlopen(http, timeout=arguments.timeout) as response:
                packet = json.loads(response.read().decode('utf-8'))
                record['http_status'] = response.status
            record['duration_s'] = round(time.monotonic() - began, 1)
            record['packet'] = packet
            record['observed_keys'] = sorted(packet.keys())
            record['non_empty'] = sorted(k for k, v in packet.items() if v not in (None, [], {}, ''))
            summary.append({'case': name, 'status': packet.get('status'), 'keys': record['non_empty'], 'duration_s': record['duration_s']})
        except urllib.error.HTTPError as error:
            record['duration_s'] = round(time.monotonic() - began, 1)
            record['http_status'] = error.code
            record['error'] = error.read().decode('utf-8', 'replace')
            summary.append({'case': name, 'status': 'HTTP ' + str(error.code), 'error': record['error'][:120]})
        except Exception as error:  # noqa: BLE001 - a failed probe is evidence, not a reason to stop
            record['duration_s'] = round(time.monotonic() - began, 1)
            record['error'] = type(error).__name__ + ': ' + str(error)
            summary.append({'case': name, 'status': 'failed', 'error': record['error'][:120]})

        (arguments.out / (name + '.json')).write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')
        print('{:<18} {} ({})'.format(name, summary[-1].get('status'), record.get('duration_s')), flush=True)

    (arguments.out / 'summary.json').write_text(json.dumps({
        'schema_version': 'frontend-packet-capture-v1',
        'base': arguments.base,
        'cases': summary,
        'limitations': 'Single-run local-model probes against stored evidence. Not a benchmark and not unseen holdouts; failed cases are retained deliberately.',
    }, indent=2, ensure_ascii=False), encoding='utf-8')
    print('\nCaptured ' + str(len(cases)) + ' cases into ' + str(arguments.out.relative_to(ROOT)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
