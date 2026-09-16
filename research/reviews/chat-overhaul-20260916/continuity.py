"""Measured continuity journeys: does a conversation carry what it should, end to end?

Run from the repository root:  .venv/bin/python research/reviews/chat-overhaul-20260916/continuity.py
Four journeys against the real engine and the configured provider: a bare continuation after a forecast, a
changed part of day, a corrected place, and a clarification answered in a second message. Each turn records what
the engine carried, which planner tier answered, whether the evidence stayed on the same source, and how long
it took. Failures are kept as failures.
"""
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402

STORE = ROOT / 'tmp/chat-continuity.sqlite'
if STORE.exists():
    STORE.unlink()
app = Workspace()
engine = ConversationEngine(app, database=STORE)
record = {'batch': 'docs/83-intelligent-chat-overhaul.md',
          'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'journeys': [], 'limits': [
              'One conversation per journey, one run, one machine: a model may answer differently on another day.',
              'A carried slot is read from the settled plan the engine recorded, not from the answer text alone.']}


def summarise(step, question, packet, seconds, conversation):
    planning = (packet.get('trace') or {}).get('planning') or {}
    plan = packet.get('plan') or {}
    facts = packet.get('facts') or []
    return {'step': step, 'question': question, 'conversation': conversation, 'seconds': seconds,
            'status': packet.get('status'), 'intent': plan.get('intent'),
            'context_action': plan.get('context_action'), 'changed_fields': plan.get('changed_fields'),
            'places': [p.get('name') for p in plan.get('places') or []],
            'window': [plan.get('start_local'), plan.get('end_local')],
            'planner': {'provider': planning.get('provider'), 'tier': planning.get('planner_tier'),
                        'policy': planning.get('planner_policy')},
            'facts': {'count': len(facts),
                      'sources': sorted({f.get('source_id') for f in facts if f.get('source_id')}),
                      'places': sorted({str(f.get('place') or '').split(',')[0].strip() for f in facts if f.get('place')}),
                      'windows': sorted({(f.get('start'), f.get('end')) for f in facts if f.get('start')})[:2]},
            'answer': (packet.get('answer') or '')[:260]}


def ask(question, conversation=None):
    body = {'question': question}
    if conversation:
        body['conversation_id'] = conversation
    began = time.monotonic()
    packet = engine.ask(body)
    return packet, round(time.monotonic() - began, 2)


def journey(name, steps):
    entry = {'journey': name, 'turns': []}
    conversation = None
    for step, question in steps:
        packet, seconds = ask(question, conversation)
        conversation = packet.get('conversation_id') or conversation
        entry['turns'].append(summarise(step, question, packet, seconds, conversation))
        print(json.dumps(entry['turns'][-1], ensure_ascii=False)[:300])
        sys.stdout.flush()
    record['journeys'].append(entry)


journey('a bare continuation after a forecast answer',
        [('first', 'Will it rain in Surat tomorrow morning?'),
         ('continuation', 'and tomorrow afternoon?'),
         ('changed part of day', 'what about the evening?')])
journey('a corrected place',
        [('first', 'Will it rain in Surat tomorrow morning?'),
         ('correction', 'no, I meant Ahmedabad')])
journey('a clarification answered in a second message',
        [('ambiguous', 'Will it rain in Springfield tomorrow morning?'),
         ('answer', 'the one in Gujarat')])
journey('an unrelated greeting mid-conversation',
        [('first', 'Will it rain in Surat tomorrow morning?'),
         ('greeting', 'thanks! and tomorrow?')])

target = Path(__file__).resolve().parent / 'continuity.json'
target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + chr(10))
print('written', target)
