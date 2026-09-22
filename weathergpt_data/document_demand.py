"""What readers actually ask for, and what the refresh should fetch next.

The district agromet family has 698 targets and a reader asks about one or two. Until
22 September 2026 the scheduled sweep resolved that mismatch by taking the first 40
names in the publisher's directory order, every run, forever: `already` was keyed to
the DAY's manifest, so each morning began again at Anantpur and each evening stopped
at the same place. Measured on three consecutive days:

    2026-09-20  40 swept, deferred_by_limit 658   31 fetched_new, 290 passages
    2026-09-21  40 swept, deferred_by_limit 658   32 unchanged,     0 passages
    2026-09-22  40 swept, deferred_by_limit 658   32 unchanged,     0 passages

Two runs a day downloading the same forty byte-identical PDFs, indexing nothing, and
reporting success — while 541 of 667 heads had not been re-checked since 14 September
and 399 of 662 held editions still carried the printed issue date 2026-09-11.

This ledger is the correction. Two facts are kept about every district: how often a
reader has asked for it, and when it was last read. The queue is ordered from those,
so the refresh fetches what people read and what has gone stale, rather than what
happens to sort first. Nothing here fetches anything; it decides order, and the
sweep and the query layer both take their order from it.

A demand mark is not a promise to fetch. It records that somebody asked, which is the
only honest basis for deciding which of 698 districts matters tonight.
"""
import sqlite3
from pathlib import Path

from .gazetteer import norm
from .transport import parsed, stamp, utcnow


def region_key(state, district):
    """One key per district, used by the ledger and by every lookup below.

    The index itself keeps district heads in TWO namespaces, which is a fact this module
    has to reconcile rather than pick a side in. The sweep writes
    `document|district_agromet|Ludhiana` through publish_document; the live query path
    writes `punjab|ludhiana` through publish. Both mean "this district was read", and a
    queue that saw only one of them would re-fetch what the other had just refreshed.
    """
    del state  # the publisher's district names are nationally unique; the directory refuses a repeat
    return norm(str(district))


