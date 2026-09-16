"""Transactional outbox for watch notifications: exactly-once intent, bounded retries.

A notification is enqueued when a watch check observes a *changed* official state
(a new fingerprint). The row then moves through a small state machine; every
transition is written to the notification ledger. Retries are bounded by
MAX_RETRIES with a backoff set at dispatch time, so a failing channel can never
spin an uncontrolled loop. Terminal states (dead, acked) are never re-dispatched.

Payload rule: the notification carries the official facts the check observed,
verbatim, plus the standing limitations. Nothing is invented, no severity is
altered, and a notification never claims an all-clear.
"""
import hashlib
import json
import random
import sqlite3
import uuid
from datetime import timedelta

from .transport import SourceError, parsed, stamp, utcnow

SCHEMA = 'outbox-v1'
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (60, 300, 900)
# A delivery that cannot succeed within a day of its creation is dead: the
# warning window it belongs to has almost certainly moved on, and silent
# zombie retries are worse than an auditable terminal row.
MAX_RETRY_AGE_SECONDS = 86400
# How long a worker owns a claimed row before another worker may take it.
CLAIM_LEASE_SECONDS = 300
# Jitter bound on scheduled retries so a recovering source is not hammered
# by every watcher at the same second.
RETRY_JITTER_FRACTION = 0.2

# `created` is reserved for a future producer that stages a row before queueing;
# every producer today enqueues directly into `queued`. `claimed` is a lock, not
# a delivery outcome: a worker owns the row until its lease expires. Claim and
# reclaim never write ledger rows, so the ledger stays a pure delivery history
# (queued/failed/sent/...) — the claim is visible on the row itself.
STATES = ('created', 'queued', 'claimed', 'sent', 'failed', 'dead', 'acked', 'gone')
TERMINAL_STATES = {'dead', 'acked', 'gone'}
DISPATCHABLE_STATES = {'created', 'queued'}

# Allowed (old_state -> new_state) moves. A failed row may record another failure
# (failed -> failed) while retries remain. `gone` is for rows overtaken by events:
# the watch window lapsed while queued, or the edition was superseded. Terminal
# states (dead, acked, gone) are never re-dispatched. `claimed` is entered from
# any dispatchable state and released back to queued, sent onward, or closed.
TRANSITIONS = {
    'created': {'queued', 'claimed', 'dead', 'gone'},
    'queued': {'claimed', 'sent', 'failed', 'dead', 'gone'},
    'claimed': {'queued', 'sent', 'failed', 'dead', 'gone'},
    'sent': {'acked', 'failed', 'dead', 'gone'},
    'failed': {'queued', 'claimed', 'failed', 'dead', 'gone'},
    'dead': set(),
    'acked': set(),
    'gone': set(),
}

# Delivery-error classes. Only `purged` (the push service retired the
# subscription) is terminal-by-kind today; everything else a sender reports
# is `retryable` within budget and age. `dead` is reserved for explicit
# non-retryable provider rejections (none of the current senders emit one —
# recorded here so a future channel can use it without a schema change).
ERROR_CLASSES = ('retryable', 'purged', 'dead', 'lapsed')

# Substrings of this codebase's own sender detail strings that mark a purged
# push subscription. Kept in one place so the classifier and the sender text
# cannot drift apart silently (covered by PurgeTests).
PURGED_DETAIL_MARKERS = ('expired and was retired',)

NOTIFICATION_LIMITATIONS = [
    'This is official product state, not an instruction, and origin authentication remains unverified.',
    'A no-match result is not an all-clear and it does not cover products that are not connected.',
]


def check_transition(old_state, new_state):
    """Validate one state move; raises SourceError on an illegal move."""
    if old_state not in TRANSITIONS:
        raise SourceError('Unknown outbox state: ' + str(old_state))
    if new_state not in TRANSITIONS[old_state]:
        raise SourceError('Invalid outbox transition from %s to %s' % (old_state, new_state))
    return new_state


def retry_delay(retry_count):
    """Backoff in seconds for a failure count (1-based). Bounded by table length."""
    index = max(0, min(retry_count, len(RETRY_BACKOFF_SECONDS)) - 1)
    return RETRY_BACKOFF_SECONDS[index]


