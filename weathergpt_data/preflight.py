"""Startup preflight: what this machine can actually do before the server starts.

The launcher used to require Ollama and one specific model, which contradicted the rules-first
floor: the engine plans the core question shapes with no model at all. The preflight reports what
is present, what is absent and what is therefore limited, and it never prints or records key
material - only where a key came from.
"""
import json
import socket
import sqlite3
import sys
from pathlib import Path

from .transport import utcnow

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'startup-preflight-v1'
REGISTRIES = ('sources.json', 'source-review.json', 'hardening-progress.json', 'product-progress.json',
              'language-support.json', 'acceptance-benchmark.json')
NOT_CONNECTED = ('radar and satellite imagery', 'sea-area and coastal bulletins as live products',
                 'flood-extent mapping', 'official warning dissemination of any kind',
                 'delivery, push or scheduled notification outside a foreground command')


def port_free(port, host='127.0.0.1'):
    """True when nothing is listening on the loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, int(port))) != 0


def registries():
    """Every registry parses, or the name that does not is reported."""
    broken, missing = [], []
    for name in REGISTRIES:
        path = ROOT / 'data' / 'registry' / name
        if not path.exists():
            missing.append(name)
            continue
        try:
            json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as failure:
            broken.append({'registry': name, 'why': str(failure)[:200]})
    return {'checked': len(REGISTRIES), 'missing': missing, 'unparsed': broken}


def corpus():
    """How much indexed evidence is on this machine, counted rather than assumed."""
    store = ROOT / 'data' / 'runtime' / 'ingestion' / 'bulletins' / 'bulletin-grid-v2' / 'index.sqlite'
    counts = {'passages': 0, 'documents': 0, 'store': str(store)}
    if not store.exists():
        return dict(counts, present=False)
    try:
        with sqlite3.connect(store) as db:
            counts['passages'] = db.execute('SELECT COUNT(*) FROM passages').fetchone()[0]
            counts['documents'] = db.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    except sqlite3.Error as failure:
        return dict(counts, present=True, error=str(failure)[:200])
    return dict(counts, present=True)


def providers(probe_ollama=True):
    """The rules floor, the local models and the OpenRouter configuration, without key material."""
    from . import providers as layer
    report = {'rules_floor': {'available': True, 'model': layer.RULE_MODEL,
                              'detail': 'the core question shapes are planned deterministically with no model at all'},
              'ollama': {'configured': True, 'reachable': None, 'models': [], 'wanted': None,
                         'wanted_installed': None, 'why': ''},
              'openrouter': {'configured': bool(layer.openrouter_key()), 'key_source': layer.key_source(),
                             'free_models': layer.free_models()}}
    client = layer.OllamaClient()
    report['ollama']['wanted'] = getattr(client, 'model', None)
    if probe_ollama:
        # Service reachability and model availability are reported separately. A reachable
        # service that does not carry the configured model must not be called unreachable.
        try:
            names = client.catalogue()
        except Exception as failure:  # a missing local service is a state, not an error to raise
            report['ollama']['reachable'] = False
            report['ollama']['why'] = str(failure)[:200]
        else:
            report['ollama']['reachable'] = True
            report['ollama']['models'] = sorted(str(name) for name in names)[:40]
            wanted = report['ollama']['wanted']
            installed = wanted in names
            report['ollama']['wanted_installed'] = installed
            if not installed:
                report['ollama']['why'] = ('the service is reachable but the configured model ' + str(wanted) +
                                           ' is not installed (installed: ' +
                                           (', '.join(report['ollama']['models'][:5]) or 'none reported') +
                                           '); set WEATHERGPT_MODEL or run "ollama pull ' + str(wanted) + '"')
    return report


def report(port=8765, probe_ollama=True):
    """One dict a launcher can print and a test can assert on. It holds no secret."""
    from .transport import utcnow as clock
    checks = []
    version = '%d.%d.%d' % sys.version_info[:3]
    checks.append({'check': 'python', 'state': 'ok' if sys.version_info >= (3, 9) else 'blocked', 'detail': version})
    registry = registries()
    state = 'ok' if not registry['missing'] and not registry['unparsed'] else 'blocked'
    checks.append({'check': 'registries', 'state': state,
                   'detail': '%d checked, %d missing, %d unparsed' % (registry['checked'], len(registry['missing']),
                                                                       len(registry['unparsed']))})
    evidence = corpus()
    checks.append({'check': 'document corpus',
                   'state': 'ok' if evidence.get('passages') else ('limited' if evidence.get('present') else 'limited'),
                   'detail': ('%d passages in %d documents' % (evidence.get('passages', 0), evidence.get('documents', 0))
                              if evidence.get('present') else 'no indexed corpus on this machine yet')})
    from .gazetteer import Gazetteer
    try:
        places = Gazetteer()
        places.search('Ahmedabad', 'Gujarat')
        checks.append({'check': 'gazetteer', 'state': 'ok', 'detail': 'a known place resolves; the index is readable'})
    except (OSError, ValueError, KeyError) as failure:
        checks.append({'check': 'gazetteer', 'state': 'limited', 'detail': str(failure)[:200]})
    available = port_free(port)
    checks.append({'check': 'port ' + str(port), 'state': 'ok' if available else 'blocked',
                   'detail': 'free' if available else 'something is already listening on the loopback port'})
    runtime = ROOT / 'data' / 'runtime'
    writable = False
    try:
        runtime.mkdir(parents=True, exist_ok=True)
        probe = runtime / '.preflight-write'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink()
        writable = True
    except OSError as failure:
        checks.append({'check': 'runtime store', 'state': 'blocked', 'detail': str(failure)[:200]})
    if writable:
        checks.append({'check': 'runtime store', 'state': 'ok', 'detail': str(runtime)})
    provider_state = providers(probe_ollama=probe_ollama)
    if provider_state['openrouter']['configured']:
        routed = 'OpenRouter configured (' + provider_state['openrouter']['key_source'] + '), ' + str(len(provider_state['openrouter']['free_models'])) + ' free model id(s) registered'
    else:
        routed = 'no OpenRouter key configured: the rules floor and any local model still answer'
    if provider_state['ollama']['reachable'] and provider_state['ollama']['wanted_installed']:
        local = 'a local Ollama is reachable with model ' + str(provider_state['ollama']['wanted'])
        provider_ok = True
    elif provider_state['ollama']['reachable']:
        local = provider_state['ollama']['why']
        provider_ok = False
    else:
        local = 'no local Ollama was reachable'
        provider_ok = False
    checks.append({'check': 'model providers', 'state': 'ok' if (provider_ok or provider_state['openrouter']['configured']) else 'limited',
                   'detail': local + '; ' + routed})
    blocked = [item['check'] for item in checks if item['state'] == 'blocked']
    return {'schema_version': SCHEMA, 'generated_at_utc': clock().replace(microsecond=0).isoformat(),
            'root': str(ROOT), 'checks': checks, 'blocked': blocked,
            'providers': provider_state, 'registries': registry, 'evidence': evidence,
            'not_connected': list(NOT_CONNECTED),
            'note': ('A preflight reports states, not permissions: a limited state means part of the workspace is thinner, '
                     'not that the workspace may not be used.')}
