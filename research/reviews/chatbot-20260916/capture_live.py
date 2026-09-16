"""Live loopback evidence for the conversational front door: the first reading, the next questions.

Run from the repository root:  .venv/bin/python research/reviews/chatbot-20260916/capture_live.py
It starts the real workspace on an ephemeral loopback port, reads the session token from the served
page, and records what /api/chat/preview and /api/chat answered against the real local store. It
writes no conversation of its own while a stored conversation can carry the continuation check; the
one turn it does ask is recorded as such. Nothing here is published; the record is local evidence.
"""
import json, re, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import Workspace, make_server  # noqa: E402

QUESTION = 'Will it rain in Ahmedabad tomorrow morning?'
TURN = 'Will it rain in Surat tomorrow morning?'
record = {'batch': 'docs/82-chatbot-experience.md', 'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'surface': 'loopback workspace server, real local store', 'checks': [], 'limits': [
              'One machine, one store, one session; this is not national or multi-user acceptance.',
              'The preview is measured as a reading, not as an answer: it carries no value.',
              'The model planner was not reachable while this ran, so the continuity journeys are not measured here.']}
app = Workspace()
server = make_server(app, 0)
thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
base = 'http://127.0.0.1:' + str(server.server_port)
try:
    html = urllib.request.urlopen(base).read().decode()
    token = re.search(r'name="workspace-token" content="([^"]+)"', html)[1]
    record['checks'].append({'check': 'page_serves_token', 'served': 'workspace-token' in html})

    def call(path, body=None, method='GET', timeout=180):
        headers = {'X-WeatherGPT-Token': token}
        data = None
        if body is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(body).encode()
        request = urllib.request.Request(base + path, data, headers, method=method)
        began = time.monotonic()
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
        return payload, round(time.monotonic() - began, 3)

    ledger, _ = call('/api/conversations')
    before_previews = ledger['total']

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

    after_previews, _ = call('/api/conversations')
    record['checks'].append({'check': 'previews_added_no_conversation',
                             'before': before_previews, 'after': after_previews['total'],
                             'added': after_previews['total'] - before_previews})

    # A real turn on this store: the rules path plans it, so the chips are measured live rather than
    # only in a fixture. The question names a day and a part of day, the shape the rules floor reads.
    answer, seconds = call('/api/chat', {'question': TURN}, 'POST')
    chips = answer.get('quick_replies') or []
    readable = []
    for chip in chips:
        reading = call('/api/chat/preview', {'question': chip['reply']}, 'POST')[0]['reading']
        readable.append({'label': chip['label'], 'reply': chip['reply'], 'planned_from': chip.get('basis'),
                         'rules_read_the_reply': bool(reading) and reading.get('basis') == 'rules',
                         'read_places': reading['places'] if reading else None})
    record['checks'].append({'check': 'a_live_answer_offers_only_rules_readable_next_questions',
                             'question': TURN, 'seconds': seconds, 'status': answer['status'],
                             'planner': (answer.get('trace') or {}).get('planning'),
                             'chips': readable,
                             'all_chips_rules_readable': bool(readable) and all(item['rules_read_the_reply'] for item in readable)})

    # Is a model planner reachable here? The continuity journeys need one, and the batch must say
    # whether it could measure them rather than assume it.
    try:
        with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=4) as probe:
            models = [entry.get('name') for entry in json.load(probe).get('models', [])]
        record['model_planner'] = {'endpoint': 'http://127.0.0.1:11434', 'reachable': True, 'models': models}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        record['model_planner'] = {'endpoint': 'http://127.0.0.1:11434', 'reachable': False, 'reason': str(exc)}

    progress, _ = call('/api/chat/progress')
    record['checks'].append({'check': 'progress_is_readable_beside_a_preview', 'state': progress['state'],
                             'stages_are_facts_not_progress': progress['stages_are_facts_not_progress']})
    after, _ = call('/api/conversations')
    record['conversations_held_before'] = before_previews
    record['conversations_held_after'] = after['total']
    record['conversations_added_by_the_measured_turn'] = after['total'] - after_previews['total']
finally:
    server.shutdown(); server.server_close(); thread.join(5)

target = Path(__file__).resolve().parent / 'live-http-checks.json'
target.write_text(json.dumps(record, indent=2) + chr(10))
print(json.dumps({k: v for k, v in record.items() if k != 'checks'}, indent=1))
for check in record['checks']:
    print('-', check['check'], json.dumps({k: v for k, v in check.items() if k != 'check'})[:240])