def retry_at_with_jitter(now, retry_count):
    """A retry instant: exact backoff plus bounded jitter.

    `retry_delay` stays pure and exact (pinned by tests); the jitter lives
    here so a recovering source is not hit by every watcher at once.
    """
    base = retry_delay(retry_count)
    spread = base * RETRY_JITTER_FRACTION
    return stamp(now + timedelta(seconds=base + random.uniform(-spread, spread)))


def idempotency_key(watch_id, fingerprint_sha256, channel, dedupe_kind='change'):
    """Duplicate-safe delivery identity: one logical event per key.

    The same warning state re-fetched, re-queued after a restart, or evaluated
    by an overlapping worker maps to the same key, so only the first enqueue
    wins. Escalation follow-ups carry their own kind and never collide with
    the change event they follow.
    """
    raw = '|'.join((str(watch_id), str(fingerprint_sha256), str(channel),
                    str(dedupe_kind or 'change')))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def classify_error(detail):
    """Map a sender's human detail string to an error class.

    Matches only this codebase's own sender vocabulary (see
    `PURGED_DETAIL_MARKERS`); anything unrecognised is retryable within
    budget and age, never silently dropped.
    """
    text = str(detail or '')
    if any(marker in text for marker in PURGED_DETAIL_MARKERS):
        return 'purged'
    return 'retryable'


def build_notification_payload(watch, outcome, packet_facts, packet_status, now=None):
    """The notification content for one changed official state. Facts verbatim."""
    moment = now or utcnow()
    place = watch.get('place') or {}
    facts = [fact for fact in (packet_facts or [])
             if isinstance(fact, dict) and fact.get('parameter') == 'official_district_warning'][:4]
    return {'schema_version': 'notification-v1',
            'watch_id': watch.get('id'), 'hazard': watch.get('hazard'),
            'place': {'name': place.get('name'), 'state': place.get('state')},
            'window': {'starts': watch.get('window_start'), 'ends': watch.get('window_end')},
            'matched': bool(outcome.get('matched')), 'reason': outcome.get('reason'),
            'detail': outcome.get('detail'),
            'facts': [{'label': fact.get('label'), 'value': fact.get('value'), 'unit': fact.get('unit'),
                       'start': fact.get('start'), 'end': fact.get('end'),
                       'hazard_codes': fact.get('hazard_codes'), 'source_id': fact.get('source_id')}
                      for fact in facts],
            'unmapped_hazard_codes': outcome.get('unmapped_hazard_codes') or [],
            'packet_status': packet_status,
            'checked_at_utc': stamp(moment),
            'limitations': list(NOTIFICATION_LIMITATIONS)}


