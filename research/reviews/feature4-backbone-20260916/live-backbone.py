"""Live check of the merged Feature 4 backbone: watch health, a supervised cycle, the outbox and a 429.

Run from the repository root:  .venv/bin/python research/reviews/feature4-backbone-20260916/live-backbone.py
It serves a throwaway copy of the ingestion store, so the reader's own watches and outbox are untouched, and
records what each endpoint actually answered.
"""
import json, re, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import Workspace, make_server  # noqa: E402

# A directory of this run's own: the watch store, the outbox and the heartbeat file all live beside the
# ingestion store, so a reused copy would carry a previous run's heartbeat into the first reading.
SHOTS = ROOT / 'tmp/feature4-live/ingestion.sqlite'
SHOTS.parent.mkdir(parents=True, exist_ok=True)
import shutil  # noqa: E402
for stale in sorted(SHOTS.parent.glob('*')):
    if stale.name != '.gitkeep':
        stale.unlink()
shutil.copyfile(ROOT / 'data/runtime/ingestion/ingestion.sqlite', SHOTS)

app = Workspace(database=SHOTS)
server = make_server(app, 0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = 'http://127.0.0.1:' + str(server.server_port)
record = {'batch': 'docs/85-feature4-dissemination-backbone.md',
          'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'surface': 'loopback workspace over a throwaway copy of the ingestion store',
          'checks': [], 'limits': [
              'One machine, one store copy, one run; the reader own watches and outbox were not touched.',
              'A synthetic cycle is not a live IMD edition run and not a device delivery.']}
try:
    html = urllib.request.urlopen(base).read().decode()
    token = re.search(r'name="workspace-token" content="([^"]+)"', html)[1]

    def call(path, body=None, method='GET'):
        headers = {'X-WeatherGPT-Token': token}
        data = None
        if body is not None:
            headers['Content-Type'] = 'application/json'
            data = json.dumps(body).encode()
        request = urllib.request.Request(base + path, data, headers, method=method)
        began = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.status, json.load(response), round(time.monotonic() - began, 2)
        except urllib.error.HTTPError as error:
            payload = None
            try:
                payload = json.load(error)
            except ValueError:
                payload = None
            return error.code, payload, round(time.monotonic() - began, 2)

    status, health, seconds = call('/api/watch-health')
    record['checks'].append({'check': 'watch_health_before_any_run', 'http': status, 'seconds': seconds,
                             'schema': health.get('schema_version'), 'mode': health.get('mode'),
                             'heartbeat': health.get('heartbeat'), 'tick': health.get('tick'),
                             'outbox': health.get('outbox'), 'watches': health.get('watches'),
                             'plan_watcher': health.get('plan_watcher'), 'note': health.get('note')})

    status, created, seconds = call('/api/watches/create', {'place': {'name': 'Patna, Bihar', 'latitude': 25.5941,
                                                                     'longitude': 85.1376},
                                                           'hazard': 'heavy rain'}, 'POST')
    record['checks'].append({'check': 'create_a_watch', 'http': status, 'seconds': seconds,
                             'schema': (created or {}).get('schema_version'), 'watch_id': (created or {}).get('id'),
                             'hazard': (created or {}).get('hazard'), 'state': (created or {}).get('state'),
                             'connected': (created or {}).get('connected'), 'detail': (created or {}).get('detail')})

    status, again, _ = call('/api/watches/create', {'place': {'name': 'Patna, Bihar', 'latitude': 25.5941,
                                                              'longitude': 85.1376},
                                                   'hazard': 'heavy rain'}, 'POST')
    total = len(call('/api/watches')[1].get('watches') or [])
    record['checks'].append({'check': 'the_same_watch_is_idempotent', 'http': status,
                             'same_id': bool((again or {}).get('id') and (again or {}).get('id') == created.get('id')),
                             'watches_total': total})

    status, checked, seconds = call('/api/watches/check', {}, 'POST')
    record['checks'].append({'check': 'a_foreground_check_cycle', 'http': status, 'seconds': seconds,
                             'results': len((checked or {}).get('results') or []),
                             'dispatched': len((checked or {}).get('dispatched') or []),
                             'escalated': len((checked or {}).get('escalated') or []),
                             'note': (checked or {}).get('note')})

    status, health2, _ = call('/api/watch-health')
    record['checks'].append({'check': 'watch_health_after_a_run', 'http': status, 'mode': health2.get('mode'),
                             'tick': health2.get('tick'), 'heartbeat_trigger': (health2.get('heartbeat') or {}).get('trigger'),
                             'outbox': health2.get('outbox')})

    status, outbox, _ = call('/api/outbox')
    rows = (outbox or {}).get('notifications') or []
    record['checks'].append({'check': 'outbox_shape_after_the_run', 'http': status, 'schema': (outbox or {}).get('schema_version'),
                             'rows': len(rows), 'states': sorted({row.get('state') for row in rows}),
                             'has_error_class': all('error_class' in row for row in rows) if rows else None})

    codes = []
    for _ in range(62):
        status, payload, _ = call('/api/push/unsubscribe', {'endpoint': 'https://example.invalid/ephemeral'}, 'POST')
        codes.append(status)
    record['checks'].append({'check': 'the_route_budget_answers_429', 'calls': len(codes),
                             'first': codes[0], 'last': codes[-1],
                             'count_429': codes.count(429),
                             'detail': (payload or {}).get('error') if codes[-1] == 429 else None})

    if created.get('id'):
        status, deleted, _ = call('/api/watches/delete', {'id': created['id']}, 'POST')
        record['checks'].append({'check': 'the_check_watch_is_removed_again', 'http': status,
                                 'state': (deleted or {}).get('state'), 'note': (deleted or {}).get('note')})
finally:
    server.shutdown(); server.server_close(); thread.join(5)

target = Path(__file__).resolve().parent / 'live-backbone.json'
target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + chr(10))
for check in record['checks']:
    print(json.dumps(check, ensure_ascii=False)[:300])
print('written', target)
