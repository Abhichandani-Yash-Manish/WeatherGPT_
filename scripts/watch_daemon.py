#!/usr/bin/env python3
"""Run watch checks plus outbox dispatch on a supervised foreground interval.

This loop checks watches, dispatches the outbox, escalates unacked rows, prints
one JSON summary per cycle, and records a heartbeat tick the /api/watch-health
route reads. It survives one bad cycle (the failure is recorded, the loop
continues) and skips — rather than crashes on — an overlapping check run held
by another process.

Foreground only: it stops with this terminal (Ctrl-C). For unattended runs,
place it under an OS supervisor (systemd unit, Windows Task Scheduler, or
`docker restart: unless-stopped`): the heartbeat's freshness window is what
proves the supervisor is alive.

    python3 scripts/watch_daemon.py --interval 900
"""
import argparse
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.outbox import dispatch_outbox, escalate_unacked  # noqa: E402
from weathergpt_data.push import channel_sender  # noqa: E402
from weathergpt_data.transport import SourceError  # noqa: E402
from weathergpt_data.watches import check_due, record_heartbeat  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402


def run_cycle(workspace, store, send, cycle=1, interval=900, owner=None, now=None):
    """One supervised check+dispatch cycle. Never raises for run-level faults.

    Returns the summary dict (also recorded as the heartbeat tick). An
    overlapping check run is skipped, not failed; any other cycle error is
    recorded on the summary and the heartbeat so /api/watch-health shows it.
    """
    from weathergpt_data.transport import utcnow
    clock = getattr(workspace, 'clock', None) or utcnow
    now = now or clock()
    owner = owner or ('daemon-%s' % uuid.uuid4().hex[:8])
    began = time.time()
    summary = {'schema_version': 'watch-daemon-cycle-v1', 'cycle': cycle,
               'owner': owner, 'trigger': 'daemon', 'interval_seconds': interval,
               'stale_after_seconds': interval * 2 + 60,
               'checked': 0, 'notifications_enqueued': 0, 'dispatched': 0,
               'escalated': 0, 'skipped': False, 'last_error': None,
               'seconds': 0.0,
               'delivery': 'local_inbox_only_no_push'}
    try:
        try:
            results = check_due(store, workspace.conversation, now=now)
        except SourceError as exc:
            # Another checker owns the lock (a second daemon, a manual run):
            # skip this cycle. The claim/lease layer keeps delivery exact, and
            # the heartbeat proves the skip was observed, not silent.
            summary['skipped'] = True
            summary['last_error'] = 'Overlapping check run skipped: ' + str(exc)
            record_heartbeat(store.path, summary, now=now)
            summary['seconds'] = round(time.time() - began, 2)
            return summary
        dispatched = dispatch_outbox(store.path, now=now, send=send, owner=owner)
        escalated = escalate_unacked(store.path, now=now)
        summary['checked'] = len(results)
        summary['notifications_enqueued'] = sum(1 for row in results if row.get('notification'))
        summary['dispatched'] = len(dispatched)
        summary['escalated'] = len(escalated)
    except Exception as exc:  # one bad cycle must never kill supervision
        summary['last_error'] = 'Cycle failed (%s): %s' % (type(exc).__name__, str(exc)[:200])
    summary['seconds'] = round(time.time() - began, 2)
    record_heartbeat(store.path, summary, now=now)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--interval', type=int, default=900,
                        help='seconds between check cycles (default 900; minimum 60)')
    parser.add_argument('--cycles', type=int, default=0,
                        help='stop after this many cycles (default 0 runs until interrupted)')
    args = parser.parse_args()
    interval = max(60, args.interval)
    workspace = Workspace()
    if workspace.conversation is None:
        workspace.conversation = ConversationEngine(workspace)
    store = workspace.watch_store()
    send = channel_sender(store.path.parent / 'push-vapid.json', store.path)
    owner = 'daemon-%s' % uuid.uuid4().hex[:8]
    cycle = 0
    try:
        while True:
            cycle += 1
            summary = run_cycle(workspace, store, send, cycle=cycle,
                                interval=interval, owner=owner)
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            if args.cycles and cycle >= args.cycles:
                return 0
            time.sleep(interval)
    except KeyboardInterrupt:
        print(json.dumps({'schema_version': 'watch-daemon-cycle-v1', 'stopped_after_cycles': cycle}),
              ensure_ascii=False)
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
