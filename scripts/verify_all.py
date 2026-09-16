#!/usr/bin/env python3
"""Run the repeatable local verification: tests, component checks and registry parsing.

    python3 scripts/verify_all.py
    python3 scripts/verify_all.py --skip-tests

This is the clean-machine entry point. It installs nothing and changes no runtime state;
it fails loudly on the first broken step and prints a summary either way.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_SUITES = ['tests/test_charts.js', 'tests/test_viz.js', 'tests/test_views.js', 'tests/test_bulletin_ui.js',
               'tests/test_conversation_ui.js', 'tests/test_suite_ui.js', 'tests/test_voice_ui.js',
               'tests/test_briefcase_ui.js', 'tests/test_workspace_ui.js', 'tests/test_notify_ui.js']
REGISTRIES = ['data/registry/sources.json', 'data/registry/source-review.json', 'data/registry/product-progress.json',
              'data/registry/hardening-progress.json', 'data/registry/language-support.json',
              'data/registry/acceptance-benchmark.json', 'data/registry/answer-policy.json',
              'data/registry/openrouter-free-models.json']


def run(command):
    result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True)
    tail = (result.stdout.strip().splitlines() or [''])[-1]
    if result.returncode:
        print(result.stdout, end='')
        print(result.stderr, end='')
    return result.returncode == 0, tail, result.stderr.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--skip-tests', action='store_true', help='skip pytest and the node component suites')
    args = parser.parse_args()
    steps = []

    python_ok = sys.version_info >= (3, 9)
    steps.append(('python >= 3.9', python_ok, sys.version.split()[0]))
    node = shutil.which('node')
    steps.append(('node available', bool(node), node or 'not found'))
    for name in ('requirements-foundation.txt', 'requirements-bulletins.txt', 'requirements.txt', 'requirements-dev.txt'):
        steps.append((name + ' present', (ROOT / name).exists(), ''))
    for registry in REGISTRIES:
        path = ROOT / registry
        try:
            json.loads(path.read_text())
            steps.append(('parse ' + registry, True, ''))
        except (OSError, ValueError) as error:
            steps.append(('parse ' + registry, False, str(error)[:120]))

    ok, tail, err = run([sys.executable, 'scripts/check_status_drift.py'])
    steps.append(('status drift guard', ok, tail or err))

    if not args.skip_tests:
        ok, tail, err = run([sys.executable, '-m', 'pytest', 'tests/', '-q'])
        steps.append(('python tests', ok, tail or err))
        for suite in NODE_SUITES:
            ok, tail, err = run(['node', suite])
            steps.append(('node ' + Path(suite).name, ok, tail or err))
    ok, tail, err = run([sys.executable, 'scripts/audit_workspace_frontend.py', '--baseline'])
    steps.append(('frontend workspace audit', ok, tail or err))
    # The React build is audited from the built files, since that is what a browser receives. A missing
    # build is a reported skip while the vanilla frontend is still the default.
    ok, tail, err = run([sys.executable, 'scripts/audit_react_build.py'])
    steps.append(('react build audit', ok, tail or err))
    # The surfaces a reader can reach must be served, and the two frontends must agree on them.
    ok, tail, err = run([sys.executable, 'scripts/audit_surface_registry.py'])
    steps.append(('surface registry audit', ok, tail or err))
    # A ported check has to be named in the ledger, and every named test has to exist in its spec. This
    # reads the vanilla suites and the React specs; a missing React build does not affect it.
    ok, tail, err = run([sys.executable, 'scripts/audit_check_port.py'])
    steps.append(('component check port ledger', ok, tail or err))

    width = max(len(name) for name, _, _ in steps) + 2
    for name, ok, detail in steps:
        print('%-*s %s %s' % (width, name, 'PASS' if ok else 'FAIL', detail))
    failed = [name for name, ok, _ in steps if not ok]
    print('')
    print('%d step(s), %d failed%s' % (len(steps), len(failed), (': ' + ', '.join(failed)) if failed else ''))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
