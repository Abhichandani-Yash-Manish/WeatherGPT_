#!/usr/bin/env python3
"""Report whether this machine can run the workspace, and the next action for anything missing.

    python3 scripts/doctor.py
    python3 scripts/doctor.py --json

Read-only: it starts nothing, downloads nothing, writes nothing and changes no runtime
state. A green doctor means the pieces the workspace needs are present on this machine;
it is not operational acceptance, and it says nothing about forecast skill.
"""
import argparse
import importlib
import json
import os
import shutil
import sqlite3
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRIES = ('sources.json', 'source-review.json', 'product-progress.json', 'hardening-progress.json',
              'language-support.json', 'acceptance-benchmark.json', 'answer-policy.json')
CORE_PACKAGES = (('numpy', 'numerical checks and point-in-polygon geography'),
                 ('shapely', 'district warning point-in-polygon checks'),
                 ('sentence_transformers', 'whole-document passage retrieval over the indexed corpus'),
                 ('torch', 'the embedding model the passage index runs on'))
OPTIONAL_PACKAGES = (('pdfplumber', 'published PDF extraction during document intake'),
                     ('pypdf', 'reading the print layout of an exported answer'))
RUNTIME = ROOT / 'data/runtime'


def check_python():
    version = '.'.join(str(part) for part in sys.version_info[:3])
    ok = sys.version_info >= (3, 9)
    return {'id': 'python', 'state': 'ok' if ok else 'fail', 'detail': 'Python ' + version,
            'next_action': '' if ok else 'Install Python 3.9 or newer and run this again.'}


def check_node():
    binary = shutil.which('node')
    return {'id': 'node', 'state': 'ok' if binary else 'warn', 'detail': binary or 'not on PATH',
            'next_action': '' if binary else 'Install Node to run the six component-check suites; the workspace itself runs without it.'}


def check_packages():
    results = []
    for name, purpose in CORE_PACKAGES + OPTIONAL_PACKAGES:
        required = any(name == core for core, _ in CORE_PACKAGES)
        try:
            module = importlib.import_module(name)
            version = getattr(module, '__version__', 'version not stated')
            results.append({'id': 'package:' + name, 'state': 'ok', 'detail': name + ' ' + str(version) + ' for ' + purpose,
                            'next_action': ''})
        except Exception as error:  # noqa: BLE001 - any import failure is the same finding
            results.append({'id': 'package:' + name, 'state': 'fail' if required else 'warn',
                            'detail': name + ' could not be imported (' + type(error).__name__ + ') but is used for ' + purpose,
                            'next_action': 'pip install -r requirements.txt (or the package named above) in the interpreter that runs the workspace.'})
    return results


def check_registries():
    missing, broken = [], []
    for name in REGISTRIES:
        path = ROOT / 'data/registry' / name
        if not path.exists():
            missing.append(name)
            continue
        try:
            json.loads(path.read_text(encoding='utf-8'))
        except ValueError:
            broken.append(name)
    detail = '7 registries present' if not missing and not broken else 'missing ' + str(missing) + ' unparsable ' + str(broken)
    return {'id': 'registries', 'state': 'ok' if not missing and not broken else 'fail', 'detail': detail,
            'next_action': '' if not missing and not broken else 'Restore the named registry file (see data/registry/README.md) before running any batch.'}


def check_corpus():
    path = RUNTIME / 'ingestion/bulletins/bulletin-grid-v2/index.sqlite'
    if not path.exists():
        return {'id': 'corpus', 'state': 'warn', 'detail': 'no indexed passage store at ' + str(path.relative_to(ROOT)),
                'next_action': 'Run the document intake to index published editions; a point forecast does not need the corpus.'}
    try:
        with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as db:
            documents = db.execute('SELECT count(*) FROM documents').fetchone()[0]
            passages = db.execute('SELECT count(*) FROM passages').fetchone()[0]
            families = db.execute('SELECT count(DISTINCT family) FROM passages').fetchone()[0]
    except sqlite3.Error as error:
        return {'id': 'corpus', 'state': 'fail', 'detail': 'the indexed store could not be read: ' + str(error),
                'next_action': 'Re-run the document intake; the store is required for published-document questions.'}
    return {'id': 'corpus', 'state': 'ok' if passages else 'warn',
            'detail': str(documents) + ' documents, ' + str(passages) + ' passages, ' + str(families) + ' families indexed',
            'next_action': '' if passages else 'Index at least one published edition to answer document questions.'}