class OutboxStore:
    # Columns added after the original 13-column outbox table. _migrate()
    # applies them to existing databases; new code always reads/writes them.
    OUTBOX_SCHEMA_EXTRA = (('claimed_by', 'TEXT'), ('claimed_at', 'TEXT'),
                           ('lease_expires_at', 'TEXT'), ('idempotency_key', 'TEXT'),
                           ('error_class', 'TEXT'))

    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY,watch_id TEXT,correlation_id TEXT,'
                       'fingerprint_sha256 TEXT,state TEXT,channel TEXT,payload TEXT,created_at TEXT,updated_at TEXT,'
                       'retry_count INTEGER,max_retries INTEGER,next_retry_at TEXT,last_error TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS notification_ledger (id TEXT PRIMARY KEY,outbox_id TEXT,'
                       'event TEXT,timestamp TEXT,detail TEXT)')
            self._migrate(db)
            db.commit()
        finally:
            db.close()

    def _migrate(self, db):
        cols = {row[1] for row in db.execute('PRAGMA table_info(outbox)').fetchall()}
        for name, decl in self.OUTBOX_SCHEMA_EXTRA:
            if name not in cols:
                db.execute('ALTER TABLE outbox ADD COLUMN %s %s' % (name, decl))
        # Duplicate-safe delivery identity: NULL keys (pre-migration rows) never
        # collide; every new row carries a key.
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS outbox_idempotency ON outbox(idempotency_key)')

    @staticmethod
    def _decode(item):
        try:
            item['payload'] = json.loads(item['payload'] or '{}')
        except ValueError:
            item['payload'] = {}
        if not isinstance(item['payload'], dict):
            item['payload'] = {}
        return item

    def _record(self, db, outbox_id, event, detail, now):
        db.execute('INSERT INTO notification_ledger VALUES (?,?,?,?,?)',
                   (str(uuid.uuid4()), outbox_id, event, stamp(now),
                    json.dumps(detail, ensure_ascii=False) if detail is not None else None))

    def _existing_key(self, db, key):
        """A live (non-terminal) row already owning this delivery identity."""
        db.row_factory = sqlite3.Row
        return db.execute("SELECT * FROM outbox WHERE idempotency_key=? AND state NOT IN ('dead','acked','gone')",
                          (key,)).fetchone()

    def enqueue(self, watch_id, correlation_id, fingerprint_sha256, channel, payload, now=None,
                dedupe_kind='change'):
        """Enqueue one notification in queued state and record the ledger event.

        Duplicate-safe: a live row with the same delivery identity is returned
        instead of inserting a second row, so restarts, retries and overlapping
        workers cannot double-enqueue one logical event.
        """
        now = now or utcnow()
        key = idempotency_key(watch_id, fingerprint_sha256, channel, dedupe_kind)
        db = sqlite3.connect(self.path)
        try:
            existing = self._existing_key(db, key)
            if existing is not None:
                return self._decode(dict(existing))
            entry = {'id': str(uuid.uuid4()), 'watch_id': watch_id, 'correlation_id': correlation_id,
                     'fingerprint_sha256': fingerprint_sha256, 'state': 'queued', 'channel': channel,
                     'payload': payload, 'created_at': stamp(now), 'updated_at': stamp(now),
                     'retry_count': 0, 'max_retries': MAX_RETRIES, 'next_retry_at': None, 'last_error': None}
            db.execute('INSERT INTO outbox (id,watch_id,correlation_id,fingerprint_sha256,state,channel,payload,'
                       'created_at,updated_at,retry_count,max_retries,next_retry_at,last_error,idempotency_key)'
                       ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (entry['id'], watch_id, correlation_id, fingerprint_sha256, 'queued', channel,
                        json.dumps(payload, ensure_ascii=False), entry['created_at'], entry['updated_at'],
                        0, MAX_RETRIES, None, None, key))
            self._record(db, entry['id'], 'queued',
                         {'channel': channel, 'correlation_id': correlation_id,
                          'fingerprint_sha256': fingerprint_sha256}, now)
            db.commit()
        finally:
            db.close()
        return entry

    def enqueue_changed(self, watch_id, correlation_id, fingerprint_sha256, channels, payload, now=None):
        """Enqueue one row per channel and store the new fingerprint in one transaction.

        Either every row lands together with the fingerprint, or nothing lands: a crash
        between enqueue and fingerprint can never produce a duplicate on the next check.
        Per-channel delivery identities make re-evaluation duplicate-safe as well.
        Returns the list of enqueued entries.
        """
        now = now or utcnow()
        db = sqlite3.connect(self.path)
        try:
            entries = []
            for channel in channels:
                key = idempotency_key(watch_id, fingerprint_sha256, channel, 'change')
                existing = self._existing_key(db, key)
                if existing is not None:
                    entries.append(self._decode(dict(existing)))
                    continue
                entry = {'id': str(uuid.uuid4()), 'watch_id': watch_id, 'correlation_id': correlation_id,
                         'fingerprint_sha256': fingerprint_sha256, 'state': 'queued', 'channel': channel,
                         'payload': payload, 'created_at': stamp(now), 'updated_at': stamp(now),
                         'retry_count': 0, 'max_retries': MAX_RETRIES, 'next_retry_at': None, 'last_error': None}
                db.execute('INSERT INTO outbox (id,watch_id,correlation_id,fingerprint_sha256,state,channel,payload,'
                           'created_at,updated_at,retry_count,max_retries,next_retry_at,last_error,idempotency_key)'
                           ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                           (entry['id'], watch_id, correlation_id, fingerprint_sha256, 'queued',
                            entry['channel'], json.dumps(payload, ensure_ascii=False),
                            entry['created_at'], entry['updated_at'], 0, MAX_RETRIES, None, None, key))
                self._record(db, entry['id'], 'queued',
                             {'channel': entry['channel'], 'correlation_id': correlation_id,
                              'fingerprint_sha256': fingerprint_sha256}, now)
                entries.append(entry)
            db.execute('UPDATE watches SET fingerprint_sha256=? WHERE id=?', (fingerprint_sha256, watch_id))
            db.commit()
        finally:
            db.close()
        return entries

    def list(self, state=None, watch_id=None):
        query = 'SELECT * FROM outbox'
        clauses, args = [], []
        if state is not None:
            clauses.append('state=?'); args.append(state)
        if watch_id is not None:
            clauses.append('watch_id=?'); args.append(watch_id)
        if clauses:
            query += ' WHERE ' + ' AND '.join(clauses)
        query += ' ORDER BY created_at DESC'
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            rows = [self._decode(dict(row)) for row in db.execute(query, args)]
        finally:
            db.close()
        return rows

    def get(self, outbox_id):
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM outbox WHERE id=?', (outbox_id,)).fetchone()
        finally:
            db.close()
        if row is None:
            raise SourceError('No outbox notification with this identifier')
        return self._decode(dict(row))

    def ledger(self, outbox_id):
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            rows = [dict(row) for row in db.execute(
                'SELECT * FROM notification_ledger WHERE outbox_id=? ORDER BY timestamp', (outbox_id,))]
        finally:
            db.close()
        return rows

    def set_state(self, outbox_id, new_state, detail=None, now=None, next_retry_at=None,
                  error_class=None):
        """Move one notification to a new state after validating the transition."""
        now = now or utcnow()
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM outbox WHERE id=?', (outbox_id,)).fetchone()
            if row is None:
                raise SourceError('No outbox notification with this identifier')
            current = dict(row)
            check_transition(current['state'], new_state)
            retry_count = int(current['retry_count'] or 0)
            last_error = current['last_error']
            retry_at = current['next_retry_at']
            if new_state == 'failed':
                retry_count += 1
                last_error = str(detail) if detail is not None else last_error
                retry_at = next_retry_at
            if new_state in ('dead', 'gone') and detail is not None:
                last_error = str(detail) if not isinstance(detail, dict) else json.dumps(detail)
            if new_state in ('sent', 'acked'):
                retry_at = None
            db.execute('UPDATE outbox SET state=?,updated_at=?,retry_count=?,next_retry_at=?,last_error=?,'
                       'error_class=? WHERE id=?',
                       (new_state, stamp(now), retry_count, retry_at, last_error, error_class, outbox_id))
            self._record(db, outbox_id, new_state,
                         {'from': current['state'], 'detail': detail, 'retry_count': retry_count,
                          'error_class': error_class}, now)
            db.commit()
        finally:
            db.close()
        return self.get(outbox_id)

    def count_pending(self, watch_id):
        db = sqlite3.connect(self.path)
        try:
            row = db.execute("SELECT COUNT(*) FROM outbox WHERE watch_id=? AND state IN ('created','queued')",
                             (watch_id,)).fetchone()
        finally:
            db.close()
        return int(row[0]) if row else 0

    def due(self, now=None):
        """Dispatchable rows whose retry time has arrived. Terminal states never return.

        Failed rows return while their retry budget remains, so backoff retries are
        actually dispatched; rows that spent their budget stay out even before a
        dispatcher marks them dead. Claimed rows are owned by a worker and never
        return here — a stale claim must go through `reclaim` first.
        """
        now = now or utcnow()
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            rows = []
            for row in db.execute("SELECT * FROM outbox WHERE state IN ('created','queued','failed')"
                                  ' ORDER BY created_at'):
                item = self._decode(dict(row))
                if item['state'] == 'failed' and int(item.get('retry_count') or 0) >= int(item.get('max_retries') or MAX_RETRIES):
                    continue
                retry_at = item.get('next_retry_at')
                if retry_at is not None and parsed(retry_at) > now:
                    continue
                rows.append(item)
        finally:
            db.close()
        return rows

    def claim(self, owner, now=None, lease_seconds=CLAIM_LEASE_SECONDS, limit=50):
        """Take ownership of due rows for one worker. Returns the claimed rows.

        The claim is a lock, not a delivery outcome: it sets owner + lease on
        the row without writing a ledger event, so delivery history stays pure.
        A second worker claiming the same rows gets nothing back.
        """
        now = now or utcnow()
        due_ids = [item['id'] for item in self.due(now=now)[:limit]]
        if not due_ids:
            return []
        lease_until = stamp(now + timedelta(seconds=lease_seconds))
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            claimed = []
            for row_id in due_ids:
                cursor = db.execute("UPDATE outbox SET state='claimed',claimed_by=?,claimed_at=?,"
                                    "lease_expires_at=? WHERE id=? AND state IN ('created','queued','failed')",
                                    (str(owner), stamp(now), lease_until, row_id))
                if cursor.rowcount:
                    row = db.execute('SELECT * FROM outbox WHERE id=?', (row_id,)).fetchone()
                    claimed.append(self._decode(dict(row)))
            db.commit()
        finally:
            db.close()
        return claimed

    def reclaim(self, now=None):
        """Release claims whose lease expired (crashed or slow workers).

        Re-queued silently (no ledger event): the next dispatch re-sends through
        the normal path, and the idempotency key keeps providers duplicate-safe
        where the channel supports it. Returns the reclaimed count.
        """
        now = now or utcnow()
        db = sqlite3.connect(self.path)
        try:
            cursor = db.execute("UPDATE outbox SET state='queued',claimed_by=NULL,claimed_at=NULL,"
                                "lease_expires_at=NULL WHERE state='claimed' AND lease_expires_at IS NOT NULL"
                                " AND lease_expires_at<=?", (stamp(now),))
            db.commit()
            return {'requeued': cursor.rowcount}
        finally:
            db.close()

    def stats(self, now=None):
        """Queue depths per state plus the oldest undispatched age. For /health."""
        now = now or utcnow()
        db = sqlite3.connect(self.path)
        try:
            counts = {state: 0 for state in STATES}
            for state, total in db.execute('SELECT state,COUNT(*) FROM outbox GROUP BY state'):
                if state in counts:
                    counts[state] = int(total)
            oldest = db.execute("SELECT MIN(created_at) FROM outbox WHERE state IN "
                                "('created','queued','claimed','failed')").fetchone()
        finally:
            db.close()
        depth = sum(counts[state] for state in ('created', 'queued', 'claimed', 'failed'))
        return {'counts': counts, 'undispatched_depth': depth,
                'oldest_undispatched_created_at': oldest[0] if oldest else None}


