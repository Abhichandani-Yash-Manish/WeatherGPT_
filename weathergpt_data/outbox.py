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
import json
import sqlite3
import uuid
from datetime import timedelta

from .transport import SourceError, parsed, stamp, utcnow

SCHEMA = 'outbox-v1'
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (60, 300, 900)

# `created` is reserved for a future producer that stages a row before queueing;
# every producer today enqueues directly into `queued`.
STATES = ('created', 'queued', 'sent', 'failed', 'dead', 'acked', 'gone')
TERMINAL_STATES = {'dead', 'acked', 'gone'}
DISPATCHABLE_STATES = {'created', 'queued'}

# Allowed (old_state -> new_state) moves. A failed row may record another failure
# (failed -> failed) while retries remain. `gone` is for rows overtaken by events:
# the watch window lapsed while queued, or the edition was superseded. Terminal
# states (dead, acked, gone) are never re-dispatched.
TRANSITIONS = {
    'created': {'queued', 'dead', 'gone'},
    'queued': {'sent', 'failed', 'dead', 'gone'},
    'sent': {'acked', 'failed', 'dead', 'gone'},
    'failed': {'queued', 'failed', 'dead', 'gone'},
    'dead': set(),
    'acked': set(),
    'gone': set(),
}

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
            db.commit()
        finally:
            db.close()

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

    def enqueue(self, watch_id, correlation_id, fingerprint_sha256, channel, payload, now=None):
        """Enqueue one notification in queued state and record the ledger event."""
        now = now or utcnow()
        entry = {'id': str(uuid.uuid4()), 'watch_id': watch_id, 'correlation_id': correlation_id,
                 'fingerprint_sha256': fingerprint_sha256, 'state': 'queued', 'channel': channel,
                 'payload': payload, 'created_at': stamp(now), 'updated_at': stamp(now),
                 'retry_count': 0, 'max_retries': MAX_RETRIES, 'next_retry_at': None, 'last_error': None}
        db = sqlite3.connect(self.path)
        try:
            db.execute('INSERT INTO outbox VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (entry['id'], watch_id, correlation_id, fingerprint_sha256, 'queued', channel,
                        json.dumps(payload, ensure_ascii=False), entry['created_at'], entry['updated_at'],
                        0, MAX_RETRIES, None, None))
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
        Returns the list of enqueued entries.
        """
        now = now or utcnow()
        entries = [{'id': str(uuid.uuid4()), 'watch_id': watch_id, 'correlation_id': correlation_id,
                    'fingerprint_sha256': fingerprint_sha256, 'state': 'queued', 'channel': channel,
                    'payload': payload, 'created_at': stamp(now), 'updated_at': stamp(now),
                    'retry_count': 0, 'max_retries': MAX_RETRIES, 'next_retry_at': None, 'last_error': None}
                   for channel in channels]
        db = sqlite3.connect(self.path)
        try:
            for entry in entries:
                db.execute('INSERT INTO outbox VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                           (entry['id'], watch_id, correlation_id, fingerprint_sha256, 'queued',
                            entry['channel'], json.dumps(payload, ensure_ascii=False),
                            entry['created_at'], entry['updated_at'], 0, MAX_RETRIES, None, None))
                self._record(db, entry['id'], 'queued',
                             {'channel': entry['channel'], 'correlation_id': correlation_id,
                              'fingerprint_sha256': fingerprint_sha256}, now)
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

    def set_state(self, outbox_id, new_state, detail=None, now=None, next_retry_at=None):
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
            if new_state in ('sent', 'acked'):
                retry_at = None
            db.execute('UPDATE outbox SET state=?,updated_at=?,retry_count=?,next_retry_at=?,last_error=? WHERE id=?',
                       (new_state, stamp(now), retry_count, retry_at, last_error, outbox_id))
            self._record(db, outbox_id, new_state,
                         {'from': current['state'], 'detail': detail, 'retry_count': retry_count}, now)
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
        dispatcher marks them dead.
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
                                entry['fingerprint_sha256'], 'local_inbox', followup, now=now)
        created.append({'id': new_entry['id'], 'of': entry['id'], 'depth': depth})
    return created


def dispatch_outbox(store_path, now=None, send=None):
    """Send every due outbox row through its channel and record the outcome.

    store_path is the watches.sqlite path (outbox tables live beside watches).
    Rows whose watch window lapsed while queued are marked gone, never sent.
    Success marks sent; failure marks failed with a backoff while retries remain
    and dead once MAX_RETRIES is reached. Returns one summary row per dispatch.
    """
    from datetime import timedelta
    now = now or utcnow()
    send = send or default_sender
    box = OutboxStore(store_path)
    try:
        from .watches import WatchStore
        windows = {row['id']: row.get('window_end') for row in WatchStore(store_path).list(now=now)}
    except (SourceError, OSError):
        windows = {}
    results = []
    for entry in box.due(now=now):
        window_end = windows.get(entry.get('watch_id'))
        if window_end:
            try:
                lapsed = parsed(window_end) <= now
            except SourceError:
                lapsed = False
            if lapsed:
                row = box.set_state(entry['id'], 'gone', 'Watch window lapsed before delivery', now=now)
                results.append({'id': entry['id'], 'watch_id': entry['watch_id'], 'channel': entry['channel'],
                                'from': entry['state'], 'to': 'gone',
                                'detail': 'Watch window lapsed before delivery', 'retry_count': row['retry_count']})
                continue
        if entry['state'] in ('created', 'failed'):
            box.set_state(entry['id'], 'queued', 'Due for delivery', now=now)
        try:
            ok, detail = send(entry)
        except Exception as exc:  # A sender must never break the dispatch loop.
            ok, detail = False, 'Sender raised %s: %s' % (type(exc).__name__, exc)
        if ok:
            row = box.set_state(entry['id'], 'sent', detail, now=now)
        else:
            # set_state('failed') records one failed attempt; the snapshot count
            # decides the move so attempts are never double-counted.
            used = int(entry.get('retry_count') or 0)
            budget = int(entry.get('max_retries') or MAX_RETRIES)
            if used + 1 >= budget:
                row = box.set_state(entry['id'], 'dead', detail, now=now)
            else:
                retry_at = stamp(now + timedelta(seconds=retry_delay(used + 1)))
                row = box.set_state(entry['id'], 'failed', detail, now=now, next_retry_at=retry_at)
        results.append({'id': entry['id'], 'watch_id': entry['watch_id'], 'channel': entry['channel'],
                        'from': entry['state'], 'to': row['state'], 'detail': detail,
                        'retry_count': row['retry_count']})
    return results
