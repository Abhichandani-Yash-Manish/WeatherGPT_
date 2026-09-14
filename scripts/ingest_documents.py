#!/usr/bin/env python3
"""Explicit bounded daily document intake; never installs a recurring scheduler.

Each run discovers the registered document addresses for a family, verifies the
printed issue evidence, indexes whole-document passages and appends a per-day
manifest. A reachable document is never reported as a current one.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.document_ingest import (DISTRICT_OUTCOMES, DOCUMENT_EXTRACTION_VERSION, FAMILIES,
                                             district_targets, ingest, ingest_district)
from weathergpt_data.transport import Store, stamp, utcnow
from weathergpt_data.bulletin_index import BulletinIndex, EXTRACTION_VERSION

IST = ZoneInfo('Asia/Kolkata')
DEFAULT_STORE = ROOT / 'data' / 'runtime' / 'documents'
DEFAULT_RUNTIME = ROOT / 'data' / 'runtime' / 'ingestion'
DEFAULT_MANIFEST = ROOT / 'data' / 'processed' / 'bulletins'
RETENTION_DAYS = 7
FREE_SPACE_FLOOR_BYTES = 5 * 1024 ** 3
FLUSH_EVERY = 20


def free_space(path):
    import shutil
    path = Path(path)
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free


def sweep_manifest(day):
    path = manifest_path(day)
    if path.exists():
        return json.loads(path.read_text())
    return {'schema_version': 'document-intake-day-v1', 'day': day, 'runs': [], 'documents': [], 'rejected': []}


def write_sweep(day, document):
    path = manifest_path(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False, sort_keys=True) + chr(10), encoding='utf-8')
    return path


class SweepLock:
    """One sweep at a time. Two concurrent sweeps would each hold the day manifest in
    memory and overwrite the other's recorded targets, losing work that was really done."""

    def __init__(self, path):
        self.path = Path(path)
        self.handle = None

    def __enter__(self):
        import fcntl
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open('a')
        try:
            fcntl.flock(self.handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.handle.close()
            raise SystemExit('Another sweep is already running (lock: %s). Wait for it or stop it first.' % self.path)
        return self

    def __exit__(self, *exception):
        import fcntl
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        self.handle.close()
        return False


def run_district_sweep(store_root, runtime_root, targets=None, limit=None, state=None,
                       recheck=False, retry_failed=False, fetch_ttl=0, byte_budget=None):
    """Sweep the district agromet family. Resumable, idempotent and honest about where it stopped.

    The publisher offers no conditional request (measured 2026-09-14, evidence
    research/discovery/evidence/district-change-detection-20260914T191404Z), so every
    target is downloaded and hashed. An unchanged body skips extraction only.
    """
    from weathergpt_data.bulletin_index import BulletinIndex
    from weathergpt_data.transport import Store
    import time
    store = Store(Path(store_root))
    index = BulletinIndex(Path(runtime_root) / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite')
    listed, directory = district_targets(ROOT)
    lock = SweepLock(Path(runtime_root) / 'district-sweep.lock')
    if state:
        listed = [t for t in listed if t['state'].lower() == state.lower()]
        if not listed:
            raise SystemExit('No listed district for source state ' + state)
    if targets:
        wanted = {t.lower() for t in targets}
        listed = [t for t in listed if t['district'].lower() in wanted]
    started = utcnow()
    day = started.astimezone(IST).date().isoformat()
    held = lock.__enter__()
    document = sweep_manifest(day)
    sweep = document.get('district_sweep')
    if not sweep:
        sweep = {'family': 'district_agromet', 'source_id': 'S57', 'directory': directory,
                 'extraction_version': DOCUMENT_EXTRACTION_VERSION, 'outcome_vocabulary': DISTRICT_OUTCOMES,
                 'change_detection': {'conditional_requests': 'not_available',
                                      'evidence': 'research/discovery/evidence/district-change-detection-20260914T191404Z',
                                      'signal': 'sha256 of the downloaded body against the recorded head'},
                 'passes': [], 'targets': {}}
        document['district_sweep'] = sweep
    already = sweep['targets']
    if retry_failed:
        # Only the districts whose recorded outcome was an error. A held layout and a
        # publisher's 'not issued' are answers, not failures, so retrying them would
        # re-download the whole corpus to learn nothing new.
        outstanding = [t for t in listed if (already.get(t['district']) or {}).get('outcome') == 'failed']
    else:
        outstanding = [t for t in listed if recheck or t['district'] not in already]
    recorded_today = len(listed) - len(outstanding)
    queue = outstanding[:limit] if limit else outstanding
    free = free_space(store_root)
    if free < FREE_SPACE_FLOOR_BYTES:
        raise SystemExit('Refusing to sweep: %.1f GB free is below the %.1f GB floor. Prune document bodies first.'
                         % (free / 1024 ** 3, FREE_SPACE_FLOOR_BYTES / 1024 ** 3))
    entry = {'started_at_utc': stamp(started), 'listed': len(listed), 'queued': len(queue),
             'mode': 'retry_failed' if retry_failed else ('recheck_all' if recheck else 'resume'),
             'already_recorded_today': recorded_today, 'deferred_by_limit': len(outstanding) - len(queue),
             'free_bytes_at_start': free,
             'counts': {k: 0 for k in DISTRICT_OUTCOMES}, 'bytes_downloaded': 0, 'passages_indexed': 0,
             'quarantined_pages': 0, 'stopped_at': None}
    sweep['passes'].append(entry)
    clock = time.time()
    position, target = 0, None
    try:
        for position, target in enumerate(queue):
            if byte_budget and entry['bytes_downloaded'] >= byte_budget:
                entry['stopped_at'] = {'position': position, 'of': len(queue), 'district': target['district'],
                                       'reason': 'byte budget for this pass reached'}
                break
            if free_space(store_root) < FREE_SPACE_FLOOR_BYTES:
                entry['stopped_at'] = {'position': position, 'of': len(queue), 'district': target['district'],
                                       'reason': 'free space fell below the floor'}
                break
            record = ingest_district(store, index, target['state'], target['district'],
                                     now=utcnow(), fetch_ttl=fetch_ttl)
            # The sweep records the family, its source and the outcome vocabulary once.
            # Repeating them on all 698 rows adds nothing a reader cannot look up.
            already[target['district']] = {k: v for k, v in record.items()
                                           if k not in ('outcome_meaning', 'family', 'source_id')}
            entry['counts'][record['outcome']] += 1
            entry['bytes_downloaded'] += record.get('bytes') or 0
            entry['passages_indexed'] += record.get('passages') or 0
            entry['quarantined_pages'] += record.get('quarantined_pages') or 0
            if (position + 1) % FLUSH_EVERY == 0:
                entry['elapsed_s'] = round(time.time() - clock, 1)
                write_sweep(day, document)
    except KeyboardInterrupt:
        entry['stopped_at'] = {'position': position, 'of': len(queue),
                               'district': target['district'] if target else None,
                               'reason': 'interrupted by the operator'}
    entry['elapsed_s'] = round(time.time() - clock, 1)
    entry['finished_at_utc'] = stamp(utcnow())
    entry['completed'] = entry['stopped_at'] is None
    path = write_sweep(day, document)
    held.__exit__(None, None, None)
    return {'day': day, 'manifest': str(path.relative_to(ROOT)), 'pass': entry,
            'recorded_targets': len(already), 'listed_targets': len(listed)}



def manifest_path(day):
    return DEFAULT_MANIFEST / day / 'manifest.json'


def write_manifest(day, entry):
    path = manifest_path(day)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = json.loads(path.read_text()) if path.exists() else {'schema_version': 'document-intake-day-v1', 'day': day, 'runs': [], 'documents': [], 'rejected': []}
    document['runs'].append(entry)
    known = {d['sha256'] for d in document['documents']}
    for accepted in entry['accepted']:
        if accepted['sha256'] in known:
            continue
        record = {k: accepted[k] for k in ('sha256', 'url', 'family', 'source_id', 'pages', 'passages', 'bytes') if k in accepted}
        record.update({k: accepted.get(k) for k in ('issue_date', 'issue_date_basis', 'currency', 'quarantined_pages', 'blob')})
        record['retention'] = {'body_retained_until': None, 'policy': 'document bodies are pruned after %d days; passages and this manifest remain' % RETENTION_DAYS}
        record['first_seen_at_utc'] = entry['started_at_utc']
        document['documents'].append(record)
        known.add(accepted['sha256'])
    for rejected in entry['rejected']:
        document['rejected'].append({**rejected, 'family': entry['family'], 'at_utc': entry['started_at_utc']})
    path.write_text(json.dumps(document, indent=1, ensure_ascii=False, sort_keys=True) + chr(10), encoding='utf-8')
    return path


def run_families(names, store_root, runtime_root=DEFAULT_RUNTIME):
    store = Store(store_root)
    reports = []
    for name in names:
        started = utcnow()
        report = ingest(store, runtime_root, name, now=started)
        report['started_at_utc'] = stamp(started)
        day = started.astimezone(IST).date().isoformat()
        if report['accepted']:
            for accepted in report['accepted']:
                accepted['family'] = name
            path = write_manifest(day, report)
            report['manifest'] = str(path.relative_to(ROOT))
        reports.append(report)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', default=str(DEFAULT_STORE))
    parser.add_argument('--runtime', default=str(DEFAULT_RUNTIME))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('families')
    run = sub.add_parser('run')
    run.add_argument('--family', action='append', default=None, choices=sorted(FAMILIES))
    run.add_argument('--all', action='store_true')
    sweep = sub.add_parser('sweep', help='sweep the 698-district agromet family; resumable and idempotent')
    sweep.add_argument('--state', default=None, help='limit the sweep to one source state')
    sweep.add_argument('--district', action='append', default=None, help='limit the sweep to named districts')
    sweep.add_argument('--limit', type=int, default=None, help='stop after this many queued targets')
    sweep.add_argument('--recheck', action='store_true', help='re-test every target already recorded today')
    sweep.add_argument('--retry-failed', action='store_true',
                       help='re-test only the targets whose recorded outcome today was a failure')
    sweep.add_argument('--ttl', type=int, default=0, help='accept a cached body younger than this many seconds')
    sweep.add_argument('--byte-budget', type=int, default=None, help='stop this pass after downloading this many bytes')
    search = sub.add_parser('search')
    search.add_argument('--query', required=True)
    search.add_argument('--family', default=None)
    search.add_argument('--scope', default=None)
    search.add_argument('--region', default=None)
    search.add_argument('--limit', type=int, default=6)
    sub.add_parser('status')
    manifest = sub.add_parser('manifest')
    manifest.add_argument('--day', default=None)
    args = parser.parse_args()
    store_root = Path(args.store)
    if args.command == 'families':
        print(json.dumps({k: {'source_id': v['source_id'], 'scope': v['scope'], 'region': v.get('region'),
                              'label': v['label'], 'address': v.get('address'), 'discovery': v.get('discovery')}
                          for k, v in sorted(FAMILIES.items())}, indent=1, ensure_ascii=False))
        return
    if args.command == 'sweep':
        result = run_district_sweep(store_root, Path(args.runtime), targets=args.district, limit=args.limit,
                                    state=args.state, recheck=args.recheck, retry_failed=args.retry_failed,
                                    fetch_ttl=args.ttl, byte_budget=args.byte_budget)
        print(json.dumps(result, indent=1, ensure_ascii=False))
        return
    if args.command == 'run':
        if not args.all and not args.family:
            parser.error('choose --family or --all')
        names = sorted(FAMILIES) if args.all else args.family
        reports = run_families(names, store_root, Path(args.runtime))
        print(json.dumps(reports, indent=1, ensure_ascii=False))
        return
    index = BulletinIndex(Path(args.runtime) / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite')
    if args.command == 'status':
        print(json.dumps(index.document_families(), indent=1, ensure_ascii=False, default=str))
        return
    if args.command == 'search':
        results, method = index.search_passages(args.query, family=args.family, scope=args.scope,
                                               region=args.region, limit=args.limit)
        print(json.dumps({'method': method, 'results': [{k: r[k] for k in ('family', 'scope', 'region', 'physical_page', 'section', 'issue_date', 'document_sha256') if k in r} | {'text': r['text'][:400]}
                                                       for r in results]}, indent=1, ensure_ascii=False))
        return
    if args.command == 'manifest':
        day = args.day or datetime.now(IST).date().isoformat()
        path = manifest_path(day)
        print(path.read_text(encoding='utf-8') if path.exists() else json.dumps({'day': day, 'status': 'no manifest recorded for this day'}))
        return


if __name__ == '__main__':
    main()
