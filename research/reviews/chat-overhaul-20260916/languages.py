"""Measured language delivery: what each requested language actually produced.

Run from the repository root:  .venv/bin/python research/reviews/chat-overhaul-20260916/languages.py
It asks one weather question per language through the real engine, with the reader's explicit output
language, and records what came back: the status, the adherence the answer-language tier recorded, whether
the text changed, and the notes the reader would see. Nothing here is published.
"""
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402

QUESTION = 'Will it rain in Surat tomorrow morning?'
LANGUAGES = ['hi', 'gu', 'ta', 'bn', 'mr', 'pa', 'od', 'ur', 'hi-Latn', 'ml']
record = {'batch': 'docs/83-intelligent-chat-overhaul.md',
          'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'question': QUESTION, 'turns': [],
          'limits': ['One question, one place, one window: language delivery is measured here for this shape only.',
                     'The translation service is the configured Sarvam endpoint; a different day or quota may behave differently.']}
app = Workspace()
for code in LANGUAGES:
    store = ROOT / ('tmp/chat-language-' + code.replace('-', '_') + '.sqlite')
    if store.exists():
        store.unlink()
    engine = ConversationEngine(app, database=store)
    began = time.monotonic()
    packet = engine.ask({'question': QUESTION, 'output_language': code})
    generation = (packet.get('trace') or {}).get('generation') or {}
    language_trace = (packet.get('trace') or {}).get('language') or {}
    record['turns'].append({
        'requested': code, 'seconds': round(time.monotonic() - began, 2), 'status': packet.get('status'),
        'answered_language': packet.get('answered_language'),
        'adherence': generation.get('language_adherence'),
        'render_report': generation.get('render_report'),
        'render_failures': generation.get('render_failures'),
        'rendered': bool(packet.get('answered_language')) and packet.get('answered_language') not in (None, 'en'),
        'language_trace': language_trace or None,
        'notes': [note for note in (packet.get('notes') or []) if 'language' in note.lower() or 'script' in note.lower()][:2],
        'answer': (packet.get('answer') or '')[:200]})
    print(json.dumps(record['turns'][-1], ensure_ascii=False)[:400])
    sys.stdout.flush()

target = Path(__file__).resolve().parent / 'languages.json'
target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + chr(10))
print('written', target)