class DemandLedger:
    """A durable record of which districts were asked for, and how often."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS demand (
                region TEXT PRIMARY KEY, state TEXT, district TEXT, asked INTEGER NOT NULL DEFAULT 0,
                first_asked_utc TEXT, last_asked_utc TEXT, last_reason TEXT)''')

    def connection(self):
        return sqlite3.connect(self.path, timeout=10)

    def mark(self, state, district, now=None, reason='asked'):
        """Record that a reader asked for this district's bulletin.

        Called from the query layer on every district document turn, including the ones
        that answer perfectly from a held edition: the point is to learn which districts
        this workspace is actually used for, not only which ones failed.
        """
        if not state or not district:
            return None
        now = now or utcnow()
        key = region_key(state, district)
        with self.connection() as db:
            db.execute('''INSERT INTO demand (region,state,district,asked,first_asked_utc,last_asked_utc,last_reason)
                          VALUES (?,?,?,1,?,?,?)
                          ON CONFLICT(region) DO UPDATE SET
                            asked=asked+1, last_asked_utc=excluded.last_asked_utc,
                            last_reason=excluded.last_reason''',
                       (key, str(state), str(district), stamp(now), stamp(now), str(reason)[:200]))
        return key

    def rows(self):
        """Every demand record, newest request first."""
        with self.connection() as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute(
                'SELECT * FROM demand ORDER BY last_asked_utc DESC, asked DESC')]

    def counts(self):
        """region -> times asked, for ordering a queue without loading every column."""
        with self.connection() as db:
            return {row[0]: row[1] for row in db.execute('SELECT region, asked FROM demand')}


def head_state(index, family='district_agromet'):
    """district -> (checked_at, status), taking the most recent read from either namespace.

    `document|<family>|<District>` is the sweep's record and the one the corpus answers
    from; `<state>|<district>` is the live query path's. The newer of the two is what
    "when was this district last read" means, so that is what is returned.
    """
    prefix = 'document|' + str(family) + '|'
    held = {}
    with index.connection() as db:
        db.row_factory = sqlite3.Row
        for row in db.execute('SELECT region, checked_at, status FROM heads'):
            region = str(row['region'] or '')
            if region.startswith(prefix):
                name = region[len(prefix):]
            elif '|' in region and not region.startswith('document|'):
                name = region.split('|', 1)[1]
            else:
                continue
            key = norm(name)
            if not key:
                continue
            current = held.get(key)
            if current is None or str(row['checked_at'] or '') > str(current[0] or ''):
                held[key] = (row['checked_at'], row['status'])
    return held


# What the buckets mean, in the order the refresh takes them. A district checked today is
# not in the queue at all: the publisher issues these bulletins once each morning, so a
# second read of the same day is a download that cannot return anything new.
BUCKETS = {
    0: 'a reader asked for it and no edition is held',
    1: 'a reader asked for it and the held edition was not read today',
    2: 'no edition is held and nobody has asked yet',
    3: 'an edition is held but was not read today',
}


def sweep_queue(targets, held, demand, now=None, limit=None, recheck=False, retry_failed=False):
    """The order the refresh should fetch in, and why each target is in it.

    `targets` is the publisher's directory listing, `held` is head_state(index) and
    `demand` is DemandLedger.counts(). Ordering inside a bucket is by how many readers
    asked, then by how long it has been since the district was read, then by the
    directory's own order so the tail is covered deterministically rather than randomly.

    The decisive property is that this reads the INDEX rather than the day's manifest,
    so a district fetched yesterday counts as fetched today and the queue moves through
    the country instead of restarting at the alphabet every morning.
    """
    now = now or utcnow()
    today = now.date()
    queue = []
    for position, target in enumerate(targets):
        key = region_key(target['state'], target['district'])
        checked_at, status = held.get(key, (None, None))
        asked = demand.get(key, 0)
        when = None
        if checked_at:
            try:
                when = parsed(checked_at)
            except (ValueError, TypeError):
                when = None
        # ATTEMPTED TODAY, NOT READ TODAY.
        #
        # This counted only `status == 'ok'` as done, so a district that FAILED today stayed
        # in the queue. Under a twice-daily job that is harmless - the run ends. Under the
        # resident worker it is not: 71 of the 698 districts last read with a failure, most
        # of them held outcomes like `layout_unrecognised` or "no reviewed family marker"
        # that will fail again on the next byte-identical body, and the worker would spin on
        # them for the rest of the day, re-downloading the same PDFs forever and never
        # reaching the districts that can be read.
        #
        # An attempt is an attempt. A failure today is retried tomorrow, or now under
        # --retry-failed, which is the switch that exists to say "try those again".
        attempted = when is not None and when.date() >= today
        if retry_failed:
            # Only what actually errored. A held layout and a publisher's "not issued" are
            # answers, so retrying them re-downloads the corpus to learn nothing.
            if status != 'failed':
                continue
        elif attempted and not recheck:
            continue
        if when is None:
            bucket = 0 if asked else 2
        else:
            bucket = 1 if asked else 3
        queue.append({'target': target, 'bucket': bucket, 'why': BUCKETS[bucket], 'asked': asked,
                      'last_read_utc': checked_at, 'last_status': status,
                      'sort': (bucket, -asked, checked_at or '', position)})
    queue.sort(key=lambda item: item['sort'])
    for item in queue:
        del item['sort']
    return queue[:limit] if limit else queue


def freshness(targets, held, now=None):
    """How much of the family was read today, and how old the rest is. Measured, not assumed.

    A refresh that downloads forty identical bodies and indexes nothing looks identical to
    a refresh that did its job unless somebody counts what is actually held, which is why
    this is reported on every cycle rather than left for an audit nobody runs.
    """
    now = now or utcnow()
    today = now.date()
    read_today = attempted_today = never_held = failing = withheld = 0
    ages = []
    for target in targets:
        checked_at, status = held.get(region_key(target['state'], target['district']), (None, None))
        if not checked_at:
            never_held += 1
            continue
        # The standing vocabulary, kept apart here as it is everywhere else: `not_issued` is an
        # answer and `layout_unrecognised` is held, so neither is counted as a failure. Only a
        # transport or extraction error is. Collapsing them would report the publisher's
        # layouts as this workspace's breakages.
        if status == 'failed':
            failing += 1
        elif status not in ('ok', None):
            withheld += 1
        try:
            when = parsed(checked_at)
        except (ValueError, TypeError):
            never_held += 1
            continue
        age = (today - when.date()).days
        ages.append(age)
        if age <= 0:
            attempted_today += 1
            if status == 'ok':
                read_today += 1
    ages.sort()
    return {'listed': len(targets), 'read_today': read_today,
            # Read and attempted are different numbers and the gap between them is the
            # publisher's layouts, not this workspace's diligence. The worker is done for the
            # day when everything has been ATTEMPTED; the corpus is as fresh as it can be
            # when everything readable has been READ.
            'attempted_today': attempted_today,
            'unattempted_today': max(len(targets) - attempted_today, 0),
            'never_held': never_held,
            'held_but_stale': max(len(ages) - read_today, 0), 'last_read_failed': failing,
            'last_read_withheld': withheld,
            'oldest_read_days': ages[-1] if ages else None,
            'median_read_days': ages[len(ages) // 2] if ages else None,
            'scope': 'Counted from the corpus index heads against the publisher directory, '
                     'not from the day manifest: a district read yesterday counts as read.'}
