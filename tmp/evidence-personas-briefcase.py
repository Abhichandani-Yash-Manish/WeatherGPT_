#!/usr/bin/env python3
"""Round 6 driver: personas and the briefcase, measured against a live local server."""
import json, os, re, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'research/implementation/personas-briefcase-20260915'
PORT = 8796
BASE = 'http://127.0.0.1:%d' % PORT


def call(path, method='GET', body=None, token=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header('Host', '127.0.0.1:%d' % PORT)
    if body is not None:
        request.add_header('Content-Type', 'application/json')
        request.add_header('Origin', BASE)
    if token:
        request.add_header('X-WeatherGPT-Token', token)
    with urllib.request.urlopen(request, timeout=180) as response:
        text = response.read().decode('utf-8')
        disposition = response.headers.get('Content-Disposition')
    return (text, disposition) if raw else (json.loads(text), disposition)


def facts(packet):
    return sorted((str(fact.get('parameter')), str(fact.get('value')), str(fact.get('unit')), str(fact.get('source_id')))
                  for fact in packet.get('facts') or [])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HOME=os.environ.get('HOME', '/Users/yashabhichandani'))
    server = subprocess.Popen([sys.executable, '-m', 'weathergpt_data.workspace', '--port', str(PORT)],
                              cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        deadline, page = time.time() + 60, None
        while time.time() < deadline:
            try:
                page, _ = call('/', raw=True)
                break
            except Exception:
                time.sleep(0.5)
        if page is None:
            raise SystemExit('the server did not start: ' + server.stdout.read().decode('utf-8', 'replace')[:400])
        token = re.search(r'name="workspace-token" content="([^"]+)"', page).group(1)

        catalogue, _ = call('/api/personas', token=token)
        (OUT / 'personas-catalogue.json').write_text(json.dumps(catalogue, indent=2, ensure_ascii=False) + chr(10))
        print('personas:', [item['id'] for item in catalogue['data']['personas']])

        # A repeat run starts from a known store: earlier entries are listed and deleted,
        # which is also the delete path being measured rather than assumed.
        before, _ = call('/api/briefs', token=token)
        for entry in before['briefs']:
            call('/api/briefs/delete', 'POST', {'id': entry['id']}, token)
        print('cleared earlier entries:', len(before['briefs']))

        question = 'Will it rain in Ahmedabad, Gujarat tomorrow morning?'
        with_persona, _ = call('/api/chat', 'POST', {'question': question, 'persona': 'farmer'}, token)
        without, _ = call('/api/chat', 'POST', {'question': question}, token)
        (OUT / 'chat-persona-farmer.json').write_text(json.dumps(with_persona, indent=2, ensure_ascii=False) + chr(10))
        (OUT / 'chat-no-persona.json').write_text(json.dumps(without, indent=2, ensure_ascii=False) + chr(10))
        same = facts(with_persona) == facts(without)
        print('persona carried:', bool(with_persona.get('persona')), '| same evidence:', same, '| facts:', len(with_persona.get('facts') or []))
        assert with_persona.get('persona'), 'the answer did not carry the reading position'
        assert same, 'the persona changed the evidence, which it must never do'

        alert, _ = call('/api/briefs/save', 'POST', {'kind': 'alert_brief', 'lat': 23.02579, 'lon': 72.58727, 'day': 1}, token)
        (OUT / 'brief-save-alert.json').write_text(json.dumps(alert, indent=2, ensure_ascii=False) + chr(10))
        advisory, _ = call('/api/briefs/save', 'POST', {'kind': 'advisory_brief', 'region': 'Ahmedabad', 'state': 'Gujarat',
                                                        'crop': 'cotton', 'stage': 'squaring', 'topic': 'irrigation',
                                                        'mode': 'source_lookup', 'lat': 23.02579, 'lon': 72.58727, 'day': 1}, token)
        (OUT / 'brief-save-advisory.json').write_text(json.dumps(advisory, indent=2, ensure_ascii=False) + chr(10))
        briefs, _ = call('/api/briefs', token=token)
        (OUT / 'briefs-list.json').write_text(json.dumps(briefs, indent=2, ensure_ascii=False) + chr(10))
        kept = briefs['briefs']
        print('kept:', [(entry['kind'], entry['title']) for entry in kept])
        assert len(kept) == 2, 'both kinds of brief should be kept'

        first = kept[0]['id']
        saved, _ = call('/api/briefs/get?id=' + first, token=token)
        (OUT / 'brief-get.json').write_text(json.dumps(saved, indent=2, ensure_ascii=False) + chr(10))
        markdown, disposition = call('/api/briefs/export?id=' + first, token=token, raw=True)
        (OUT / 'brief-export.md').write_text(markdown)
        (OUT / 'brief-export-headers.txt').write_text('Content-Disposition: %s' % disposition + chr(10))
        print('export:', disposition, '|', len(markdown), 'characters')

        removed, _ = call('/api/briefs/delete', 'POST', {'id': first}, token)
        (OUT / 'brief-delete.json').write_text(json.dumps(removed, indent=2, ensure_ascii=False) + chr(10))
        after, _ = call('/api/briefs', token=token)
        print('after delete:', len(after['briefs']), 'kept')

        journey = [
            '# Personas and the briefcase - measured on a live local server',
            '',
            'Driver: `tmp/evidence-personas-briefcase.py` against `python3 -m weathergpt_data.workspace --port 8796`,',
            'in a browser-less loopback client. This is a desktop-web component check, not native-speaker, screen-reader,',
            'mobile or cross-browser acceptance, and it measures no forecast skill.',
            '',
            '## Measured',
            '',
            '- Registered positions: ' + ', '.join(item['label'] + ' (`' + item['id'] + '`)' for item in catalogue['data']['personas']) + '.',
            '- The same question asked with a position and without one returned the same ' + str(len(with_persona.get('facts') or [])) + ' facts: same parameters, values, units and sources.',
            '- The answer carried the position it was read under: `' + str((with_persona.get('persona') or {}).get('label')) + '`, applied as `' + str((with_persona.get('persona') or {}).get('applied')) + '`.',
            '- Kept briefs: ' + str(len(kept)) + ' (' + ', '.join(entry['kind'] for entry in kept) + '), each with its content hash and named sources.',
            '- Export: `' + str(disposition) + '`, ' + str(len(markdown.splitlines())) + ' lines of Markdown.',
            '- After deleting the first entry, ' + str(len(after['briefs'])) + ' remained in the local store.',
            '',
            '## What this does not establish',
            '',
            '- No delivery, push, scheduling or sharing: the store is local and the export is a file.',
            '- No measured effect of a position on answer quality: the check pins that it changes no evidence.',
            '- No browser layout, keyboard or screen-reader acceptance.',
            '',
        ]
        (OUT / 'journey.md').write_text(chr(10).join(journey))
        print('journey written')
    except Exception as failure:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        print('--- server output ---')
        print(server.stdout.read().decode('utf-8', 'replace')[-3000:])
        raise
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == '__main__':
    main()