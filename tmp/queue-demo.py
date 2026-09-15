"""Record the bounded queue's own counters while two turns overlap."""
import json, re, threading, time, urllib.request, pathlib

BASE = 'http://127.0.0.1:8790'
html = urllib.request.urlopen(BASE).read().decode()
token = re.search(r'name="workspace-token" content="([^"]+)"', html)[1]
headers = {'Content-Type': 'application/json', 'X-WeatherGPT-Token': token}
out = pathlib.Path('research/reviews/refinement-20260915/queue-position.json')
samples = []
responses = {}


def ask(name, question):
    body = json.dumps({'question': question}).encode()
    request = urllib.request.Request(BASE + '/api/chat', body, headers)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            responses[name] = {'http': response.status, 'status': json.load(response).get('status')}
    except Exception as error:  # noqa: BLE001 - a refusal is a result here
        responses[name] = {'error': type(error).__name__, 'detail': str(error)[:120]}


threads = [threading.Thread(target=ask, args=('first', 'Will it rain in Kohima, Nagaland tomorrow morning?')),
           threading.Thread(target=ask, args=('second', 'What is the temperature forecast for Imphal, Manipur tomorrow morning?'))]
for index, thread in enumerate(threads):
    thread.start()
    time.sleep(0.4)
start = time.time()
while time.time() - start < 60:
    if not any(thread.is_alive() for thread in threads):
        break
    try:
        request = urllib.request.Request(BASE + '/api/chat/progress', headers={'X-WeatherGPT-Token': token})
        with urllib.request.urlopen(request, timeout=5) as response:
            packet = json.load(response)
        samples.append({'seconds': round(time.time() - start, 1), 'state': packet['state'], 'stage': packet['stage'],
                        'waiting': packet['queue']['waiting'], 'active': packet['queue']['active'],
                        'capacity': packet['queue']['capacity'], 'line': (packet.get('stage_label') or '')})
    except Exception:  # noqa: BLE001
        pass
    time.sleep(0.2)
for thread in threads:
    thread.join(200)
maximum = max((sample['waiting'] for sample in samples), default=0)
record = {'schema_version': 'queue-position-v1', 'samples': len(samples), 'max_waiting_observed': maximum,
          'stages_seen': sorted({sample['stage'] for sample in samples if sample['stage']}),
          'active_observed': max((sample['active'] for sample in samples), default=0),
          'capacity': next((sample['capacity'] for sample in samples if sample['capacity']), None),
          'responses': responses,
          'note': 'The UI refuses a second question while a turn is running; this reading comes from the API, which is what the queue bound protects.'}
out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(record, ensure_ascii=False)[:600])
