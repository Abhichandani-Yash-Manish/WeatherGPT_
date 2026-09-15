import sys, pathlib
sys.path.insert(0, str(pathlib.Path('.').resolve()))
from weathergpt_data.specialist_tasks import PROFILES
for kind, profile in PROFILES.items():
    print(kind, sorted(profile.keys()))
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.workspace import Workspace
engine = ConversationEngine(Workspace())
p = engine.ask({'question': 'What are the wave conditions off Kochi tomorrow?'})
print('status', p['status'], '| facts', len(p.get('facts') or []), '| choices', len(p.get('choices') or []))
print('answer:', (p.get('answer') or '')[:180].replace(chr(10), ' '))
print('notes:', [n[:150] for n in (p.get('notes') or [])][:3])
print('tools:', [t.get('name') for t in (p.get('trace') or {}).get('tools') or []])