"""Live loopback evidence for the conversational front door: the first reading and the receipt.

Run from the repository root:  .venv/bin/python research/reviews/chatbot-20260916/capture_live.py
It starts the real workspace on an ephemeral loopback port, reads the session token from the served
page, and records what /api/chat/preview and /api/chat answered. It writes no conversation of its
own when the local store already holds one: a carried reading is measured against a real stored
conversation rather than a fabricated one. Nothing here is published; the record is local evidence.
"""
import json, re, sys, threading, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import Workspace, make_server  # noqa: E402

QUESTION = 'Will it rain in Ahmedabad tomorrow morning?'
record = {'batch': 'docs/82-chatbot-experience.md', 'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'surface': 'loopback workspace server, real local store', 'checks': [], 'limits': [
              'One machine, one store, one session; this is not national or multi-user acceptance.',
              'The preview is measured as a reading, not as an answer: it carries no value.']}
app = Workspace()
server = make_server(app, 0)
thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
base = 'http://127.0.0.1:' + str(server.server_port)
try:
    html = urllib.request.urlopen(base).read().decode()
    token = re.search(r'name="workspace-token" content="([^"]+)"', html)[1]
    record['checks'].append({'check': 'page_serves_token', 'served': 'workspace-token' in html})

    def call(path, body=None, method='GET'):
        headers = {'X-WeatherGPT-Token': token}
        data = None
        if body is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(body).encode()
        request = urllib.request.Request(base + path, data, headers, method=method)
        began = time.monotonic()
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.load(response)
        return payload, round(time.monotonic() - began, 3)

    ledger, _ = call('/api/conversations')
    record['conversations_held_before'] = ledger['total']

    packet, seconds = call('/api/chat/preview', {'question': QUESTION}, 'POST')
    record['checks'].append({'check': 'preview_for_a_recognised_question', 'seconds': seconds,
                             'schema_version': packet['schema_version'], 'provisional': packet['provisional'],
                             'model_calls': packet['model_calls'], 'basis': packet['reading']['basis'],
                             'places': packet['reading']['places'], 'measures': packet['reading']['measures'],
                             'products': [item['kind'] for item in packet['reading']['products']],
                             'line': packet['reading']['line'],
                             'carries_facts_or_citations': bool(packet.get('facts') or packet.get('citations'))})

    if ledger['conversations']:
        cid = ledger['conversations'][0]['id']
        carried, seconds = call('/api/chat/preview', {'question': 'and tomorrow afternoon?', 'conversation_id': cid}, 'POST')
        record['checks'].append({'check': 'preview_of_a_continuation', 'conversation': cid, 'seconds': seconds,
                                 'basis': carried['reading']['basis'] if carried['reading'] else None,
                                 'line': carried['reading']['line'] if carried['reading'] else None,
                                 'model_calls': carried['model_calls']})
    else:
        answer, seconds = call('/api/chat', {'question': QUESTION}, 'POST')
        record['checks'].append({'check': 'first_turn_answered_to_hold_a_conversation', 'seconds': seconds,
                                 'status': answer['status'], 'conversation_id': answer['conversation_id']})
        carried, seconds = call('/api/chat/preview', {'question': 'and tomorrow afternoon?',
                                                      'conversation_id': answer['conversation_id']}, 'POST')
        record['checks'].append({'check': 'preview_of_a_continuation', 'seconds': seconds,
                                 'basis': carried['reading']['basis'] if carried['reading'] else None,
                                 'line': carried['reading']['line'] if carried['reading'] else None})

    after, _ = call('/api/conversations')
    record['conversations_held_after'] = after['total']
    record['checks'].append({'check': 'previews_added_no_conversation',
                             'before': ledger['total'], 'after': after['total'],
                             'added': after['total'] - ledger['total']})

    progress, _ = call('/api/chat/progress')
    record['checks'].append({'check': 'progress_is_readable_beside_a_preview', 'state': progress['state'],
                             'stages_are_facts_not_progress': progress['stages_are_facts_not_progress']})
finally:
    server.shutdown(); server.server_close(); thread.join(5)

target = Path(__file__).resolve().parent / 'live-http-checks.json'
target.write_text(json.dumps(record, indent=2) + chr(10))
print(json.dumps(record, indent=2))
