#!/usr/bin/env python3
"""Report the model providers this workspace can reach, and check the configured one.

    python3 scripts/models.py              providers, availability and the routing order
    python3 scripts/models.py --catalogue  the free models OpenRouter publishes
    python3 scripts/models.py --check      plan two questions through the router and print the trace
    python3 scripts/models.py --probe-free measure the live free catalogue against the curated ranking
    python3 scripts/models.py --set-key    prompt without echo and store the key in local configuration

Read-only except for --probe-free, which records what a live catalogue read observed, and
--set-key, which writes data/runtime/model-config.json at mode 0600. Neither ever prints the
key: the key is entered through getpass, so it also stays out of shell history. --check sends
one planning request, and only to a provider that is configured. No paid model is ever routed.
"""
import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data import providers  # noqa: E402
from weathergpt_data.providers import ModelRouter, OpenRouterClient  # noqa: E402

CORE_QUESTION = 'Will it rain in Ahmedabad, Gujarat tomorrow morning?'
FOLLOW_UP = 'And what about the evening?'
FREE_REGISTRY = ROOT / 'data' / 'registry' / 'openrouter-free-models.json'
# OpenRouter keys are far longer than this; the floor only rejects an empty or mistyped entry.
MIN_KEY_LENGTH = 20


def redact(text, key):
    """A key must not reach a printed line or a registry record, even inside an error message."""
    text = str(text)
    return text.replace(key, '<redacted>') if key else text


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
    choices = providers.free_model_choices()
    for row in choices['refused']:
        print('refused model id: ' + row['model_id'] + ' - ' + row['reason'])
    if not providers.openrouter_key():
        print('next: python3 scripts/models.py --set-key (hidden prompt), then restart the server')
        print('      then: python3 scripts/models.py --probe-free')
    return choices


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


def set_key(reader=None, path=None, provider='openrouter'):
    """Store a provider key in local backend configuration at mode 0600, without echoing it.

    The key arrives through getpass (hidden input, no shell history) and is never printed. An
    empty or clearly mistyped key, an unreadable existing configuration and a missing parent
    directory are all named rather than worked around; other configuration keys are kept.
    """
    provider = str(provider or 'openrouter').strip().lower()
    if provider not in {'openrouter', 'deepseek'}:
        print('refused: unknown provider ' + provider + '. Use openrouter or deepseek.')
        return 2
    field = 'deepseek_api_key' if provider == 'deepseek' else 'openrouter_api_key'
    label = 'DeepSeek API key' if provider == 'deepseek' else 'OpenRouter API key'
    path = Path(path or providers.LOCAL_CONFIG)
    reader = reader or getpass.getpass
    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding='utf-8')) or {}
        except ValueError:
            print('refused: ' + str(path) + ' is not valid JSON. Nothing was written.')
            return 2
        if not isinstance(existing, dict):
            print('refused: ' + str(path) + ' does not hold a JSON object. Nothing was written.')
            return 2
    try:
        key = str(reader(label + ' (hidden, never printed): ') or '').strip()
    except (EOFError, KeyboardInterrupt):
        print('cancelled: nothing was written.')
        return 2
    if len(key) < MIN_KEY_LENGTH:
        print('refused: that entry is ' + str(len(key)) + ' character(s) and ' + label + 's are longer. '
              'Nothing was written.')
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    existing[field] = key
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
        handle.write(json.dumps(existing, indent=2, ensure_ascii=False) + '\n')
    os.chmod(path, 0o600)
    print(provider + ' key stored in ' + str(path) + ' at mode 0600; it was not printed and data/runtime is git-ignored')
    print('next: restart the server (python3 scripts/start_weather.py), then python3 scripts/models.py --check')
    return 0


def read_registry(path=None):
    """The curated free-model ranking as data. Missing or unparsable is reported, not replaced."""
    path = Path(path or FREE_REGISTRY)
    try:
        return path, json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return path, None
    except ValueError as error:
        print('the curated ranking does not parse: ' + str(path) + ' (' + str(error)[:80] + ')')
        return path, None


def record_observation(registry, observation):
    """Replace the availability block and keep earlier states as bounded history, newest first."""
    history = [row for row in (registry.get('availability_history') or []) if isinstance(row, dict)]
    previous = registry.get('availability')
    if isinstance(previous, dict) and previous.get('status') and previous.get('status') != 'not_probed':
        history.insert(0, previous)
    registry['availability'] = observation
    registry['availability_history'] = history[:20]
    return registry


