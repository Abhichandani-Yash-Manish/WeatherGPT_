#!/usr/bin/env python3
"""Back up the local conversation, watch, ingestion and bulletin-index stores.

    python3 scripts/backup_state.py --output /path/to/new-directory

The output directory must not exist. SQLite files are copied through the backup API;
a manifest of sizes and hashes is written beside them.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.state_backup import backup_state, default_sources  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = backup_state(args.output, default_sources())
    print(json.dumps({'schema_version': manifest['schema_version'], 'files': len(manifest['files']),
                      'output': str(args.output),
                      'note': 'Document bodies and raw evidence blobs are excluded.'}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