def check_model():
    base = os.getenv('WEATHERGPT_OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
    model = os.getenv('WEATHERGPT_MODEL', 'qwen3.6:latest')
    from urllib.parse import urlsplit
    parts = urlsplit(base)
    if parts.scheme != 'http' or parts.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        return {'id': 'model', 'state': 'fail', 'detail': 'the configured model endpoint is not loopback: ' + base,
                'next_action': 'Point WEATHERGPT_OLLAMA_URL at a local Ollama endpoint.'}
    try:
        with urllib.request.urlopen(base + '/api/tags', timeout=2) as response:
            installed = [item.get('name') for item in (json.load(response).get('models') or [])]
    except OSError:
        return {'id': 'model', 'state': 'warn', 'detail': 'no local model server answered at ' + base + ' (model ' + model + ')',
                'next_action': 'python3 scripts/start_weather.py starts installed Ollama if it is on PATH.'}
    if model not in installed:
        return {'id': 'model', 'state': 'fail', 'detail': 'the selected model is not installed: ' + model + ' (installed: ' + str(len(installed)) + ')',
                'next_action': 'ollama pull ' + model + ' or set WEATHERGPT_MODEL to one of the installed models.'}
    return {'id': 'model', 'state': 'ok', 'detail': model + ' answered at ' + base, 'next_action': ''}


def check_runtime():
    results = []
    database = RUNTIME / 'ingestion/conversations.sqlite'
    if database.exists():
        try:
            with sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True) as db:
                conversations = db.execute('SELECT count(*) FROM conversations').fetchone()[0]
            results.append({'id': 'runtime:conversations', 'state': 'ok',
                            'detail': str(conversations) + ' stored conversation(s); nothing is published automatically', 'next_action': ''})
        except sqlite3.Error as error:
            results.append({'id': 'runtime:conversations', 'state': 'warn', 'detail': 'the conversation store could not be read: ' + str(error),
                            'next_action': 'Delete or repair data/runtime/ingestion/conversations.sqlite; the workspace recreates it empty.'})
    else:
        results.append({'id': 'runtime:conversations', 'state': 'ok', 'detail': 'no conversation store yet; the first question creates it', 'next_action': ''})
    blobs = RUNTIME / 'documents/blobs'
    count = len(list(blobs.glob('*'))) if blobs.exists() else 0
    results.append({'id': 'runtime:documents', 'state': 'ok' if count else 'warn',
                    'detail': str(count) + ' saved document blob(s) under data/runtime/documents',
                    'next_action': '' if count else 'No document body is saved yet; passages and hashes alone still answer document questions.'})
    return results


def collect():
    checks = [check_python(), check_node()]
    checks += check_packages()
    checks.append(check_registries())
    checks.append(check_corpus())
    checks.append(check_model())
    checks += check_runtime()
    return checks


def summarise(checks):
    counts = {'ok': 0, 'warn': 0, 'fail': 0}
    for check in checks:
        counts[check['state']] = counts.get(check['state'], 0) + 1
    return counts


def exit_code(checks):
    return 1 if any(check['state'] == 'fail' for check in checks) else 0


def report(checks):
    """The whole report, with the readiness claim kept out of it on purpose."""
    return {'schema_version': 'doctor-report-v1', 'checks': checks, 'counts': summarise(checks),
            'operational_ready': False,
            'note': 'Presence of these pieces is not operational acceptance and not a skill measurement.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true', help='print the whole report as JSON')
    arguments = parser.parse_args()
    checks = collect()
    counts = summarise(checks)
    if arguments.json:
        print(json.dumps(report(checks), indent=2, ensure_ascii=False))
    else:
        width = max(len(check['id']) for check in checks)
        for check in checks:
            if check['state'] == 'ok':
                continue
            print('{:<{width}}  {:<4}  {}'.format(check['id'], check['state'].upper(), check['detail'], width=width))
            if check['next_action']:
                print(' ' * (width + 8) + 'next: ' + check['next_action'])
        print('{:<{width}}  {} ok, {} warning(s), {} failure(s)'.format('summary', counts['ok'], counts['warn'], counts['fail'], width=width))
        if not counts['warn'] and not counts['fail']:
            print('Everything this workspace needs is present on this machine. That is not operational acceptance.')
    return exit_code(checks)


if __name__ == '__main__':
    sys.exit(main())
