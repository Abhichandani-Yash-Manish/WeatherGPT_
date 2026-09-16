"""Live journeys for the intelligent-chat batch, against the real provider chain.

Run from the repository root:  .venv/bin/python research/reviews/chat-overhaul-20260916/journeys.py
It uses the workspace's own provider order and the real ingestion store, with conversation state in a
throwaway database so the reader's stored conversations are not touched. What it records is what the
product did: which planner answered, which provider and model, how long it took, and what the turn
produced. Nothing here is published; the record is local evidence.
"""
import json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402

STORE = ROOT / 'tmp/chat-overhaul-journeys.sqlite'
if STORE.exists():
    STORE.unlink()
app = Workspace()
engine = ConversationEngine(app, database=STORE)
record = {'batch': 'docs/83-intelligent-chat-overhaul.md',
          'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'planner_policy': getattr(engine.model, 'policy', None),
          'providers': getattr(engine.model, 'describe', lambda: [])(),
          'turns': [], 'limits': [
              'One machine, one provider order, one run: a model may answer differently on another day.',
              'The weather turn reads the real ingestion store; its collection status is whatever the store held.',
              'Latency is measured once per turn and is not a service level.']}

def summarise(question, packet, seconds, conversation):
    planning = (packet.get('trace') or {}).get('planning') or {}
    generation = (packet.get('trace') or {}).get('generation') or {}
    facts = packet.get('facts') or []
    answer = packet.get('answer') or ''
    return {'question': question, 'conversation': conversation, 'seconds': seconds, 'status': packet.get('status'),
            'answer_basis': packet.get('answer_basis'), 'intent': (packet.get('plan') or {}).get('intent'),
            'planner': {'provider': planning.get('provider'), 'model': planning.get('model'),
                        'policy': planning.get('planner_policy'), 'latency_ms': planning.get('latency_ms'),
                        'failover': planning.get('failover')},
            'generation': {'provider': generation.get('provider'), 'status': generation.get('status'),
                           'authored_by': generation.get('authored_by'),
                           'language_adherence': generation.get('language_adherence'),
                           'repair': (generation.get('repair') or {}).get('reason')},
            'tools': [tool.get('name') for tool in (packet.get('trace') or {}).get('tools') or []],
            'facts': len(facts), 'first_fact': ({k: facts[0].get(k) for k in ['place', 'label', 'value', 'unit', 'source_id']}
                                                if facts else None),
            'quick_replies': len(packet.get('quick_replies') or []),
            'chat_leak_check': engine.chat_reply_problem(answer) if packet.get('answer_basis') == 'conversation' else None,
            'answer': answer[:600]}

def ask(question, conversation=None):
    body = {'question': question}
    if conversation:
        body['conversation_id'] = conversation
    began = time.monotonic()
    packet = engine.ask(body)
    return packet, round(time.monotonic() - began, 2)

for question in ['hello', 'what can you do?', 'what is 17 times 3?', 'नमस्ते']:
    packet, seconds = ask(question)
    record['turns'].append(summarise(question, packet, seconds, packet.get('conversation_id')))
    print(json.dumps(record['turns'][-1], ensure_ascii=False)[:400])
    sys.stdout.flush()

packet, seconds = ask('Will it rain in Surat tomorrow morning?')
weather_conversation = packet.get('conversation_id')
record['turns'].append(summarise('Will it rain in Surat tomorrow morning?', packet, seconds, weather_conversation))
print(json.dumps(record['turns'][-1], ensure_ascii=False)[:400])
sys.stdout.flush()

packet, seconds = ask('thanks!', weather_conversation)
record['turns'].append(summarise('thanks!', packet, seconds, weather_conversation))
print(json.dumps(record['turns'][-1], ensure_ascii=False)[:400])

target = Path(__file__).resolve().parent / 'journeys.json'
target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + chr(10))
print('written', target)
