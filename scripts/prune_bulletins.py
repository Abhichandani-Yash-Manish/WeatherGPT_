#!/usr/bin/env python3
"""Prune source document bodies past the retention window, keeping the evidence.

What goes: the cached PDF and HTML bodies in the document store, once their
recorded retrieval is older than the window.

What stays, permanently: every extracted passage, every document hash, every
publication manifest and every per-day intake manifest. A pruned document is
still indexed, still citable and still answerable from its passages; only its
body stops being servable, and /api/documents/<sha> then answers 410 saying so
rather than 404.

Nothing here touches a failure record. Failures are kept so a later run can see
what went wrong.

    python3 scripts/prune_bulletins.py                  # report what is prunable
    python3 scripts/prune_bulletins.py --apply          # delete those bodies
    python3 scripts/prune_bulletins.py --days 14 --apply
"""
import argparse
import json
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.transport import parsed, stamp, utcnow

DEFAULT_STORE = ROOT / 'data' / 'runtime' / 'documents'
RETENTION_DAYS = 7


def store_label(store):
    try:
        return str(Path(store).relative_to(ROOT))
    except ValueError:
        return str(store)


def survey(store, days, now=None):
    """Classify every cached body as retained or prunable, by its recorded retrieval."""
    now = now or utcnow()
    horizon = now - timedelta(days=days)
    cache = store / 'cache'
    retained, prunable, unreadable = [], [], []
    referenced = {}
    for entry in sorted(cache.glob('*.json')) if cache.exists() else []:
        try:
            index = json.loads(entry.read_text())
            retrieved = parsed(index['retrieved_at_utc'])
            blob = store / index['blob']
        except (ValueError, TypeError, KeyError, OSError) as error:
            unreadable.append({'cache_entry': entry.name, 'error': str(error)})
            continue
        item = {'sha256': index.get('sha256'), 'source_id': index.get('source_id'), 'url': index.get('url'),
                'retrieved_at_utc': index['retrieved_at_utc'], 'blob': index['blob'],
                'bytes': blob.stat().st_size if blob.exists() else 0, 'body_present': blob.exists(),
                'cache_entry': entry.name}
        # One body can serve several request identities; the newest retrieval wins.
        previous = referenced.get(index['blob'])
        if previous is None or parsed(previous['retrieved_at_utc']) < retrieved:
            referenced[index['blob']] = item
        (retained if retrieved >= horizon else prunable).append(item)
    still_wanted = {blob for blob, item in referenced.items() if parsed(item['retrieved_at_utc']) >= horizon}
    prunable = [item for item in prunable if item['blob'] not in still_wanted and item['body_present']]
    orphans = []
    for blob in sorted((store / 'blobs').glob('*.bin')) if (store / 'blobs').exists() else []:
        if not any(str(Path('blobs') / blob.name) == item['blob'] for item in referenced.values()):
            orphans.append({'blob': str(Path('blobs') / blob.name), 'bytes': blob.stat().st_size,
                            'note': 'No cache entry refers to this body.'})
    return {'checked_at_utc': stamp(now), 'retention_days': days, 'horizon_utc': stamp(horizon),
            'store': store_label(store), 'retained': retained, 'prunable': prunable,
            'unreadable_cache_entries': unreadable, 'unreferenced_bodies': orphans}


def prune(store, report, apply=False):
    removed, freed, failures = [], 0, []
    seen = set()
    for item in report['prunable']:
        if item['blob'] in seen:
            continue
        seen.add(item['blob'])
        path = store / item['blob']
        if not path.exists():
            continue
        size = path.stat().st_size
        if apply:
            try:
                path.unlink()
            except OSError as error:
                failures.append({'blob': item['blob'], 'error': str(error)})
                continue
        removed.append({'blob': item['blob'], 'sha256': item['sha256'], 'bytes': size,
                        'retrieved_at_utc': item['retrieved_at_utc']})
        freed += size
    return {'applied': apply, 'bodies_removed': len(removed), 'bytes_freed': freed,
            'removals': removed, 'failures': failures,
            'kept': ('passages, document hashes, publication manifests and per-day intake manifests '
                     'are retained permanently and are not touched by this script')}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--store', default=str(DEFAULT_STORE))
    parser.add_argument('--days', type=int, default=RETENTION_DAYS)
    parser.add_argument('--apply', action='store_true', help='delete the prunable bodies (otherwise report only)')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()
    if args.days < 1:
        parser.error('a retention window of less than one day is not supported')
    store = Path(args.store)
    if not store.exists():
        parser.error('no document store at ' + str(store))
    report = survey(store, args.days)
    result = prune(store, report, apply=args.apply)
    summary = {'store': report['store'], 'retention_days': args.days, 'horizon_utc': report['horizon_utc'],
               'bodies_retained': sum(1 for i in report['retained'] if i['body_present']),
               'bodies_prunable': result['bodies_removed'], 'bytes_freed' if args.apply else 'bytes_reclaimable':
                   result['bytes_freed'], 'applied': args.apply,
               'unreferenced_bodies': len(report['unreferenced_bodies']),
               'unreadable_cache_entries': len(report['unreadable_cache_entries']),
               'kept': result['kept'], 'failures': result['failures']}
    print(json.dumps({**summary, **({'removals': result['removals']} if args.verbose else {})},
                     indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
