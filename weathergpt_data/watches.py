"""Local watch requests: registered, evaluated on demand, never delivered silently.

A request to be notified is a request the workspace must answer explicitly. What it can
honestly do without hosting, push or a background daemon is: record the watch with the
place and hazard it resolved, name the official products it will check, and evaluate the
watch only when it is asked to. A no-match result is not an all-clear, and a hazard the
connected official products do not carry (a flood warning, for example) is recorded as
not connected rather than mapped onto a similar-sounding product.
"""
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from .transport import SourceError, parsed, stamp, utcnow

# Columns added after the original 10-column schema. _migrate() applies them to
# existing databases; new code always reads/writes them.
WATCH_SCHEMA_EXTRA = (('fingerprint_sha256', 'TEXT'), ('channels', 'TEXT'), ('consent_record', 'TEXT'))

DEFAULT_CHANNELS = ['local_inbox']
CONNECTED_CHANNELS = ('local_inbox', 'web_push')
CONSENT_SOURCES = ('explicit_chat_request', 'browser_push_grant')


def _dedupe_key(place, hazard, window_start, window_end):
    """Identity of an equivalent subscription: place + hazard + window.

    Coordinates are rounded to ~10 m so repeated pins of the same place match;
    a named place without coordinates keys on its normalised name and state.
    """
    place = place or {}
    coords = place.get('coordinates') or {}
    try:
        lat = round(float(coords.get('latitude')), 4)
        lon = round(float(coords.get('longitude')), 4)
        point = '%s,%s' % (lat, lon)
    except (TypeError, ValueError):
        point = 'name:' + re.sub(r'\s+', ' ', str(place.get('name') or '').strip().lower()) \
                + '|state:' + str(place.get('state') or '').strip().lower()
    return (point, hazard, window_start or '', window_end or '')


def _decode_json_list(raw, fallback):
    try:
        value = json.loads(raw) if raw else fallback
    except ValueError:
        return list(fallback)
    return value if isinstance(value, list) else list(fallback)


def _decode_json_dict(raw):
    try:
        value = json.loads(raw) if raw else {}
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def default_consent(now=None):
    """Consent record for the local inbox: the watch itself was an explicit request."""
    return {'local_inbox': {'granted_at': stamp(now or utcnow()), 'source': 'explicit_chat_request'}}


def compute_fingerprint(watch_id, hazard, place_name, facts, reason, packet_status,
                        cap_eligible=None, cap_messages=None):
    """Deterministic SHA-256 of the official state that matters to one watch.

    Inputs are the structured warning facts (never the rendered answer text, which
    can carry retrieval timestamps) plus the CAP relay counts the warning tool
    records. A colour-code change, a new hazard code, a CAP lifecycle move, or a
    different evaluation reason all change the fingerprint; an identical official
    state reproduces it, which is what makes duplicate suppression exact.

    Implemented in :mod:`warning_state` (canon-v1); this wrapper preserves the
    historical hash byte-for-byte so stored fingerprints stay valid.
    """
    from .warning_state import canonical_input, fingerprint
    return fingerprint(canonical_input(watch_id, hazard, place_name, facts, reason,
                                       packet_status, cap_eligible, cap_messages))


def _cap_counts(packet):
    """CAP relay counts the warning tool recorded in the packet trace, if any."""
    for tool in (packet.get('trace') or {}).get('tools') or []:
        if isinstance(tool, dict) and 'cap_lifecycle_eligible' in tool:
            return tool.get('cap_lifecycle_eligible'), tool.get('cap_messages')
    return None, None

# The district warning layer's own hazard codes, as read in docs/27. Only the codes
# observed in the feed are mapped; an unlisted code stays unmapped and is never called
# a match for the user's words.
HAZARD_CODES = {
    'heavy_rain': {2, 16, 17},
    'thunderstorm': {4},
    'strong_wind': {8},
}
HAZARD_WORDS = [
    ('heavy_rain', r'heavy rain|very heavy rain|extremely heavy rain|rainfall|barish|बारिश|વરસાદ'),
    ('thunderstorm', r'thunderstorm|lightning|squall|gale|आंधी|તોફાન'),
    ('strong_wind', r'strong wind|high wind|wind warning|gusts|हवा|પવન'),
    ('flood', r'flood|inundation|बाढ़|પૂર'),
    ('cyclone', r'cyclone|storm surge|समुद्री तूफान|ચક્રવાત'),
    ('heat', r'heat ?wave|loo|लू'),
    ('cold', r'cold ?wave|शीतलहर'),
]
WATCH_INTENT = re.compile(
    r'\b(?:notify|alert|inform|tell|warn)\s+(?:me|us)\b[^.?!]{0,120}\b(?:if|when|whenever|should|in case)\b', re.I)
