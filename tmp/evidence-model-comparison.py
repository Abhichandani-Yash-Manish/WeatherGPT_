#!/usr/bin/env python3
"""Round 13 driver: a model-vs-model comparison through the rules path, live."""
import json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/implementation/model-comparison-20260915'
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
    rows = []
    for name, question, target in [
        ('compare', 'Compare the models for rainfall in Ahmedabad tomorrow morning.', 'chat-compare-models.json'),
        ('plain', 'Will it rain in Ahmedabad tomorrow morning?', 'chat-plain-rain.json'),
    ]:
        packet = call('/api/chat', 'POST', {'question': question}, token)
        (OUT / target).write_text(json.dumps(packet, indent=2, ensure_ascii=False) + chr(10))
        task = (packet.get('task_results') or [{}])[0]
        planning = (packet.get('trace') or {}).get('planning') or {}
        rows.append({'name': name, 'question': question, 'status': packet.get('status'),
                     'provider': planning.get('provider'), 'model': planning.get('model'),
                     'facts': len(packet.get('facts') or []), 'calculations': len(packet.get('calculations') or []),
                     'crosscheck_text': task.get('comparison_text'),
                     'answer_tail': (packet.get('answer') or '')[-260:].replace(chr(10), ' ')})
        print(name, '->', packet.get('status'), '| provider', planning.get('provider'), '| facts', len(packet.get('facts') or []),
              '| calculations', len(packet.get('calculations') or []), '| comparison:', bool(task.get('comparison_text')))
    lines = ['# Comparing two forecast sources, from the rules path', '',
             'Driver: `tmp/evidence-model-comparison.py` against a live local server. The comparison is between the GFS point',
             'product and the Open-Meteo best-match product for the same point and window; best-match may share GFS upstream, so',
             'agreement is not independent confirmation and no skill, average or confidence score is produced.', '', '## Measured', '']
    for row in rows:
        lines.append('- **' + row['name'] + '** — ' + row['question'])
        lines.append('  - status: ' + str(row['status']) + ' · planner: ' + str(row['provider']) + '/' + str(row['model']) + ' · facts: ' + str(row['facts']) + ' · calculations: ' + str(row['calculations']))
        if row['crosscheck_text']:
            lines.append('  - comparison: ' + str(row['crosscheck_text'])[:400])
        lines.append('  - answer ends: ' + str(row['answer_tail']))
    lines += ['', '## What this does not establish', '',
              '- No skill, accuracy or calibration: the comparison reports two sources for the same window and the difference between them.',
              '- Best-match may share GFS lineage; the caveat travels with the comparison.',
              '- One place and one window were measured, on one morning.', '']
    (OUT / 'journey.md').write_text(chr(10).join(lines))
    print('written', OUT / 'journey.md')


if __name__ == '__main__':
    main()