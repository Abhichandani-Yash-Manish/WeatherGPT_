"""Review-only fresh challenge sample; not a representative benchmark."""
import json, re, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
BASE = 'http://127.0.0.1:8765'
GROUPS = [
    ('forecast_continuity', [
        'For Kochi, Kerala tomorrow from 9 AM to noon, give rain probability, gusts and feels-like temperature.',
        'And from 3 PM to 6 PM?',
        'Compare the rain amount for that same afternoon period with GFS too.',
    ]),
    ('official_warning', ['Are there any current official cyclone warnings that apply to Chennai, Tamil Nadu?']),
    ('dissemination', ['Notify me if an official flood warning is issued for Patna, Bihar tonight.']),
    ('observation', ['What is the observed temperature right now in Mysuru, Karnataka? Name the observing station and measurement time.']),
    ('agriculture', ['Can I irrigate my soybean at flowering tomorrow in Indore district, Madhya Pradesh? Check the district bulletin and tomorrow morning rain forecast.']),
    ('aviation', ['Show the latest METAR and TAF for VOBL and explain what each says.']),
    ('marine', ['What wave heights are forecast off Mangaluru, Karnataka tomorrow morning?']),
    ('river', ['What is the latest observed Brahmaputra water level at Dibrugarh and how far is it below danger level?']),
    ('history', ['Compare annual rainfall in Mysuru district, Karnataka in 2010 and 2020.']),
    ('climate', ['Show the annual mean temperature trend for India from 1981 to 2020 and explain the limits of that trend.']),
    ('hindi', ['भोपाल, मध्य प्रदेश में कल सुबह बारिश की संभावना कितनी है? हिंदी में बताओ।']),
    ('gujarati', ['રાજકોટ, ગુજરાતમાં કાલે સવારે વરસાદની સંભાવના કેટલી છે? ગુજરાતીમાં સમજાવો.']),
    ('district_scope', ['What is the average rainfall forecast across all of Wayanad district, Kerala tomorrow?']),
    ('multi_task', ['For Bhubaneswar, Odisha: tell me tomorrow morning rain probability, current official warnings, observed temperature now, and annual district rainfall in 2010. Answer each part separately.']),
]

def main():
    target = ROOT / 'live-probe'
    target.mkdir(exist_ok=False)
    with urllib.request.urlopen(BASE) as response:
        token = re.search(r'name="workspace-token" content="([^"]+)"', response.read().decode())[1]
    summary = []
    for group, questions in GROUPS:
        cid = None
        for i, question in enumerate(questions, 1):
            body = {'question': question}
            if cid:
                body['conversation_id'] = cid
            start = time.monotonic()
            request = urllib.request.Request(BASE + '/api/chat', json.dumps(body).encode(),
                {'Content-Type': 'application/json', 'X-WeatherGPT-Token': token, 'Origin': BASE})
            try:
                with urllib.request.urlopen(request, timeout=180) as response:
                    result = json.load(response)
            except Exception as exc:
                result = {'error': str(exc)}
                if hasattr(exc, 'read'):
                    result['body'] = exc.read().decode()
            cid = result.get('conversation_id', cid)
            name = f'{group}-{i}.json'
            (target / name).write_text(json.dumps({'question': question, 'result': result}, indent=2, ensure_ascii=False) + '\n')
            row = {'file': name, 'question': question, 'status': result.get('status'),
                'facts': len(result.get('facts', [])), 'passages': len(result.get('passages', [])),
                'seconds': round(time.monotonic()-start, 2), 'error': result.get('error')}
            summary.append(row)
            (target / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
            print(json.dumps(row, ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
