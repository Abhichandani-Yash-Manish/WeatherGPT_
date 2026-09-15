#!/usr/bin/env python3
"""Check locally registered watches once, in the foreground.

There is no daemon and no push. This script runs the official warning tool for every
open watch on demand, records the outcome in the local watch store, and says plainly
that a no-match is not an all-clear.

    python3 scripts/check_watches.py
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.watches import check_due  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true', help='print the raw JSON only')
    args = parser.parse_args()
    workspace = Workspace()
    if workspace.conversation is None:
        workspace.conversation = ConversationEngine(workspace)
    results = check_due(workspace.watch_store(), workspace.conversation, now=workspace.clock())
    packet = {'schema_version': 'watch-check-run-v1', 'checked': len(results),
              'delivery': 'local_inbox_only_no_push',
              'no_match_is_not_an_all_clear': True,
              'results': results}
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=1))
    else:
        print('Checked %d local watch(es) in the foreground. No daemon or push is installed.' % len(results))
        for row in results:
            print('%-38s %-22s matched=%s %s' % (row['id'], row['state'], row['matched'], (row.get('detail') or '')[:80]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
