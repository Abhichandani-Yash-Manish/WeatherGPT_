"""Real local-model HTTP journeys. Source failures and repeats remain recorded."""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

out = Path(__file__).parent / sys.argv[1]
out.mkdir(exist_ok=False)
base = 'http://127.0.0.1:8765'
with urllib.request.urlopen(base) as response:
    token = re.search('name="workspace-token" content="([^"]+)"', response.read().decode())[1]
groups = [
    ['Show the published IMD rice advice for Dibrugarh district, Assam.',
     'Show all matching passages, not just three.', 'Explain that.'],
    ['What does the IMD bulletin say about banana in Coimbatore district, Tamil Nadu?'],
    ['What does the IMD bulletin say about rice in Kamrup district, Assam?',
     'Not rice, maize at sowing stage.'],
    ['What does the IMD bulletin say about cotton and groundnut pests in Ahmedabad district, Gujarat?'],
    ['Show rice bulletin advice for Dibrugarh district, Assam. Also show the rain probability there tomorrow evening.'],
    ['Can I spray tomorrow?', 'Nagpur, Maharashtra', 'cotton', 'flowering stage'],
    ['Show banana advice in Surat district, Gujarat.'],
    ['Show rice advice in Madurai district, Tamil Nadu.'],
    ['What does the IMD bulletin say about wheat in Ahmedabad district, Gujarat?'],
]
if len(sys.argv) > 2:
    groups = json.loads(Path(sys.argv[2]).read_text())
summary = []
for group_id, questions in enumerate(groups, 1):
    cid = None
    for turn, question in enumerate(questions, 1):
        payload = {'question': question}
        if cid:
            payload['conversation_id'] = cid
        start = time.monotonic()
        try:
            request = urllib.request.Request(base + '/api/chat', json.dumps(payload).encode(),
                {'Content-Type': 'application/json', 'X-WeatherGPT-Token': token, 'Origin': base})
            with urllib.request.urlopen(request, timeout=120) as response:
                packet = json.load(response)
        except Exception as error:
            packet = {'error': str(error), 'detail': error.read().decode() if hasattr(error, 'read') else ''}
        cid = packet.get('conversation_id', cid)
        name = f'{group_id}-{turn}.json'
        (out / name).write_text(json.dumps(packet, indent=2, ensure_ascii=False))
        row = {'file': name, 'question': question, 'status': packet.get('status'),
               'seconds': round(time.monotonic() - start, 2),
               'crop_passages': sum(p.get('evidence_kind') == 'published_advisory_passage' for p in packet.get('passages', [])),
               'context_sections': sum(p.get('evidence_kind') == 'published_bulletin_context' for p in packet.get('passages', []))}
        summary.append(row)
        (out / 'summary.json').write_text(json.dumps(summary, indent=2))
        print(json.dumps(row), flush=True)