UNCONNECTED = {'flood', 'cyclone', 'heat', 'cold'}


def watch_intent(question):
    """True when the user asked to be notified rather than only answered once."""
    return bool(WATCH_INTENT.search(question or ''))


def hazard_of(question):
    text = question or ''
    for hazard, pattern in HAZARD_WORDS:
        if re.search(pattern, text, re.I):
            return hazard
    return 'any_official_warning'


def connected(hazard):
    """Whether the connected official products actually carry this hazard."""
    return hazard not in UNCONNECTED


def evaluate(packet, hazard):
    """Pure evaluation of a warning packet against a hazard. Returns match and basis."""
    if not connected(hazard):
        return {'matched': False, 'reason': 'hazard_not_connected',
                'detail': 'The connected official products are the IMD district warning product and the CAP relay; neither carries a '
                          'flood or cyclone warning product. This watch is recorded, but it cannot be satisfied by mapping your words '
                          'onto a similar-sounding product.'}
    codes = HAZARD_CODES.get(hazard, set())
    matched = []
    unmapped = set()
    for fact in packet.get('facts') or []:
        if fact.get('parameter') != 'official_district_warning':
            continue
        if fact.get('quiet'):
            continue
        found = set(fact.get('hazard_codes') or [])
        if not found:
            continue
        if hazard == 'any_official_warning' or found & codes:
            matched.append({'fact_id': fact.get('id'), 'label': fact.get('label'), 'value': fact.get('value'),
                            'start': fact.get('start'), 'end': fact.get('end'), 'source_id': fact.get('source_id')})
        else:
            unmapped |= found
    if matched:
        return {'matched': True, 'reason': 'current_official_district_hazard_matches',
                'detail': 'The IMD district warning product reports a current day matching this watch. This is official product state, '
                          'not an instruction, and origin authentication remains unverified.',
                'facts': matched[:4]}
    return {'matched': False, 'reason': 'no_matching_current_official_day',
            'detail': 'No current day of the connected official district warning product matches this watch for the resolved district. '
                      'This is not an all-clear and it does not cover products that are not connected.',
            'unmapped_hazard_codes': sorted(unmapped)}


