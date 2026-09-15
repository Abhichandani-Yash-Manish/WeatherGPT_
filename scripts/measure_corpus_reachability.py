
"""Record what the published-corpus route answers on this machine, for batch evidence.

    python3 scripts/measure_corpus_reachability.py

Fourteen questions run through the real conversation engine in this process: the rules-first planner, the
governed retrievers and the renderer, against the live local workspace. The record keeps each question's status, its retrieved passages, the words that named the topic and the answer head, so a later run can
be compared with it. It measures no publisher and claims no accuracy: a published document is a record of
what a publisher issued, not a forecast, an observation or a current warning."""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import Workspace
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.transport import utcnow

QUESTIONS = [
 'What does the latest IMD national weather bulletin say about heavy rainfall?',
 "What does today's district agromet bulletin for Nashik say?",
 'Summarise the latest national bulletin.',
 'What changed in the latest state agromet bulletin for Maharashtra?',
 'What does the agromet bulletin for Nashik say about grapes?',
 'Is there any warning in the latest sea area bulletin?',
 'Show me the latest press release.',
 'What does the latest flash flood guidance say for Assam?',
 'What does the coastal bulletin say for the Konkan coast?',
 'What does the latest special advisory say?',
 'What does the district agromet advisory say about cotton irrigation in Ahmedabad?',
 'What does the agromet bulletin for Pune say about onion?',
 'What does the district agromet advisory for Madurai say about banana?',
 'What does the district agromet bulletin for Nowhereville say?',
]
engine = ConversationEngine(Workspace())
rows = []
for q in QUESTIONS:
    started = utcnow().isoformat(); t0 = time.time()
    try:
        r = engine.ask({'question': q})
    except Exception as exc:
        rows.append({'question': q, 'checked_at_utc': started, 'error': type(exc).__name__ + ': ' + str(exc),
                     'seconds': round(time.time() - t0, 2)}); print('ERR', q, exc, flush=True); continue
    coverage = r.get('retrieval_coverage')
    coverage = coverage[0] if isinstance(coverage, list) and coverage else (coverage if isinstance(coverage, dict) else {})
    rows.append({'question': q, 'checked_at_utc': started, 'seconds': round(time.time() - t0, 2),
                 'status': r.get('status'), 'passages': len(r.get('passages') or []),
                 'documents_read': len(r.get('document_evidence') or []),
                 'pending_slots': [slot.get('field') for slot in (r.get('pending_slots') or [])],
                 'match_basis': coverage.get('match_basis'), 'topic_tokens': coverage.get('topic_tokens'),
                 'topic_matched': coverage.get('topic_matched'),
                 'answer': (r.get('answer') or '')[:900]})
    print(json.dumps({k: rows[-1][k] for k in ('question', 'status', 'seconds', 'passages')}, ensure_ascii=False), flush=True)
out = Path('research/implementation/corpus-reachability-20260915')
out.mkdir(parents=True, exist_ok=True)
summary = {'checked_at_utc': utcnow().isoformat(), 'engine': 'local conversation engine, rules-first planner',
           'journeys': len(rows),
           'answered': sum(1 for row in rows if row.get('status') == 'answered'),
           'partial': sum(1 for row in rows if row.get('status') == 'partial'),
           'needs_clarification': sum(1 for row in rows if row.get('status') == 'needs_clarification'),
           'unavailable': sum(1 for row in rows if row.get('status') == 'unavailable'),
           'errors': sum(1 for row in rows if row.get('error')),
           'limits': ['One process, one machine, one instant against live sources.',
                      'A published document is a record of what a publisher issued: these readings are not forecasts, observations or current warnings.',
                      'The district crop questions that reach the indexed-edition fallback say so in the answer.']}
(out / 'journeys.json').write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False) + '\n')
print(json.dumps(summary, indent=1))

