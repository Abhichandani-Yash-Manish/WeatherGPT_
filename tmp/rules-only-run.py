"""Prove the floor: the engine answers with no model provider at all."""
import json, pathlib, sys
sys.path.insert(0, '.')
from weathergpt_data.providers import ModelRouter
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.workspace import Workspace

out = pathlib.Path('research/implementation/provider-layer-20260915')
out.mkdir(parents=True, exist_ok=True)
workspace = Workspace()
engine = ConversationEngine(workspace, model=ModelRouter(clients=[], rules=True))
questions = [
    'Will it rain in Ahmedabad, Gujarat tomorrow morning?',
    'Is there an official warning for Patna, Bihar tomorrow?',
    'What was the annual rainfall in Ahmedabad district, Gujarat in 1990?',
]
record = {'schema_version': 'rules-only-engine-v1', 'providers': [], 'turns': []}
for question in questions:
    try:
        result = engine.ask({'question': question})
        turn = {'question': question, 'status': result.get('status'),
                'plan_intent': (result.get('plan') or {}).get('intent'),
                'tasks': [t['kind'] + '/' + t['operation'] for t in (result.get('plan') or {}).get('tasks', [])],
                'facts': len(result.get('facts') or []),
                'citations': [c.get('source_id') for c in (result.get('citations') or [])][:4],
                'answer_head': (result.get('answer') or '')[:240],
                'planning_meta': (result.get('trace') or {}).get('planning')}
    except Exception as error:  # noqa: BLE001 - a failure is a result here
        turn = {'question': question, 'error': type(error).__name__ + ': ' + str(error)[:200]}
    record['turns'].append(turn)
    print(json.dumps(turn, ensure_ascii=False)[:300])
(out / 'rules-only-engine.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n')
print('wrote', out / 'rules-only-engine.json')
