import json, os, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path('.').resolve()))
config = pathlib.Path('data/runtime/model-config.json')
config.parent.mkdir(parents=True, exist_ok=True)
config.write_text(json.dumps({'openrouter_api_key': 'sk-or-v1-' + '0' * 64}))
os.chmod(config, 0o600)
from weathergpt_data.providers import default_model, free_models, key_source
print('key source:', key_source())
print('free models:', free_models()[:3], '...')
client = default_model()
try:
    plan, meta = client.plan('And what about the afternoon?', __import__('datetime').datetime.now(__import__('datetime').timezone.utc), [])
    print('planned by:', meta.get('provider'), '|', meta.get('model'))
    print('failover recorded:', json.dumps(meta.get('failover'))[:200])
    print('plan tasks:', [(t['kind'], t['operation']) for t in plan['tasks']])
except Exception as failure:
    print('raised:', type(failure).__name__, str(failure)[:200])
config.unlink()
print('synthetic key removed; key source now:', key_source())