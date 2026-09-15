#!/usr/bin/env python3
"""Round 8 driver: language journeys end to end, and the re-measured ledger."""
import json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/implementation/language-voice-20260915'
BASE = 'http://127.0.0.1:8790'


def call(path, method='GET', body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    if body is not None:
        request.add_header('Content-Type', 'application/json')
        request.add_header('Origin', BASE)
    request.add_header('Host', '127.0.0.1:8790')
    if token:
        request.add_header('X-WeatherGPT-Token', token)
    with urllib.request.urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode('utf-8'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    page = urllib.request.urlopen(BASE + '/', timeout=60).read().decode('utf-8')
    token = re.search(r'name="workspace-token" content="([^"]+)"', page).group(1)
    journeys = [
        ('hi', 'Ahmedabad, Gujarat mein kal subah barish hogi?', 'chat-hi.json'),
        ('gu', 'Ahmedabad, Gujarat ma kale savere varsad thashe?', 'chat-gu.json'),
        ('hi', 'Aurangabad mein kal barish hogi?', 'chat-hi-clarification.json'),
        ('ta', 'Ahmedabad, Gujarat mein kal barish hogi?', 'chat-ta-held.json'),
        ('hi', 'Sultanpur mein kal barish hogi?', 'chat-hi-selection.json'),
        ('hi', 'Ahmedabad district agromet advisory cotton ke liye kya kehta hai?', 'chat-hi-document.json'),
    ]
    summary = []
    for language, question, name in journeys:
        packet = call('/api/chat', 'POST', {'question': question, 'output_language': language}, token)
        (OUT / name).write_text(json.dumps(packet, indent=2, ensure_ascii=False) + chr(10))
        generation = (packet.get('trace') or {}).get('generation') or {}
        language_trace = (packet.get('trace') or {}).get('language') or {}
        facts = packet.get('facts') or []
        summary.append({'language': language, 'question': question, 'status': packet.get('status'),
                        'answer_first_160': (packet.get('answer') or '')[:160], 'facts': len(facts),
                        'adherence': generation.get('language_adherence') or language_trace.get('adherence'),
                        'rendered': generation.get('rendered') if 'rendered' in generation else language_trace.get('rendered'),
                        'selection': language_trace.get('selection'), 'citations': len(packet.get('citations') or []),
                        'choices': len(packet.get('choices') or []), 'notes': [n for n in (packet.get('notes') or []) if 'language' in n.lower()][:2]})
        print(language, packet.get('status'), '| facts', len(facts), '| adherence', summary[-1]['adherence'],
              '| rendered', summary[-1]['rendered'], '| choices', summary[-1]['choices'])
    ledger = json.loads((ROOT / 'data/registry/language-support.json').read_text())
    languages = ledger['languages']
    states = {direction: [code for code, row in languages.items() if (row.get(direction) or {}).get('state') == 'verified']
              for direction in ('write', 'speak', 'hear')}
    failures = {direction: {code: (languages[code].get(direction) or {}).get('reason') for code in languages
                            if (languages[code].get(direction) or {}).get('state') == 'failed'}
                for direction in ('write', 'speak', 'hear')}
    lines = ['# Language and voice: the re-measured ledger, three journeys, and real audio', '',
             'Measured 2026-09-15 UTC on this machine. Ledger: `data/registry/language-support.json`.',
             'Drivers: `tmp/evidence-language-voice.py` against a live local server, and',
             '`python3 scripts/measure_speech_roundtrip.py --languages hi,gu`.',
             'This is a reach and phenomenon measurement. It is not an accuracy, fluency or intelligibility test,',
             'and no native-speaker review of any rendering, transcript or audio has taken place.', '',
             '## The ledger, re-measured', '']
    for direction in ('write', 'speak', 'hear'):
        lines.append('- **' + direction + '**: verified for ' + str(len(states[direction])) + ' of ' + str(len(languages)) +
                     ' registered languages' + (': ' + ', '.join(sorted(states[direction])) if states[direction] else 'none'))
    for direction in ('write', 'speak', 'hear'):
        for code, reason in sorted(failures[direction].items()):
            lines.append('  - ' + direction + ' failed for ' + code + ': ' + str(reason)[:180])
    lines += ['', '## Journeys through the gate', '']
    for row in summary:
        lines.append('- **' + row['language'] + '** — ' + row['question'])
        lines.append('  - status: ' + str(row['status']) + ' · facts: ' + str(row['facts']) + ' · citations: ' + str(row['citations']) + ' · choices offered: ' + str(row['choices']))
        lines.append('  - gate: selection ' + str(row['selection']) + ' · adherence ' + str(row['adherence']) + ' · rendered ' + str(row['rendered']))
        lines.append('  - answer opens: ' + str(row['answer_first_160']).replace(chr(10), ' '))
        for note in row['notes']:
            lines.append('  - note: ' + str(note)[:200])
    lines += ['', '## Real audio, synthesised and transcribed', '']
    speech = json.loads((OUT / 'speech-roundtrip.json').read_text())
    for row in speech.get('languages') or []:
        lines.append('- **' + row['language'] + '** — audio ' + str(row['audio_bytes']) + ' bytes, model ' + str(row['model']) + ', detected ' + str(row['detected_language_code']))
        lines.append('  - place present: ' + str(row['place_present']) + ' · number as digits: ' + str(row['number_as_digits']) + ' · unit present: ' + str(row['unit_present']) + ' · negation present: ' + str(row['negation_marker_present']))
        lines.append('  - transcript: ' + str(row.get('transcript'))[:160])
        lines.append('  - recognition probability: ' + str(row.get('recognition_probability')) + ' (the recogniser own number, never answer or forecast confidence)')
    lines += ['', '## What this does not establish', '',
              '- No accuracy, intelligibility or fluency: the round trip records what came back, not whether it was right.',
              '- No native-speaker review of any rendering, transcript or audio.',
              '- Reach is per language and per direction and can be withdrawn by the provider: a verified row is what one probe at one instant returned.',
              '- A language whose write failed is shipped in the source language with an honest downgrade rather than an unverified rendering; the Tamil journey above is that behaviour, not a silent fallback.',
              '- The journeys are four turns, not a usability study, and no mobile or screen-reader acceptance was measured.', '']
    (OUT / 'language-journeys.md').write_text(chr(10).join(lines))
    print('written', OUT / 'language-journeys.md')


if __name__ == '__main__':
    main()