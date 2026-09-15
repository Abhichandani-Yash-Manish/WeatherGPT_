#!/usr/bin/env python3
"""Start the local workspace, after saying what this machine can actually do.

    python3 scripts/start_weather.py                  # preflight, then serve on 8765
    python3 scripts/start_weather.py --preflight-only # report and exit
    python3 scripts/start_weather.py --json           # the same report as JSON

The engine plans the core question shapes with rules and no model at all, so a missing Ollama or an
unconfigured OpenRouter key is a state to report, not a reason to refuse to start. A blocked check
(a broken registry, an unusable runtime store, a port already in use) exits non-zero: those are
conditions under which the workspace cannot answer truthfully. No key material is ever printed.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data import preflight  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--preflight-only', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--skip-ollama-probe', action='store_true')
    arguments = parser.parse_args()
    report = preflight.report(port=arguments.port, probe_ollama=not arguments.skip_ollama_probe)
    if arguments.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print('WeatherGPT preflight - ' + report['generated_at_utc'])
        for check in report['checks']:
            print('  %-18s %-8s %s' % (check['check'], check['state'], check['detail']))
        print('  not connected: ' + '; '.join(report['not_connected']))
        print('  ' + report['note'])
    if report['blocked']:
        print('Refusing to start: ' + ', '.join(report['blocked']) + '. Fix the blocked check and run again.')
        return 2
    if arguments.preflight_only:
        return 0
    os.chdir(ROOT)
    print('Serving on http://127.0.0.1:%d (loopback only, per-process token). Ctrl-C to stop.' % arguments.port, flush=True)
    os.execv(sys.executable, [sys.executable, '-m', 'weathergpt_data.workspace', '--port', str(arguments.port)])


if __name__ == '__main__':
    sys.exit(main())