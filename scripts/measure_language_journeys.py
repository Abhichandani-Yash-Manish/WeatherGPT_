
"""Record what the engine answers when the day and part words are in the question's own script.

    python3 scripts/measure_language_journeys.py

Eight questions, one per language, through the real conversation engine in this process: the rules-first
planner, the governed retrievers and the renderer. Each row keeps the status, the planned window, the
assumptions and the answer head, so a later run can be compared with it. It measures no publisher and
no translation quality: a model forecast for a named point is not an observation, a district average or
an official warning, and no fluent review has taken place.
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import Workspace
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.transport import utcnow

QUESTIONS = [
 ('gu', 'કલ અમદાવાદ, ગુજરાતમાં વરસાદ પડશે?'),
 ('hi', 'कल सुबह वडोदरा, गुजरात में मौसम कैसा रहेगा?'),
 ('kn', 'ನಾಳೆ ಬೆಳಿಗ್ಗೆ ಅಹಮದಾಬಾದ್‌ನಲ್ಲಿ ಮಳೆ ಬರುತ್ತದೆಯೇ?'),
 ('ta', 'நாளை காலை அகமதாபாத்தில் மழை பெய்யுமா?'),
 ('bn', 'কাল সকালে কলকাতায় বৃষ্টি হবে?'),
 ('ur', 'آج شام دلی میں بارش ہوگی؟'),
 ('mr', 'उद्या सकाळी पुण्यात पाऊस पडेल का?'),
 ('en', 'Will it rain in the morning in Ahmedabad?'),
]
engine = ConversationEngine(Workspace())
rows = []
for code, question in QUESTIONS:
    started = utcnow().isoformat(); t0 = time.time()
    try:
        r = engine.ask({'question': question, 'output_language': code})
    except Exception as exc:
        rows.append({'language': code, 'question': question, 'checked_at_utc': started,
                     'error': type(exc).__name__ + ': ' + str(exc), 'seconds': round(time.time() - t0, 2)})
        print('ERR', code, exc, flush=True); continue
    task = ((r.get('plan') or {}).get('tasks') or [{}])[0]
    rows.append({'language': code, 'question': question, 'checked_at_utc': started,
                 'seconds': round(time.time() - t0, 2), 'status': r.get('status'),
                 'window': {'start_local': task.get('start_local'), 'end_local': task.get('end_local')},
                 'assumptions': (r.get('plan') or {}).get('assumptions'),
                 'facts': len(r.get('facts') or []),
                 'answer': (r.get('answer') or '')[:300]})
    print(json.dumps({k: rows[-1][k] for k in ('language', 'status', 'window', 'facts', 'seconds')}, ensure_ascii=False), flush=True)
out = Path('research/implementation/language-time-reads-20260915/journeys.json')
summary = {'checked_at_utc': utcnow().isoformat(), 'journeys': len(rows),
           'answered': sum(1 for row in rows if row.get('status') in {'answered', 'partial'}),
           'with_a_window': sum(1 for row in rows if (row.get('window') or {}).get('start_local')),
           'errors': sum(1 for row in rows if row.get('error')),
           'limits': ['One process, one machine, one instant against live sources.',
                      'A model forecast for a named point, not an observation, district average or official warning.',
                      'No fluent review: these record which window was planned and whether a task answered, not whether the translation reads well.']}
out.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False) + '\n')
print(json.dumps(summary, indent=1, ensure_ascii=False))

