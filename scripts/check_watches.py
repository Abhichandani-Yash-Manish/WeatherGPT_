#!/usr/bin/env python3
"""Check locally registered watches once, in the foreground, and dispatch the outbox.

There is no daemon: this runs once, in the foreground. It runs the official warning
tool for every open watch on demand, enqueues a notification only when the observed
official state changed since the last check, dispatches due outbox rows through their
own channels, and says plainly that a no-match is not an all-clear.

It DOES send web push. This docstring said "no push" and the run summary reported
'local_inbox_only_no_push' while the code called channel_sender, which pushes to every
active subscription for the watch. Corrected 20 September 2026: a machine-readable field
asserting the opposite of what the code does is worse than no field, and this one would
have been read as proof that the notification journey had never run.

    python3 scripts/check_watches.py
"""
import argparse
import json
import sys
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
    parser.add_argument('--json', action='store_true', help='print the raw JSON only')
    args = parser.parse_args()
    workspace = Workspace()
    if workspace.conversation is None:
        workspace.conversation = ConversationEngine(workspace)
    store = workspace.watch_store()
    results = check_due(store, workspace.conversation, now=workspace.clock())
    key_path = store.path.parent / 'push-vapid.json'
    dispatched = dispatch_outbox(store.path, now=workspace.clock(),
                                 send=channel_sender(key_path, store.path))
    escalated = escalate_unacked(store.path, now=workspace.clock())
    notified = sum(1 for row in results if row.get('notification'))
    from weathergpt_data.watches import record_heartbeat
    record_heartbeat(store.path, {'trigger': 'manual-cli',
                                  'stale_after_seconds': 3600,
                                  'checked': len(results),
                                  'notifications_enqueued': notified,
                                  'dispatched': len(dispatched),
                                  'escalated': len(escalated)}, now=workspace.clock())
    channels = {}
    for row in dispatched:
        name = str(row.get('channel') or 'unknown')
        channels[name] = channels.get(name, 0) + 1
    packet = {'schema_version': 'watch-check-run-v1', 'checked': len(results),
              # What was actually dispatched, by channel, rather than a fixed claim about it.
              'delivery_by_channel': channels,
              'web_push_attempted': bool(channels.get('web_push')),
              'no_match_is_not_an_all_clear': True,
              'notifications_enqueued': notified,
              'results': results,
              'dispatched': dispatched,
              'escalated': escalated}
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=1))
    else:
        print('Checked %d local watch(es) in the foreground; %d notification(s) enqueued, %d dispatched, %d escalated. '
              'No daemon is installed.' % (len(results), notified, len(dispatched), len(escalated)))
        if channels:
            print('Dispatched by channel: ' + ', '.join('%s=%d' % pair for pair in sorted(channels.items())))
        for row in results:
            print('%-38s %-22s matched=%s %s' % (row['id'], row['state'], row['matched'], (row.get('detail') or '')[:80]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