class WatchStore:
    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS watches (id TEXT PRIMARY KEY,created_at TEXT,question TEXT,place TEXT,hazard TEXT,'
                       'window_start TEXT,window_end TEXT,state TEXT,last_checked_at TEXT,result TEXT)')
            self._migrate(db)
            db.commit()
        finally:
            db.close()

    def _migrate(self, db):
        """Add change-detection, channel and consent columns to pre-existing stores."""
        cols = {row[1] for row in db.execute('PRAGMA table_info(watches)').fetchall()}
        for name, decl in WATCH_SCHEMA_EXTRA:
            if name not in cols:
                db.execute('ALTER TABLE watches ADD COLUMN %s %s' % (name, decl))

    def create(self, question, place, hazard, window_start=None, window_end=None, now=None,
                channels=None, consent_record=None):
        now = now or utcnow()
        for existing in self.list(now=now):
            if existing.get('expired') or existing.get('state') == 'expired':
                continue
            if _dedupe_key(existing.get('place'), existing.get('hazard'),
                           existing.get('window_start'), existing.get('window_end')) == \
               _dedupe_key(place, hazard, window_start, window_end):
                found = dict(existing, duplicate=True)
                # Stored rows predate the inline summary fields create()
                # returns; fill the stable defaults so callers see one shape.
                found.setdefault('delivery', 'local_inbox_only_no_push')
                return found
        channels = list(channels) if channels else list(DEFAULT_CHANNELS)
        consent_record = consent_record if isinstance(consent_record, dict) else default_consent(now)
        watch = {'id': str(uuid.uuid4()), 'created_at': stamp(now), 'question': question, 'place': place, 'hazard': hazard,
                 'window_start': window_start, 'window_end': window_end,
                 'state': 'registered_check_on_request', 'delivery': 'local_inbox_only_no_push',
                 'checked_products': ['S15 IMD district warning product', 'S06 CAP relay assessment'],
                 'not_connected': [h for h in UNCONNECTED if h == hazard],
                 'fingerprint_sha256': None, 'channels': channels, 'consent_record': consent_record}
        db = sqlite3.connect(self.path)
        try:
            db.execute('INSERT INTO watches (id,created_at,question,place,hazard,window_start,window_end,state,'
                       'last_checked_at,result,fingerprint_sha256,channels,consent_record)'
                       ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (watch['id'], watch['created_at'], question, json.dumps(place, ensure_ascii=False), hazard,
                        window_start, window_end, watch['state'], None, None, None,
                        json.dumps(channels, ensure_ascii=False), json.dumps(consent_record, ensure_ascii=False)))
            db.commit()
        finally:
            db.close()
        return watch

    @staticmethod
    def _decode(item):
        try:
            item['place'] = json.loads(item['place'] or '{}')
        except ValueError:
            item['place'] = {}
        if not isinstance(item['place'], dict):
            item['place'] = {}
        try:
            item['result'] = json.loads(item['result']) if item.get('result') else None
        except ValueError:
            item['result'] = None
        if item['result'] is not None and not isinstance(item['result'], dict):
            item['result'] = None
        item['channels'] = _decode_json_list(item.get('channels'), DEFAULT_CHANNELS)
        item['consent_record'] = _decode_json_dict(item.get('consent_record'))
        return item

    def list(self, now=None):
        now = now or utcnow()
        rows = []
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            for row in db.execute('SELECT * FROM watches ORDER BY created_at DESC'):
                item = self._decode(dict(row))
                item['expired'] = bool(item.get('window_end') and parsed(item['window_end']) < now)
                rows.append(item)
        finally:
            db.close()
        return rows

    def mark(self, watch_id, state, last_checked_at, result):
        db = sqlite3.connect(self.path)
        try:
            db.execute('UPDATE watches SET state=?,last_checked_at=?,result=? WHERE id=?',
                       (state, last_checked_at, json.dumps(result, ensure_ascii=False), watch_id))
            db.commit()
        finally:
            db.close()

    def get(self, watch_id):
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM watches WHERE id=?', (watch_id,)).fetchone()
        finally:
            db.close()
        if row is None:
            raise SourceError('No local watch with this identifier')
        return self._decode(dict(row))

    def set_fingerprint(self, watch_id, fingerprint):
        db = sqlite3.connect(self.path)
        try:
            db.execute('UPDATE watches SET fingerprint_sha256=? WHERE id=?', (fingerprint, watch_id))
            db.commit()
        finally:
            db.close()

    def set_channels(self, watch_id, channels, consent_source=None, now=None):
        """Replace the delivery channels of one watch, keeping consent honest.

        local_inbox can never be removed: the inbox is the base truth every watch
        keeps. Unknown channels raise. Added non-inbox channels gain a consent entry
        stamped with the given source (which must name the real grant); removed
        channels lose theirs. Returns the updated watch.
        """
        now = now or utcnow()
        watch = self.get(watch_id)
        channels = list(channels or [])
        unknown = [channel for channel in channels if channel not in CONNECTED_CHANNELS]
        if unknown:
            raise SourceError('Unknown delivery channel: ' + ', '.join(sorted(set(unknown))))
        if 'local_inbox' not in channels:
            raise SourceError('local_inbox cannot be removed from a watch')
        if consent_source is not None and consent_source not in CONSENT_SOURCES:
            raise SourceError('Unknown consent source: ' + str(consent_source))
        consent = dict(watch.get('consent_record') or {})
        if consent_source is not None:
            for channel in channels:
                if channel != 'local_inbox' and channel not in consent:
                    consent[channel] = {'granted_at': stamp(now), 'source': consent_source}
        for channel in list(consent):
            if channel != 'local_inbox' and channel not in channels:
                del consent[channel]
        db = sqlite3.connect(self.path)
        try:
            db.execute('UPDATE watches SET channels=?,consent_record=? WHERE id=?',
                       (json.dumps(channels, ensure_ascii=False),
                        json.dumps(consent, ensure_ascii=False), watch_id))
            db.commit()
        finally:
            db.close()
        return self.get(watch_id)

    def archive(self, watch_id, now=None):
        """Retire a watch and cancel every undelivered notification. Returns cancelled count."""
        from .outbox import OutboxStore
        now = now or utcnow()
        self.get(watch_id)
        box = OutboxStore(self.path)
        cancelled = 0
        for entry in box.list(watch_id=watch_id):
            if entry['state'] in ('created', 'queued', 'failed', 'sent'):
                box.set_state(entry['id'], 'dead', 'Watch archived by the owner', now=now)
                cancelled += 1
        db = sqlite3.connect(self.path)
        try:
            db.execute('UPDATE watches SET state=?,last_checked_at=? WHERE id=?',
                       ('expired', stamp(now), watch_id))
            db.commit()
        finally:
            db.close()
        return {'id': watch_id, 'state': 'expired', 'cancelled_notifications': cancelled}