def default_sender(entry):
    """Deliver one outbox row. local_inbox is always connected; anything else is not.

    Returns (ok, detail). A sender for another channel (web push in Phase 3) is
    injected by the caller; unknown channels fail closed with a bounded retry.
    """
    if entry.get('channel') == 'local_inbox':
        return True, 'Ready in the local watch inbox; no background daemon is installed.'
    return False, 'Channel %s is not connected in this workspace' % (entry.get('channel'),)


ACK_RESPONSES = ('safe', 'need_help', 'evacuating', 'seen')
ESCALATION_TIMEOUT_SECONDS = 1800
ESCALATION_MAX_DEPTH = 2


class FeedbackStore:
    """Two-way responses to sent notifications: safe, need help, evacuating, seen."""
    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS watch_feedback (id TEXT PRIMARY KEY,watch_id TEXT,'
                       'outbox_id TEXT,response TEXT,timestamp TEXT,channel TEXT)')
            db.commit()
        finally:
            db.close()

    def record(self, watch_id, outbox_id, response, channel, now=None):
        if response not in ACK_RESPONSES:
            raise SourceError('Unknown acknowledgement response: ' + str(response)
                              + '. Send one of: ' + ', '.join(ACK_RESPONSES))
        now = now or utcnow()
        entry = {'id': str(uuid.uuid4()), 'watch_id': watch_id, 'outbox_id': outbox_id,
                 'response': response, 'timestamp': stamp(now), 'channel': channel}
        db = sqlite3.connect(self.path)
        try:
            db.execute('INSERT INTO watch_feedback VALUES (?,?,?,?,?,?)',
                       (entry['id'], watch_id, outbox_id, response, entry['timestamp'], channel))
            db.commit()
        finally:
            db.close()
        return entry

    def list(self, watch_id=None):
        query = 'SELECT * FROM watch_feedback'
        args = []
        if watch_id is not None:
            query += ' WHERE watch_id=?'
            args.append(str(watch_id))
        query += ' ORDER BY timestamp'
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            rows = [dict(row) for row in db.execute(query, args)]
        finally:
            db.close()
        return rows


