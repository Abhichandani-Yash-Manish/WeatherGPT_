#!/usr/bin/env python3
"""Run watch checks plus outbox dispatch on a foreground interval.

This is a development convenience, not a production daemon: a simple bounded
loop that checks watches, dispatches the outbox, prints one JSON summary per
cycle, and sleeps. Stop it with Ctrl-C. The recorded decision stays "manual
trigger now, scheduler later"; this loop is the manual trigger on repeat.

    python3 scripts/watch_daemon.py --interval 900
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.outbox import dispatch_outbox, escalate_unacked  # noqa: E402
from weathergpt_data.push import channel_sender  # noqa: E402
from weathergpt_data.watches import check_due  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402


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
    cycle = 0
    try:
        while True:
            cycle += 1
            began = time.time()
            results = check_due(store, workspace.conversation, now=workspace.clock())
            dispatched = dispatch_outbox(store.path, now=workspace.clock(), send=send)
            escalated = escalate_unacked(store.path, now=workspace.clock())
            summary = {'schema_version': 'watch-daemon-cycle-v1', 'cycle': cycle,
                       'checked': len(results),
                       'notifications_enqueued': sum(1 for row in results if row.get('notification')),
                       'dispatched': len(dispatched),
                       'escalated': len(escalated),
                       'seconds': round(time.time() - began, 2),
                       'delivery': 'local_inbox_only_no_push'}
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