def check_watch(store, engine, watch, now=None, correlation_id=None):
    """Run the official warning tool for one watch and record the outcome.

    Change detection: the observed official state is fingerprinted and compared
    with the stored fingerprint. An unreachable source holds: nothing is enqueued
    and the fingerprint does not move. The first readable check establishes the
    baseline and enqueues nothing; a later check whose fingerprint differs enqueues
    one outbox row per deliverable channel and stores the new fingerprint in the
    same transaction; an identical state enqueues nothing. A hazard the connected
    products do not carry never enqueues, though its fingerprint still advances.
    Dispatch (sending) happens separately in dispatch_outbox.
    """
    from .outbox import OutboxStore, build_notification_payload
    from .warning_state import build_snapshot, detect, snapshot_from_stored
    from .warning_tools import execute_warning
    now = now or utcnow()
    if watch.get('window_end') and parsed(watch['window_end']) < now:
        store.mark(watch['id'], 'expired', stamp(now), {'reason': 'window_ended', 'detail': 'The watch window ended before this check.'})
        return {'id': watch['id'], 'state': 'expired', 'matched': False, 'detail': 'The watch window ended before this check.'}
    plan = {'places': [watch['place']], 'language': 'en'}
    task = {'kind': 'warning', 'operation': 'lookup', 'parameters': ['official_warning'], 'years': [], 'period': 'annual',
            'start_local': watch.get('window_start') or '', 'end_local': watch.get('window_end') or '',
            'place_indices': [0], 'request_quote': watch['question']}
    packet = {'facts': [], 'citations': [], 'notes': [], 'trace': {'tools': [], 'generation': None},
              'question': watch['question'], 'plan': plan, 'status': 'unavailable'}
    packet = execute_warning(engine, packet, plan, task)
    outcome = evaluate(packet, watch['hazard'])
    state = 'matched' if outcome['matched'] else ('hazard_not_connected' if outcome['reason'] == 'hazard_not_connected' else 'checked_no_match')
    store.mark(watch['id'], state, stamp(now), {**outcome, 'packet_status': packet.get('status'), 'packet_answer': packet.get('answer')})
    result = {'id': watch['id'], 'state': state, 'matched': outcome['matched'], 'detail': outcome['detail'],
              'packet_status': packet.get('status'), 'packet_answer': packet.get('answer')}
    place = watch.get('place') or {}
    cap_eligible, cap_messages = _cap_counts(packet)
    new_snapshot = build_snapshot(watch['id'], watch.get('hazard'), place.get('name'),
                                  packet.get('facts'), outcome.get('reason'), packet.get('status'),
                                  cap_eligible, cap_messages, matched=outcome['matched'])
    fingerprint = new_snapshot['fingerprint_sha256']
    result['fingerprint_sha256'] = fingerprint
    result['notification'] = None
    result['notifications'] = []
    result['channels_notified'] = []
    result['channels_skipped'] = []
    old_snapshot = snapshot_from_stored(watch)
    # First readable check always establishes the baseline silently — even for
    # hazards the connected products do not carry (historical behaviour pinned
    # by UnconnectedHeldTests). Unavailable holds regardless of check number.
    event = detect(old_snapshot, new_snapshot,
                   unavailable=(packet.get('status') == 'unavailable'),
                   not_connected=(old_snapshot is not None
                                  and outcome.get('reason') == 'hazard_not_connected'
                                  and packet.get('status') != 'unavailable'))
    result['change_kind'] = event['kind']
    if event['kind'] == 'held':
        if event['reason'] == 'not_connected_held':
            # Historical behaviour: the state advances (so oscillation is
            # visible) but nothing is ever enqueued for unconnected hazards.
            store.set_fingerprint(watch['id'], fingerprint)
        result['fingerprint_basis'] = event['reason']
        return result
    if event['kind'] == 'baseline':
        store.set_fingerprint(watch['id'], fingerprint)
        result['fingerprint_basis'] = 'baseline'
    elif event['kind'] == 'no_change':
        result['fingerprint_basis'] = 'unchanged'
    else:
        from .push import deliverable_channels
        correlation_id = correlation_id or str(uuid.uuid4())
        payload = build_notification_payload(watch, outcome, packet.get('facts'), packet.get('status'), now=now)
        payload['change_kind'] = event['kind']
        payload['change_reason'] = event['reason']
        channels, skipped = deliverable_channels(store.path, watch, now=now)
        notified = OutboxStore(store.path).enqueue_changed(
            watch['id'], correlation_id, fingerprint, channels, payload, now=now)
        result['notification'] = notified[0]['id'] if notified else None
        result['notifications'] = [entry['id'] for entry in notified]
        result['channels_notified'] = channels
        result['channels_skipped'] = skipped
        result['fingerprint_basis'] = 'changed'
    return result


