#!/usr/bin/env python3
'''Sweep the listed state agromet targets, recording each outcome as itself.

    python3 scripts/ingest_state_agromet.py                 # every listed target
    python3 scripts/ingest_state_agromet.py --only Rajasthan,Gujarat
    python3 scripts/ingest_state_agromet.py --dry-run       # list the targets and stop

A listed target and a reachable address are not a promise that a bulletin is issued. Each target's
outcome is recorded with the same vocabulary the district sweep uses: fetched_new, unchanged,
not_issued, layout_unrecognised, no_text_layer and failed are six different things, and a failure is
never recorded as an absence. The state a centre serves is this registry's claim until the document
names it, so every record carries state_named_in_document.
'''
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.bulletin_index import BulletinIndex, EXTRACTION_VERSION  # noqa: E402
from weathergpt_data.document_ingest import ingest_state  # noqa: E402
from weathergpt_data.evidence_transport import evidence_store  # noqa: E402
from weathergpt_data.transport import stamp  # noqa: E402

REGISTRY = ROOT / 'data' / 'registry' / 'state-agromet-targets.json'
MAX_TARGETS = 40


class _Workspace:
    '''The evidence store needs only a clock and a raw root to fetch into.'''

    class _Service:
        raw_root = ROOT / 'data' / 'runtime' / 'ingestion' / 'raw'
        ingestion_database = ROOT / 'data' / 'runtime' / 'ingestion' / 'ingestion.sqlite'

    service = _Service()

    opener = None

    def clock(self):
        return datetime.now(timezone.utc)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--only', default='', help='comma-separated state names to sweep')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0)
    arguments = parser.parse_args()
    document = json.loads(REGISTRY.read_text(encoding='utf-8'))
    wanted = {name.strip().lower() for name in arguments.only.split(',') if name.strip()}
    targets = [item for item in document['candidates']
               if not wanted or str(item.get('state', '')).lower() in wanted]
    if arguments.limit:
        targets = targets[:arguments.limit]
    if len(targets) > MAX_TARGETS:
        raise SystemExit('A sweep of more than ' + str(MAX_TARGETS) + ' targets needs its own review.')
    if arguments.dry_run:
        for item in targets:
            print('%-18s %-14s %s' % (item['state'], item['centre'], item['address']))
        print(str(len(targets)) + ' target(s) listed; nothing fetched.')
        return 0
    now = datetime.now(timezone.utc)
    index = BulletinIndex(ROOT / 'data' / 'runtime' / 'ingestion' / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite')
    records = []
    with evidence_store(_Workspace(), 'imd_bulletins',
                        ROOT / 'data' / 'runtime' / 'ingestion' / 'bulletins' / 'raw') as store:
        for item in targets:
            record = ingest_state(store, index, item['state'], item['address'], now=now)
            record['centre'] = item['centre']
            records.append(record)
            print('%-18s %-14s %-20s %s' % (item['state'], item['centre'], record['outcome'],
                                            str(record.get('error') or record.get('issue_date') or '')[:60]))
    # Outcomes accumulate per state: a later run must not erase what an earlier run learned,
    # and a failed repeat is part of the record rather than noise to be overwritten.
    outcomes = document.get('outcomes') or {}
    for record in records:
        key = record['state'] + '/' + record.get('centre', '')  # a state can have several centres
        prior = outcomes.get(key) or {}
        history = (prior.get('history') or [])[-4:]
        history.append({'at_utc': record['started_at_utc'], 'outcome': record['outcome'],
                        'error': record.get('error')})
        outcomes[key] = dict(record, history=history)
    document['outcomes'] = outcomes
    # The corpus is the durable record. The indexed document for a state carries the printed issue
    # date, the marker that recognised it, its language and its currency, and reading them back
    # means a later 'unchanged' pass cannot erase what an earlier extraction measured.
    from weathergpt_data.document_ingest import STATE_NAMES_IN_DOCUMENT
    stored_by_region = {}
    try:
        import sqlite3
        with sqlite3.connect(index.path) as db:
            for (payload,) in db.execute('SELECT payload FROM documents'):
                record_doc = json.loads(payload)
                if record_doc.get('family') == 'state_agromet' and record_doc.get('region'):
                    stored_by_region[record_doc['region']] = record_doc
    except (sqlite3.Error, ValueError):
        stored_by_region = {}
    for item in document['candidates']:
        key = item['state'] + '/' + item['centre']
        record = dict(outcomes.get(key) or {})
        stored = stored_by_region.get(item['state'])
        if not stored:
            continue
        for field in ('issue_date', 'issue_date_basis', 'language', 'marker_basis', 'issuer_basis',
                      'currency', 'age_days', 'sha256'):
            if stored.get(field) is not None:
                record[field] = stored[field]
        passages = stored.get('passages') or []
        if passages:
            record['passages'] = len(passages)
            flat = ' '.join(str(passage.get('text') or '') for passage in passages).lower()
            local = STATE_NAMES_IN_DOCUMENT.get(item['state'], '')
            record['state_named_in_document'] = item['state'].lower() in flat or bool(local and local in flat)
        record['evidence_source'] = 'index'
        outcomes[key] = record
    document['outcomes'] = outcomes
    document['sweep'] = {'generated_at_utc': stamp(now), 'targets': records,
                         'counts': {outcome: len([r for r in records if r['outcome'] == outcome])
                                    for outcome in sorted({r['outcome'] for r in records})}}
    REGISTRY.write_text(json.dumps(document, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
    print('outcomes: ' + json.dumps(document['sweep']['counts']))
    print('written ' + str(REGISTRY))
    return 0


if __name__ == '__main__':
    sys.exit(main())