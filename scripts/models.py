#!/usr/bin/env python3
"""Report the model providers this workspace can reach, and check the configured one.

    python3 scripts/models.py              providers, availability and the routing order
    python3 scripts/models.py --catalogue  the free models OpenRouter publishes (no key needed)
    python3 scripts/models.py --check      plan two questions through the router and print the trace

Read-only. It never prints a key, never writes configuration and never spends a paid model:
--check sends one planning request, and only to a provider that is configured. Put the key in
data/runtime/model-config.json as {"openrouter_api_key": "..."} or in OPENROUTER_API_KEY.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data import providers  # noqa: E402
from weathergpt_data.providers import ModelRouter, OpenRouterClient  # noqa: E402

CORE_QUESTION = 'Will it rain in Ahmedabad, Gujarat tomorrow morning?'
FOLLOW_UP = 'And what about the evening?'


def show_providers():
    router = ModelRouter()
    print('routing order: rules first, then providers in this order')
    print('  %-14s %-28s %s' % ('provider', 'model(s)', 'availability'))
    print('  %-14s %-28s %s' % ('rules', providers.RULE_MODEL, 'always available (no model needed)'))
    for row in router.describe():
        models = ', '.join(row['models']) if row['models'] else (row['model'] or '-')
        state = 'available' if row['available'] else 'unavailable: ' + row['reason']
        print('  %-14s %-28s %s' % (row['provider'], models[:28], state))
    print()
    print('OpenRouter key source: ' + providers.key_source())
    if not providers.openrouter_key():
        print('next: add {"openrouter_api_key": "..."} to data/runtime/model-config.json, or set OPENROUTER_API_KEY')
        print('      then: python3 scripts/models.py --check')


def show_catalogue():
    client = OpenRouterClient(key=providers.openrouter_key() or 'no-key-needed-for-the-catalogue')
    try:
        rows = client.catalogue()
    except Exception as error:  # noqa: BLE001 - the catalogue is a convenience, not a dependency
        print('The OpenRouter catalogue could not be read: ' + type(error).__name__ + ' ' + str(error)[:120])
        print('next: check network access to openrouter.ai; the workspace itself keeps working without it')
        return 1
    free = sorted(row['id'] for row in rows if str(row.get('id', '')).endswith(':free'))
    print(str(len(rows)) + ' models published; ' + str(len(free)) + ' of them free')
    configured = set(providers.free_models())
    for name in free:
        print(('  * ' if name in configured else '    ') + name)
    print()
    print('* = in this workspace\'s routing order. Set WEATHERGPT_MODELS or model-config.json {"models": [...]}')
    return 0


def check_router():
    router = ModelRouter()
    failures = 0
    print('rules path')
    plan, meta = router.plan(CORE_QUESTION, datetime.now(timezone.utc), [])
    print('  %-28s -> %s %s | provider %s' % (CORE_QUESTION[:28], plan['intent'],
                                              [task['kind'] + '/' + task['operation'] for task in plan['tasks']],
                                              meta.get('provider')))
    print('provider path (a follow-up cannot be planned by rules)')
    try:
        plan, meta = router.plan(FOLLOW_UP, datetime.now(timezone.utc), [])
    except Exception as error:  # noqa: BLE001 - the point is to report it
        failures += 1
        print('  %-28s -> failed: %s' % (FOLLOW_UP[:28], str(error)[:160]))
        print('  this is expected when no provider is configured; the rules path above still answers core shapes')
    else:
        print('  %-28s -> %s | provider %s | model %s | %s ms' % (FOLLOW_UP[:28], plan.get('intent'),
                                                                  meta.get('provider'), meta.get('model'),
                                                                  meta.get('latency_ms')))
    return 1 if failures and not providers.openrouter_key() else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--catalogue', action='store_true', help='list the models OpenRouter publishes')
    parser.add_argument('--check', action='store_true', help='plan a question through the router')
    parser.add_argument('--json', action='store_true', help='print the provider report as JSON')
    arguments = parser.parse_args()
    if arguments.catalogue:
        return show_catalogue()
    if arguments.check:
        show_providers()
        print()
        return check_router()
    if arguments.json:
        router = ModelRouter()
        print(json.dumps({'schema_version': 'model-providers-v1', 'rules': providers.RULE_MODEL,
                          'key_source': providers.key_source(), 'providers': router.describe(),
                          'models_configured': list(providers.free_models())}, indent=2, ensure_ascii=False))
        return 0
    show_providers()
    return 0


if __name__ == '__main__':
    sys.exit(main())
