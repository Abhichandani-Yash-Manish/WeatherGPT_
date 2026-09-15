#!/usr/bin/env python3
"""Round 14 driver: the right-now reading, from the page's view and from the conversation."""
import json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/implementation/right-now-20260915'
BASE = 'http://127.0.0.1:8790'


def call(path, method='GET', body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header('Host', '127.0.0.1:8790')
    if body is not None:
        request.add_header('Content-Type', 'application/json')
        request.add_header('Origin', BASE)
    if token:
        request.add_header('X-WeatherGPT-Token', token)
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode('utf-8'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    page = urllib.request.urlopen(BASE + '/', timeout=60).read().decode('utf-8')
    token = re.search(r'name="workspace-token" content="([^"]+)"', page).group(1)
    now = call('/api/now?lat=23.02579&lon=72.58727', token=token)
    (OUT / 'now-view.json').write_text(json.dumps(now, indent=2, ensure_ascii=False) + chr(10))
    print('view', now['status'], '| stations', len((now['data']['observed'] or {}).get('stations') or []),
          '| hours', len((now['data']['next_hours'] or {}).get('rows') or []),
          '| sources', [source['source_id'] for source in now['sources']])
    rows = []
    for name, question, target in [
        ('chat-right-now', "What's it like right now in Ahmedabad?", 'chat-right-now.json'),
        ('chat-station-code', 'What is being observed at VOBL right now?', 'chat-station-code.json'),
    ]:
        packet = call('/api/chat', 'POST', {'question': question}, token)
        (OUT / target).write_text(json.dumps(packet, indent=2, ensure_ascii=False) + chr(10))
        planning = (packet.get('trace') or {}).get('planning') or {}
        rows.append({'name': name, 'question': question, 'status': packet.get('status'),
                     'facts': len(packet.get('facts') or []), 'provider': planning.get('provider'),
                     'tools': [tool.get('name') for tool in (packet.get('trace') or {}).get('tools') or []],
                     'notes': [note[:200] for note in (packet.get('notes') or [])[:8]]})
        print(name, '->', packet.get('status'), '| facts', len(packet.get('facts') or []), '| provider', planning.get('provider'))
    lines = ['# The right-now reading: what a station reported, what is published, what is next', '', "Driver: `tmp/evidence-right-now.py` against a live local server. Station reports come from the connected METAR and AWS layers (S63); the published day from the official district warning product (S63); the next hours from the model product (S62). Radar and satellite imagery, sub-hourly refresh and push are not connected and the reading says so.", '', '## Measured', '']
    reading = now['data']
    lines.append('- `/api/now` for 23.02579, 72.58727 -> ' + str(now['status']) + ' with ' +
                 str(len((reading.get('observed') or {}).get('stations') or [])) + ' station row(s), ' +
                 str(len((reading.get('next_hours') or {}).get('rows') or [])) + ' model hour(s) and the published day ' +
                 str((reading.get('in_force') or {}).get('day')) + '.')
    lines.append('- Sources named: ' + ', '.join(source['source_id'] for source in now['sources']) + '.')
    lines.append('- Summary as written: ' + str(reading.get('summary'))[:600])
    lines.append('')
    for row in rows:
        lines.append('- **' + row['name'] + '** — ' + row['question'])
        lines.append('  - status: ' + str(row['status']) + ' · planner: ' + str(row['provider']) + ' · facts: ' + str(row['facts']) + ' · tools: ' + ', '.join(str(tool) for tool in row['tools']))
        for note in row['notes']:
            lines.append('  - note: ' + note)
    lines += ['', '## What this does not establish', '', "- No radar or satellite imagery, no sub-hourly refresh and no push: the reading states that where it would otherwise be implied.", "- A station report is one station at one instant and is not a district average, a field reading or a forecast.", "- No accuracy claim: the reading reports what the connected products returned at that instant.", "- One point and one instant were measured.", '']
    (OUT / 'journey.md').write_text(chr(10).join(lines))
    print('written', OUT / 'journey.md')


if __name__ == '__main__':
    main()