def acknowledge(store_path, outbox_id, response, now=None):
    """Acknowledge a sent notification and record the two-way response."""
    now = now or utcnow()
    if response not in ACK_RESPONSES:
        raise SourceError('Unknown acknowledgement response: ' + str(response)
                          + '. Send one of: ' + ', '.join(ACK_RESPONSES))
    box = OutboxStore(store_path)
    row = box.get(outbox_id)
    if row['state'] != 'sent':
        raise SourceError('Only a sent notification can be acknowledged; this one is ' + str(row['state']))
    updated = box.set_state(outbox_id, 'acked', {'response': response}, now=now)
    feedback = FeedbackStore(store_path).record(row['watch_id'], outbox_id, response, row['channel'], now=now)
    return {'id': outbox_id, 'state': updated['state'], 'response': response, 'feedback_id': feedback['id']}


def escalate_unacked(store_path, now=None, timeout_seconds=ESCALATION_TIMEOUT_SECONDS,
                     max_depth=ESCALATION_MAX_DEPTH):
    """Escalate sent-but-unacknowledged notifications to the local inbox.

    A notification sent more than timeout_seconds ago with no acknowledgement
    gets one follow-up in the always-connected local inbox channel. Escalations
    chain at most max_depth deep and never touch terminal or already-escalated
    rows twice. SMS/IVR escalation stays deferred (G-F4-16): the follow-up names
    that limit instead of pretending another channel delivered it.
    """
    from datetime import timedelta
    now = now or utcnow()
    box = OutboxStore(store_path)
    rows = box.list()
    escalated = set()
    for row in rows:
        marker = (row.get('payload') or {}).get('escalation') or {}
        if marker.get('of') is not None:
            escalated.add((marker['of'], int(marker.get('depth', 0))))
    retired_watches = None
    try:
        from .watches import WatchStore
        retired_watches = {row['id'] for row in WatchStore(store_path).list(now=now)
                           if row.get('state') == 'expired' or row.get('expired')}
    except (SourceError, OSError, sqlite3.Error):
        retired_watches = None
    created = []
    for entry in rows:
        if entry['state'] != 'sent':
            continue
        if retired_watches is not None and entry.get('watch_id') in retired_watches:
            continue
        payload = entry.get('payload') or {}
        depth = int((payload.get('escalation') or {}).get('depth', 0))
        if depth >= max_depth:
            continue
        if parsed(entry['updated_at']) + timedelta(seconds=timeout_seconds) > now:
            continue
        if (entry['id'], depth + 1) in escalated:
            continue
        depth += 1
        followup = dict(payload)
        followup['escalation'] = {'of': entry['id'], 'depth': depth,
                                  'reason': 'No acknowledgement within %d seconds' % timeout_seconds,
                                  'deferred_channels': ['sms', 'ivr'],
                                  'limit': 'SMS/IVR escalation is not connected in this workspace.'}
        followup['checked_at_utc'] = stamp(now)
        new_entry = box.enqueue(entry['watch_id'], entry['correlation_id'],
                                entry['fingerprint_sha256'], 'local_inbox', followup, now=now,
                                dedupe_kind='escalation:%s:%d' % (entry['id'], depth))
        created.append({'id': new_entry['id'], 'of': entry['id'], 'depth': depth})
    return created


