#!/usr/bin/env python3
"""Save the current IMD district warning attributes edition for a labelled Plan Watch replay.

A replay shows a real change end to end on a day when nothing is changing live. It is only
honest if it replays editions IMD actually published, so this script records the governed
read as it was retrieved: the body, its hash and its retrieval instant. An edition whose
content hash is already recorded is not written twice.

    python3 scripts/capture_warning_edition.py
    python3 scripts/capture_warning_edition.py --out research/implementation/plan-watch-editions

Run it again after IMD publishes a new edition (the layer is updated several times a day);
a replay needs at least two different editions.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from weathergpt_data.product_api import warning_attributes  # noqa: E402
from weathergpt_data.transport import stamp, utcnow  # noqa: E402
from weathergpt_data.workspace import RECORDED_EDITIONS, Workspace  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, default=RECORDED_EDITIONS)
    args = parser.parse_args()
    data, meta = warning_attributes(Workspace().foundation(), refresh=True)
    sha = meta.get('sha256')
    args.out.mkdir(parents=True, exist_ok=True)
    for existing in args.out.glob('edition-*.json'):
        if json.loads(existing.read_text(encoding='utf-8')).get('meta', {}).get('sha256') == sha:
            print('This edition is already recorded as ' + existing.name + '; nothing written.')
            return 0
    captured = utcnow()
    path = args.out / ('edition-' + captured.strftime('%Y%m%dT%H%M%SZ') + '-' + str(sha)[:12] + '.json')
    record = {'schema_version': 'warning-edition-v1', 'captured_at_utc': stamp(captured),
              'meta': {key: meta.get(key) for key in ('sha256', 'retrieved_at_utc', 'url', 'delivery')},
              'source_id': 'S63', 'layer': 'imd:district_warnings_india',
              'note': 'Recorded official product state for a labelled replay. Usage terms are unresolved; do not redistribute.',
              'body': data}
    path.write_text(json.dumps(record, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Recorded ' + str(len(data.get('features') or [])) + ' district features as ' + str(path.relative_to(ROOT)
          if path.is_relative_to(ROOT) else path))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
