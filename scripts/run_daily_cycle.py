#!/usr/bin/env python3
"""Run one bounded, foreground daily cycle: documents, watches, prune report, health.

No daemon, scheduler, subscription or background process is installed. Every step is a
bounded CLI invocation and the cycle stops on the first failure. The recorded decision
stays "manual trigger now, scheduler later": this is the manual trigger's one command.

    python3 scripts/run_daily_cycle.py --families national_bulletin
    python3 scripts/run_daily_cycle.py --district-limit 25 --apply-prune
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def step(name, command, timeout=1800):
    began = time.time()
    try:
        result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
        ok = result.returncode == 0
        tail = (result.stdout.strip().splitlines() or [''])[-1][:200]
        error = result.stderr.strip()[-200:]
    except subprocess.TimeoutExpired:
        ok, tail, error = False, 'timed out after %ss' % timeout, ''
    return {'step': name, 'ok': ok, 'seconds': round(time.time() - began, 2), 'tail': tail, 'error': error}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--families', action='append', default=None,
                        help='document families to run; default runs every registered family')
    parser.add_argument('--district-limit', type=int, default=0,
                        help='also sweep this many queued district targets (0 skips the sweep)')
    parser.add_argument('--skip-documents', action='store_true')
    parser.add_argument('--skip-watches', action='store_true')
    parser.add_argument('--apply-prune', action='store_true', help='delete prunable document bodies instead of reporting only')
    args = parser.parse_args()

    steps = []
    if not args.skip_documents:
        command = [sys.executable, 'scripts/ingest_documents.py', 'run']
        if args.families:
            for family in args.families:
                command += ['--family', family]
        else:
            command += ['--all']
        steps.append(step('documents', command))
    if args.district_limit:
        steps.append(step('district sweep', [sys.executable, 'scripts/ingest_documents.py', 'sweep',
                                             '--limit', str(args.district_limit)]))
    if not args.skip_watches:
        steps.append(step('watch check', [sys.executable, 'scripts/check_watches.py', '--json'], timeout=600))
    steps.append(step('retention report', [sys.executable, 'scripts/prune_bulletins.py'] + (['--apply'] if args.apply_prune else [])))
    steps.append(step('health', [sys.executable, '-c',
                                 'from weathergpt_data.workspace import Workspace; import json; '
                                 'print(json.dumps(Workspace().health())[:400])'], timeout=120))
    summary = {'schema_version': 'daily-cycle-v1', 'foreground_only': True, 'daemon_installed': False,
               'scheduler_decision': 'manual_trigger_now_scheduler_later',
               'document_families': args.families or 'all registered', 'district_sweep_limit': args.district_limit,
               'prune_applied': args.apply_prune, 'steps': steps, 'ok': all(item['ok'] for item in steps)}
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0 if summary['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
