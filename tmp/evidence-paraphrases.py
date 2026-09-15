#!/usr/bin/env python3
"""Round 15 driver: the repaired shapes, live, in the scripts and wordings that failed."""
import json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/implementation/paraphrase-robustness-20260915'
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


def adherence_of(packet):
    trace = packet.get('trace') or {}
    generation = trace.get('generation') if isinstance(trace.get('generation'), dict) else {}
    language = trace.get('language') if isinstance(trace.get('language'), dict) else {}
    return (generation or {}).get('language_adherence') or (language or {}).get('adherence')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    page = urllib.request.urlopen(BASE + '/', timeout=60).read().decode('utf-8')
    token = re.search(r'name="workspace-token" content="([^"]+)"', page).group(1)
    journeys = [
        ('devanagari-rain', 'कल अहमदाबाद, गुजरात में सुबह बारिश होगी?', 'chat-devanagari-rain.json'),
        ('gujarati-rain', 'અમદાવાદમાં આવતીકાલે વરસાદ થશે?', 'chat-gujarati-rain.json'),
        ('station-code', 'VOBL ka current weather kya hai?', 'chat-station-code.json'),
        ('agromet-bulletin', 'Gujarat state agromet advisory me irrigation ke baare me kya likha hai?', 'chat-agromet-bulletin.json'),
        ('tide-out-of-scope', 'Kochi me kal tide kya hai?', 'chat-tide.json'),
        ('crosscheck-hinglish', 'Ahmedabad me kal barish ke liye models compare kijiye.', 'chat-crosscheck-hinglish.json'),
    ]
    rows = []
    for name, question, target in journeys:
        packet = call('/api/chat', 'POST', {'question': question}, token)
        (OUT / target).write_text(json.dumps(packet, indent=2, ensure_ascii=False) + chr(10))
        planning = (packet.get('trace') or {}).get('planning') or {}
        rows.append({'name': name, 'question': question, 'status': packet.get('status'),
                     'facts': len(packet.get('facts') or []), 'provider': planning.get('provider'),
                     'adherence': adherence_of(packet),
                     'answer': (packet.get('answer') or '')[:220].replace(chr(10), ' ')})
        print('%-18s %-18s facts=%-3d %s' % (name, packet.get('status'), len(packet.get('facts') or []), planning.get('provider')))
    lines = ['# The repaired shapes, live', '', "Drivers: `scripts/measure_paraphrases.py` (38 variants over 11 shapes, all held) and this file, against a live local server. The measurement is a development set and may be tuned on; it measures planner robustness, not answer quality.", '', '## Measured', '']
    for row in rows:
        lines.append('- **' + row['name'] + '** — ' + row['question'])
        lines.append('  - status: ' + str(row['status']) + ' · planner: ' + str(row['provider']) + ' · facts: ' + str(row['facts']) + ' · language adherence: ' + str(row['adherence']))
        lines.append('  - answer: ' + str(row['answer']))
    lines += ['', '## What this does not establish', '', "- The paraphrase set is a development set written by the same hand as the fixes: holding it is not evidence of generalisation (see docs/54 and docs/56 for sealed measurements).", "- A plan is not an answer, and no answer here was checked against its source by a human.", "- Indic-script support is planned and rendered through the gate, but no native speaker has reviewed any of it, and document coverage in Indian languages remains unmeasured beyond the letterhead count in docs/52.", '']
    (OUT / 'journey.md').write_text(chr(10).join(lines))
    print('written', OUT / 'journey.md')


if __name__ == '__main__':
    main()