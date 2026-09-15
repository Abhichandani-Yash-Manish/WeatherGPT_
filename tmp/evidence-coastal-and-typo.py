#!/usr/bin/env python3
"""Round 11 driver: a misspelt state and a coast, live, after the repairs."""
import json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/implementation/coastal-and-typo-repairs-20260915'
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
    journeys = [
        ('misspelt-state', 'Will it rain in Ahmedbad, Gujrat tomorrow?', 'chat-typo-state.json'),
        ('coast-alone', 'Are there warnings for the Kerala coast?', 'chat-coast-alone.json'),
        ('coast-and-port', 'Are there warnings for the Kerala coast and what are the waves off Kochi?', 'chat-coast-and-port.json'),
        ('port-only', 'What are the waves off Kochi for tomorrow?', 'chat-port-only.json'),
    ]
    rows = []
    for name, question, target in journeys:
        packet = call('/api/chat', 'POST', {'question': question}, token)
        (OUT / target).write_text(json.dumps(packet, indent=2, ensure_ascii=False) + chr(10))
        rows.append({'name': name, 'question': question, 'status': packet.get('status'),
                     'facts': len(packet.get('facts') or []), 'choices': len(packet.get('choices') or []),
                     'answer': (packet.get('answer') or '')[:260].replace(chr(10), ' '),
                     'notes': [note for note in (packet.get('notes') or []) if 'read as' in note.lower() or 'sea area' in note.lower()][:3],
                     'tasks': [task.get('status') for task in (packet.get('task_results') or [])]})
        print(name, '->', packet.get('status'), '| facts', len(packet.get('facts') or []), '| choices', len(packet.get('choices') or []))
    lines = ['# A misspelt state and a coast: what changed, measured live', '', "Driver: `tmp/evidence-coastal-and-typo.py` against a live local server. This is a desktop-web and engine check, not native-speaker, mobile or cross-browser acceptance.", '', "Repairs: a misspelt state name no longer empties a candidate list the place itself matched, and a coast or sea is read as a region rather than searched for as a settlement. Both were found by the sealed holdout of 15 September 2026 and are recorded as having been informed by it.", '', '## Measured', '']
    for row in rows:
        lines.append('- **' + row['name'] + '** — ' + row['question'])
        lines.append('  - status: ' + str(row['status']) + ' · facts: ' + str(row['facts']) + ' · choices offered: ' + str(row['choices']) + ' · task statuses: ' + str(row['tasks']))
        lines.append('  - answer: ' + str(row['answer']))
        for note in row['notes']:
            lines.append('  - note: ' + str(note)[:200])
    lines += ['', '## What this does not establish', '', "- No accuracy claim about place resolution in general: two typo patterns and one coast shape were measured.", "              '- A coast question still asks for a district or a port, because the official district product has nothing to match for a sea area and the sea-area bulletins remain unconnected.", "              '- No usability, native-language or mobile acceptance was measured.'", '']
    (OUT / 'journey.md').write_text(chr(10).join(lines))
    print('written', OUT / 'journey.md')


if __name__ == '__main__':
    main()