@contextmanager
def check_lock(store_path):
    """One check run at a time per store: a second holder gets a clean refusal.

    The fingerprint compare-and-set plus enqueue is only exact when a single run
    owns it; concurrent runs would double-enqueue the same change. Source fetch
    budgets remain unmetered — this lock orders runs, it does not pace sources.
    """
    from .filelock import try_lock_exclusive, unlock
    handle = open(store_path.with_suffix('.watch-check.lock'), 'a')
    try:
        try:
            try_lock_exclusive(handle)
        except BlockingIOError:
            raise SourceError('Another watch check is already running') from None
        yield
    finally:
        try:
            unlock(handle)
        finally:
            handle.close()


def check_due(store, engine, now=None):
    now = now or utcnow()
    correlation_id = str(uuid.uuid4())
    results = []
    with check_lock(store.path):
        for watch in store.list(now=now):
            if watch.get('state') in {'expired'}:
                continue
            results.append(check_watch(store, engine, watch, now=now, correlation_id=correlation_id))
    return results


HEARTBEAT_SCHEMA = 'watch-heartbeat-v1'


def heartbeat_path(store_path):
    """Where the last successful watch-check run records its tick (gitignored runtime)."""
    from pathlib import Path
    return Path(store_path).parent / 'watch-heartbeat.json'


def record_heartbeat(store_path, tick, now=None):
    """Atomically record one watch-check run tick. Never raises for I/O reasons.

    `tick` carries trigger/cycle/owner/counts; bookkeeping (schema, tick time)
    is added here. A failed write returns False so callers can note it, but a
    monitoring tick must never break the run it reports on.
    """
    import os
    import tempfile
    now = now or utcnow()
    path = heartbeat_path(store_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {'schema_version': HEARTBEAT_SCHEMA, 'tick_at_utc': stamp(now)}
        record.update(tick or {})
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         delete=False) as output:
            temporary = output.name
            json.dump(record, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        return True
    except OSError:
        try:
            if 'temporary' in dir() and os.path.exists(temporary):
                os.unlink(temporary)
        except OSError:
            pass
        return False


def read_heartbeat(store_path):
    """The last recorded tick, or None when no runner ever reported (or it is unreadable)."""
    path = heartbeat_path(store_path)
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return record if isinstance(record, dict) else None


def heartbeat_status(heartbeat, now=None):
    """Fresh/stale verdict for a heartbeat. Stale means nobody is checking.

    Each tick names its own `stale_after_seconds` (daemon: two intervals plus
    grace; manual: one hour). Absent or unreadable heartbeats are stale by
    definition — the supervisor cannot prove a check ever ran.
    """
    now = now or utcnow()
    if not isinstance(heartbeat, dict) or not heartbeat.get('tick_at_utc'):
        return {'fresh': False, 'age_seconds': None, 'reason': 'no watch-check run has ever reported'}
    try:
        age = (now - parsed(heartbeat['tick_at_utc'])).total_seconds()
    except (SourceError, ValueError, TypeError):
        return {'fresh': False, 'age_seconds': None, 'reason': 'the recorded tick time is unreadable'}
    stale_after = heartbeat.get('stale_after_seconds')
    try:
        stale_after = float(stale_after)
    except (TypeError, ValueError):
        stale_after = 3600.0
    if age <= stale_after:
        return {'fresh': True, 'age_seconds': age, 'reason': 'a check run reported within its freshness window'}
    return {'fresh': False, 'age_seconds': age,
            'reason': 'the last reported check run is older than its freshness window'}