def dispatch_outbox(store_path, now=None, send=None, owner=None,
                    lease_seconds=CLAIM_LEASE_SECONDS):
    """Send every due outbox row through its channel and record the outcome.

    store_path is the watches.sqlite path (outbox tables live beside watches).
    The run first reclaims stale claims (crashed workers), promotes due rows
    through the historical created|failed->queued move, claims them under one
    owner+lease, then sends. Rows whose watch window lapsed while queued are
    marked gone, never sent. A purged push subscription marks gone; an
    over-age or budget-spent row marks dead; otherwise failure marks failed
    with jittered backoff. Success marks sent. Returns one summary row per
    dispatch. A sender returning (ok, detail) keeps working; the error class
    is derived by `classify_error`.
    """
    from datetime import timedelta
    now = now or utcnow()
    send = send or default_sender
    owner = owner or ('worker-%s' % uuid.uuid4().hex[:8])
    box = OutboxStore(store_path)
    box.reclaim(now=now)
    try:
        from .watches import WatchStore
        windows = {row['id']: row.get('window_end') for row in WatchStore(store_path).list(now=now)}
    except (SourceError, OSError):
        windows = {}
    # Historical promotion first so the ledger keeps its queued/failed/queued
    # shape; the claim then owns each row for this worker only.
    for entry in box.due(now=now):
        if entry['state'] in ('created', 'failed'):
            box.set_state(entry['id'], 'queued', 'Due for delivery', now=now)
    results = []
    for entry in box.claim(owner, now=now, lease_seconds=lease_seconds):
        window_end = windows.get(entry.get('watch_id'))
        if window_end:
            try:
                lapsed = parsed(window_end) <= now
            except SourceError:
                lapsed = False
            if lapsed:
                row = box.set_state(entry['id'], 'gone', 'Watch window lapsed before delivery',
                                    now=now, error_class='lapsed')
                results.append({'id': entry['id'], 'watch_id': entry['watch_id'], 'channel': entry['channel'],
                                'from': entry['state'], 'to': 'gone', 'error_class': 'lapsed',
                                'detail': 'Watch window lapsed before delivery', 'retry_count': row['retry_count']})
                continue
        try:
            ok, detail = send(entry)
        except Exception as exc:  # A sender must never break the dispatch loop.
            ok, detail = False, 'Sender raised %s: %s' % (type(exc).__name__, exc)
        error_class = None if ok else classify_error(detail)
        if ok:
            row = box.set_state(entry['id'], 'sent', detail, now=now)
        elif error_class == 'purged':
            row = box.set_state(entry['id'], 'gone', detail, now=now, error_class='purged')
        else:
            # set_state('failed') records one failed attempt; the snapshot count
            # decides the move so attempts are never double-counted.
            used = int(entry.get('retry_count') or 0)
            budget = int(entry.get('max_retries') or MAX_RETRIES)
            try:
                age = (now - parsed(entry.get('created_at'))).total_seconds()
            except (SourceError, ValueError, TypeError):
                age = 0
            if used + 1 >= budget:
                row = box.set_state(entry['id'], 'dead', detail, now=now, error_class='retryable')
                error_class = 'retryable'
            elif age >= MAX_RETRY_AGE_SECONDS:
                row = box.set_state(entry['id'], 'dead', 'Retry age exceeded: ' + str(detail),
                                    now=now, error_class='retryable')
            else:
                retry_at = retry_at_with_jitter(now, used + 1)
                row = box.set_state(entry['id'], 'failed', detail, now=now,
                                    next_retry_at=retry_at, error_class='retryable')
        results.append({'id': entry['id'], 'watch_id': entry['watch_id'], 'channel': entry['channel'],
                        'from': entry['state'], 'to': row['state'], 'error_class': error_class,
                        'detail': detail, 'retry_count': row['retry_count']})
    return results
