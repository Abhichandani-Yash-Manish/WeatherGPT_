#!/usr/bin/env python3
"""Restore a local-state backup into a new directory, verifying it first.

    python3 scripts/restore_state.py --backup /path/to/backup --target /path/to/new-directory

Every recorded file must match its manifest size and sha256 before anything is written.
The target must not exist.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.state_backup import restore_state  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--target', type=Path, required=True)
    args = parser.parse_args()
    report = restore_state(args.backup, args.target)
    print(json.dumps(report, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
