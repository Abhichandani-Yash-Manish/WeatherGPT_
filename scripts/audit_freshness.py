#!/usr/bin/env python3
"""Is the store current enough for the chat to answer from?

    python3 scripts/audit_freshness.py            # report
    python3 scripts/audit_freshness.py --json
    python3 scripts/audit_freshness.py --strict   # exit 1 when anything is stale

The chat can only be as good as what it has to read, and a stale store does not look like a broken
store: it looks like a careful product declining to answer. On 20 September the district bulletin store
held nothing newer than 15 September, so "Is any warning in force for Patna today?" replied that every
day the stored bulletin publishes has already passed - correct, honest, and useless. Nothing failed.
Nothing alerted. The daily cycle had simply not been run, and there was no check that noticed.

This is that check. It reads the store rather than the registry, because the registry says what should be
there and the point is to find out what is.

A budget here is a serving expectation, not a publisher SLA: it is how old this product is willing to let
a thing get before it says so.
"""
import argparse, json, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (name, path, how many days old before it is stale, why it matters to a reader)
SHELVES = [
    ('district bulletins', 'data/processed/bulletins', 2,
     'the district warning product; a lapsed bulletin makes every warning question decline'),
    ('document bodies', 'data/runtime/documents', 3,
     'the passages a document question quotes'),
    ('briefings', 'data/runtime/briefings', 7,
     'the composed briefings the board and the watch inbox read'),
    ('ingestion queue', 'data/runtime/ingestion', 2,
     'the numeric products: forecast, marine, river'),
]


def newest_mtime(path):
    root = ROOT / path
    if not root.exists():
        return None
    newest = None
    for item in root.rglob('*'):
        if item.is_file() and not item.name.startswith('.'):
            stamp = item.stat().st_mtime
            newest = stamp if newest is None or stamp > newest else newest
    return newest


def dated_directories(path):
    """The YYYY-MM-DD directories a shelf keeps, newest first.

    A file's mtime says when this machine wrote it; a dated directory says which day the contents are
    ABOUT, which is the thing a reader cares about and the thing that goes stale.
    """
    root = ROOT / path
    if not root.exists():
        return []
    days = []
    for item in root.iterdir():
        if item.is_dir():
            try:
                days.append(datetime.strptime(item.name, '%Y-%m-%d').date())
            except ValueError:
                continue
    return sorted(days, reverse=True)


def ingestion_health():
    """Job states from the ingestion queue, which is where a silent refusal to store shows up."""
    path = ROOT / 'data/runtime/ingestion/ingestion.sqlite'
    if not path.exists():
        return None
    try:
        con = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
        return {state: count for state, count in con.execute('select state, count(*) from jobs group by state')}
    except sqlite3.Error as error:
        return {'unreadable': str(error)[:60]}


WFS = ('https://reactjs.imd.gov.in/geoserver/wfs?service=WFS&version=1.1.0&request=GetFeature'
       '&typename=imd:district_warnings_india&srsname=EPSG:4326&outputFormat=application/json'
       '&maxFeatures=2000&propertyName=District,Date')


def publisher_date():
    """What the district warning layer itself is dated, straight from IMD.

    This is the difference between a gap we can close and one we cannot. On 20 September this product
    declined every warning question because the bulletin it held was dated the 15th and all five of its
    days had passed - which looks exactly like a store nobody had refreshed. It was not. The live layer
    is dated the 15th too, for 742 of its 764 districts. Our copy was current with the publisher, and
    running the ingest again could not have produced a newer bulletin than the one that exists.

    A freshness report that cannot tell those apart sends you looking for a bug in your own pipeline.
    """
    import collections, urllib.request
    try:
        with urllib.request.urlopen(WFS, timeout=90) as response:
            payload = json.loads(response.read().decode('utf-8', 'replace'))
    except Exception as error:                      # network, DNS, TLS, malformed - all the same here
        return {'reachable': False, 'why': type(error).__name__ + ': ' + str(error)[:80]}
    dates = collections.Counter(
        str((feature.get('properties') or {}).get('Date'))[:10]
        for feature in payload.get('features') or [])
    dates.pop('', None)
    dates.pop('None', None)
    if not dates:
        return {'reachable': True, 'dated': None, 'why': 'the layer returned no dated feature'}
    dated, districts = dates.most_common(1)[0]
    return {'reachable': True, 'dated': dated, 'districts': districts,
            'features': sum(dates.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--strict', action='store_true', help='exit non-zero when a shelf is over budget')
    parser.add_argument('--check-sources', action='store_true',
                        help='also ask the publisher what IT is dated, to tell our staleness from theirs')
    args = parser.parse_args()

    now = time.time()
    # The local date, because the dated directories are named in local time: comparing them against a UTC
    # date makes a shelf written this morning read as a day ahead of itself.
    today = datetime.now().date()
    rows, stale = [], []

    for name, path, budget, why in SHELVES:
        written = newest_mtime(path)
        days = sorted(dated_directories(path), reverse=True)
        covers = days[0] if days else None
        age_days = None if written is None else round((now - written) / 86400, 1)
        behind = None if covers is None else (today - covers).days
        # A shelf that dates its contents is judged on the date; one that does not, on when it was written.
        measured = behind if behind is not None else age_days
        over = measured is not None and measured > budget
        rows.append({'shelf': name, 'path': path, 'budget_days': budget,
                     'covers': covers.isoformat() if covers else None, 'days_behind': behind,
                     'written_days_ago': age_days, 'over_budget': bool(over), 'why': why,
                     'present': written is not None})
        if over or written is None:
            stale.append(name)

    jobs = ingestion_health()
    upstream = publisher_date() if args.check_sources else None
    if args.json:
        print(json.dumps({'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                          'shelves': rows, 'ingestion_jobs': jobs, 'publisher': upstream,
                          'stale': stale}, indent=1))
    else:
        print(f'{"shelf":22} {"covers":12} {"behind":>7} {"budget":>7}  state')
        for row in rows:
            behind = '-' if row['days_behind'] is None else str(row['days_behind']) + 'd'
            covers = row['covers'] or (f"{row['written_days_ago']}d old" if row['present'] else 'MISSING')
            state = 'STALE' if row['over_budget'] else ('MISSING' if not row['present'] else 'ok')
            print(f'{row["shelf"]:22} {covers:12} {behind:>7} {str(row["budget_days"]) + "d":>7}  {state}')
            if row['over_budget'] or not row['present']:
                print(f'{"":22} -> {row["why"]}')
        if jobs:
            print(f'\ningestion jobs: {jobs}')
        if upstream is not None:
            if not upstream.get('reachable'):
                print(f'\npublisher: unreachable - {upstream.get("why")}')
            elif upstream.get('dated'):
                behind = (today - datetime.strptime(upstream['dated'], '%Y-%m-%d').date()).days
                print(f'\npublisher: IMD district warning layer is dated {upstream["dated"]} '
                      f'({upstream["districts"]} of {upstream["features"]} districts), {behind}d old')
                if behind > 1:
                    print('           the publisher is behind, not this store: re-running the ingest '
                          'cannot produce a newer bulletin than the one that exists')
        print(f'\n{len(rows)} shelf/shelves, {len(stale)} over budget'
              + (': ' + ', '.join(stale) if stale else ''))
        if stale:
            print('\nRefresh with:  python3 scripts/run_daily_cycle.py')

    return 1 if (stale and args.strict) else 0


if __name__ == '__main__':
    sys.exit(main())