def write_registry(path, registry):
    """Write the registry back in the same shape the rest of data/registry uses."""
    Path(path).write_text(json.dumps(registry, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def fetch_catalogue():
    """The live OpenRouter catalogue ids through the governed adapter, sending the configured key."""
    client = OpenRouterClient(key=providers.openrouter_key(), timeout=30)
    return [row['id'] for row in client.catalogue(with_key=True)]


def probe_free(fetch=None, path=None, now=None):
    """Intersect the curated ranking with the live catalogue and record what was observed.

    With no key the honest answer is 'not configured': the run exits 0, records that state and
    claims nothing about availability. A ranked id the catalogue does not publish is recorded
    missing; ids the catalogue publishes beyond the ranking are recorded, not adopted.
    """
    path, registry = read_registry(path)
    if registry is None:
        print('no curated ranking is available at ' + str(path) + '; there is nothing to intersect')
        print('next: restore data/registry/openrouter-free-models.json, then re-run --probe-free')
        return 1
    key = providers.openrouter_key()
    stamp = (now or datetime.now(timezone.utc)).isoformat(timespec='seconds')
    ranked = [str((entry or {}).get('model_id') or '') for entry in registry.get('models') or []
              if isinstance(entry, dict)]
    observation = {'status': 'not_configured', 'checked_at_utc': stamp, 'key_source': providers.key_source(),
                   'ranked_ids_found': [], 'ranked_ids_missing': [], 'unranked_free_ids_published': [],
                   'reason': ('no OpenRouter key is configured, so availability was not measured and is '
                              'not inferred from the ranking')}
    if not key:
        write_registry(path, record_observation(registry, observation))
        print('OpenRouter key: not configured (' + providers.key_source() + ')')
        print('availability: not measured; ' + str(len(ranked)) + ' ranked free id(s) stay unverified')
        print('recorded in ' + str(path) + ' as status not_configured')
        print('next: python3 scripts/models.py --set-key (hidden prompt), restart the server, re-run --probe-free')
        return 0
    fetch = fetch or fetch_catalogue
    try:
        published = sorted({str(model).strip() for model in fetch() if str(model).strip()})
    except Exception as error:  # noqa: BLE001 - the point is to record the failure, not to hide it
        observation.update(status='probe_failed',
                           reason=redact(type(error).__name__ + ' ' + str(error)[:160], key))
        write_registry(path, record_observation(registry, observation))
        print('probe failed: ' + observation['reason'])
        print('recorded in ' + str(path) + '; the ranking is unchanged and no availability is claimed')
        return 1
    free = [model for model in published if model.endswith(':free')]
    observation.update(status='measured', ranked_ids_found=[model for model in ranked if model in free],
                       ranked_ids_missing=[model for model in ranked if model not in free],
                       unranked_free_ids_published=[model for model in free if model not in ranked])
    write_registry(path, record_observation(registry, observation))
    print('OpenRouter key: configured (' + providers.key_source() + ')')
    print('catalogue: ' + str(len(published)) + ' model(s) published, ' + str(len(free)) + ' of them free')
    print('ranked: ' + str(len(observation['ranked_ids_found'])) + ' found, '
          + str(len(observation['ranked_ids_missing'])) + ' not published')
    for model in observation['ranked_ids_missing']:
        print('  missing: ' + model)
    for model in observation['unranked_free_ids_published']:
        print('  free but unranked: ' + model)
    print('recorded in ' + str(path) + '; a missing id is not routed to without failover')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--catalogue', action='store_true', help='list the models OpenRouter publishes')
    parser.add_argument('--check', action='store_true', help='plan a question through the router')
    parser.add_argument('--probe-free', action='store_true',
                        help='measure the live free catalogue against the curated ranking and record it')
    parser.add_argument('--set-key', nargs='?', const='openrouter', choices=['openrouter', 'deepseek'],
                        help='prompt without echo and store a provider key at mode 0600 (openrouter, or deepseek)')
    parser.add_argument('--json', action='store_true', help='print the provider report as JSON')
    arguments = parser.parse_args()
    if arguments.set_key:
        return set_key(provider=arguments.set_key)
    if arguments.probe_free:
        return probe_free()
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
                          'models_configured': list(providers.free_models()),
                          'models_refused': list(providers.free_model_choices()['refused'])},
                         indent=2, ensure_ascii=False))
        return 0
    show_providers()
    return 0


if __name__ == '__main__':
    sys.exit(main())
