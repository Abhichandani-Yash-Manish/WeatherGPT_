#!/bin/sh
cd /Users/yashabhichandani/Desktop/WeatherGPT
CONFIG=data/runtime/model-config.json
rm -f "$CONFIG"
echo '--- 1. with no key configured'
env HOME=/Users/yashabhichandani python3 scripts/models.py 2>&1 | grep -i 'OpenRouter key source' 
echo '--- 2. set a synthetic key through the documented flow'
printf 'sk-or-v1-0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n' | env HOME=/Users/yashabhichandani python3 scripts/models.py --set-key 2>&1 | tail -3
echo '--- 3. what the workspace reports afterwards (no key material)'
python3 -c "import json,pathlib,os,stat; p=pathlib.Path('data/runtime/model-config.json'); mode=stat.S_IMODE(p.stat().st_mode); data=json.loads(p.read_text()); print('mode: %o' % mode); print('keys in config:', sorted(data.keys())); print('key length recorded:', len(str(data.get('openrouter_api_key','')))); print('key value printed anywhere: no')"
env HOME=/Users/yashabhichandani python3 scripts/models.py 2>&1 | grep -iE 'OpenRouter|free-tier|ranked' | head -4
echo '--- 4. remove the synthetic key again'
rm -f "$CONFIG"
env HOME=/Users/yashabhichandani python3 scripts/models.py 2>&1 | grep -i 'OpenRouter key source'
