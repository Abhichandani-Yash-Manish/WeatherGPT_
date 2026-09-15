import json, re, sys, time, urllib.request
from pathlib import Path
ROOT = Path('.').resolve()
OUT = ROOT / 'research/implementation/product-review-20260915'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'http://127.0.0.1:8790'
page = urllib.request.urlopen(BASE + '/', timeout=30).read().decode()
token = re.search(r'name="workspace-token" content="([^"]+)"', page).group(1)
def post(body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + '/api/chat', data=data, method='POST')
    req.add_header('Content-Type', 'application/json'); req.add_header('Origin', BASE)
    req.add_header('Host', '127.0.0.1:8790'); req.add_header('X-WeatherGPT-Token', token)
    began = time.monotonic()
    with urllib.request.urlopen(req, timeout=300) as response:
        packet = json.loads(response.read().decode())
    return packet, round(time.monotonic() - began, 1)
journeys = [
    ('right-now-city', "What's it like right now in Ahmedabad?"),
    ('right-now-shared-name', 'What is it like right now in Kochi?'),
    ('rain-english', 'Will it rain in Ahmedabad, Gujarat tomorrow morning?'),
    ('rain-hindi', 'कल अहमदाबाद, गुजरात में सुबह बारिश होगी?'),
    ('rain-gujarati', 'અમદાવાદમાં આવતીકાલે સવારે વરસાદ થશે?'),
    ('warning', 'Is any warning in force for Patna, Bihar today?'),
    ('advisory', 'What does the Ahmedabad district agromet advisory say for cotton?'),
    ('advisory-decision', 'Kya main Ahmedabad me cotton me irrigation kar sakta hoon is hafte?'),
    ('bulletin', 'What does the latest all India weather bulletin say about heavy rainfall?'),
    ('trend', 'Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.'),
    ('marine', 'What are the wave conditions off Kochi tomorrow?'),
    ('airport', 'What is the current weather at VOBL?'),
    ('not-connected', 'What is the tide at Kochi tomorrow?'),
]
rows = []
for name, question in journeys:
    packet, seconds = post({'question': question})
    planning = (packet.get('trace') or {}).get('planning') or {}
    rows.append({'name': name, 'question': question, 'status': packet.get('status'), 'seconds': seconds,
                 'facts': len(packet.get('facts') or []), 'passages': len(packet.get('passages') or []),
                 'choices': len(packet.get('choices') or []), 'provider': planning.get('provider'),
                 'model': planning.get('model'), 'answer': (packet.get('answer') or '')[:220].replace(chr(10), ' '),
                 'pending_slots': [slot.get('field') for slot in packet.get('pending_slots') or []],
                 'notes': len(packet.get('notes') or [])})
    print('%-22s %-18s facts=%-3d passages=%-3d %ss' % (name, packet.get('status'), len(packet.get('facts') or []), len(packet.get('passages') or []), seconds))
(OUT / 'journeys.json').write_text(json.dumps({'generated_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'journeys': rows}, indent=2, ensure_ascii=False) + chr(10))
answered = [row for row in rows if row['status'] == 'answered']
print('answered', len(answered), 'of', len(rows))