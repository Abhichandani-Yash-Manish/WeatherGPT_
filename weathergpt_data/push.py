"""Web push for watch notifications: VAPID keys, subscriptions, sending.

A browser that grants notification permission registers the service worker and
subscribes; the subscription is stored here, bound to a watch or to every
watch. Dispatch sends the outbox payload through the push service with VAPID
authentication. A 410 Gone (or 404) response retires the subscription so dead
endpoints are never retried. Nothing here invents warning content: the push
body is the outbox payload's official facts, verbatim.

VAPID keys live in a gitignored JSON file beside the runtime databases. The
private key is stored as a 32-octet base64url scalar because the installed
py-vapid release cannot reload its own PEM output.
"""
import base64
import json
import sqlite3
import uuid
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization

from .transport import SourceError, stamp, utcnow

SCHEMA = 'push-v1'
# Local prototype identifier for the VAPID subject claim. This workspace has no
# public contact URL; the claim names the loopback origin it runs on.
VAPID_SUBJECT = 'http://127.0.0.1/'
PUSH_TTL_SECONDS = 3600


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def public_b64url(vapid):
    """The applicationServerKey the browser subscribes with."""
    point = vapid.public_key.public_bytes(serialization.Encoding.X962,
                                          serialization.PublicFormat.UncompressedPoint)
    return _b64url(point)


def vapid_keypair(key_path):
    """Load the VAPID pair from key_path, generating and storing it on first use.

    Returns (vapid_instance, public_b64url). The file holds the private scalar
    and the public point; it must stay out of version control with the runtime
    databases.
    """
    key_path = key_path if hasattr(key_path, 'read_text') else __import__('pathlib').Path(key_path)
    if key_path.exists():
        try:
            record = json.loads(key_path.read_text(encoding='utf-8'))
            private_raw, public_key = record['private_raw_b64url'], record['public_b64url']
        except (ValueError, KeyError, OSError) as exc:
            raise SourceError('Stored VAPID keys are unreadable: ' + str(exc)) from exc
    else:
        from py_vapid import Vapid
        vapid = Vapid()
        vapid.generate_keys()
        private_raw = _b64url(vapid.private_key.private_numbers().private_value.to_bytes(32, 'big'))
        public_key = public_b64url(vapid)
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(json.dumps({'schema_version': 'vapid-key-v1', 'private_raw_b64url': private_raw,
                                        'public_b64url': public_key}, indent=2) + '\n', encoding='utf-8')
        return vapid, public_key
    from py_vapid import Vapid
    try:
        vapid = Vapid.from_raw(private_raw.encode())
    except (ValueError, TypeError) as exc:
        raise SourceError('Stored VAPID keys are invalid: ' + str(exc)) from exc
    if public_b64url(vapid) != public_key:
        raise SourceError('Stored VAPID public key does not match the private key')
    return vapid, public_key


def validate_subscription(endpoint, p256dh, auth):
    """Reject malformed push subscriptions before they are stored."""
    if not isinstance(endpoint, str):
        raise SourceError('Push subscription needs an endpoint URL')
    parts = urlparse(endpoint)
    if parts.scheme != 'https' or not parts.netloc:
        raise SourceError('Push subscription endpoint must be an https URL')
    for name, value in (('p256dh', p256dh), ('auth', auth)):
        if not isinstance(value, str) or not value.strip():
            raise SourceError('Push subscription needs a ' + name + ' key')
        try:
            base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))
        except (ValueError, TypeError) as exc:
            raise SourceError('Push subscription ' + name + ' is not base64url: ' + str(exc)) from exc


class PushStore:
    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        try:
            db.execute('CREATE TABLE IF NOT EXISTS push_subscriptions (id TEXT PRIMARY KEY,endpoint TEXT,'
                       'p256dh TEXT,auth TEXT,watch_id TEXT,state TEXT,created_at TEXT,expires_at TEXT)')
            db.commit()
        finally:
            db.close()

    def subscribe(self, endpoint, p256dh, auth, watch_id=None, expires_at=None, now=None):
        from .watches import WatchStore
        now = now or utcnow()
        validate_subscription(endpoint, p256dh, auth)
        if watch_id is not None:
            WatchStore(self.path).get(str(watch_id))
        entry = {'id': str(uuid.uuid4()), 'endpoint': endpoint, 'p256dh': p256dh, 'auth': auth,
                 'watch_id': str(watch_id) if watch_id is not None else None,
                 'state': 'active', 'created_at': stamp(now), 'expires_at': expires_at}
        db = sqlite3.connect(self.path)
        try:
            db.execute('INSERT INTO push_subscriptions VALUES (?,?,?,?,?,?,?,?)',
                       (entry['id'], endpoint, p256dh, auth, entry['watch_id'], 'active',
                        entry['created_at'], expires_at))
            db.commit()
        finally:
            db.close()
        return entry

    def list(self, state=None, watch_id=None):
        query = 'SELECT * FROM push_subscriptions'
        clauses, args = [], []
        if state is not None:
            clauses.append('state=?'); args.append(state)
        if watch_id is not None:
            clauses.append('watch_id=?'); args.append(str(watch_id))
        if clauses:
            query += ' WHERE ' + ' AND '.join(clauses)
        query += ' ORDER BY created_at DESC'
        db = sqlite3.connect(self.path)
        try:
            db.row_factory = sqlite3.Row
            rows = [dict(row) for row in db.execute(query, args)]
        finally:
            db.close()
        return rows

    def active_for_watch(self, watch_id):
        """Active subscriptions bound to this watch, plus unbound ones (every watch)."""
        watch_id = str(watch_id)
        return [row for row in self.list(state='active')
                if row.get('watch_id') in (None, watch_id)]

    def set_state(self, subscription_id, state, now=None):
        if state not in ('active', 'expired', 'revoked'):
            raise SourceError('Unknown subscription state: ' + str(state))
        db = sqlite3.connect(self.path)
        try:
            cursor = db.execute('UPDATE push_subscriptions SET state=? WHERE id=?', (state, subscription_id))
            if cursor.rowcount == 0:
                raise SourceError('No push subscription with this identifier')
            db.commit()
        finally:
            db.close()

    def unsubscribe(self, endpoint, now=None):
        db = sqlite3.connect(self.path)
        try:
            cursor = db.execute("UPDATE push_subscriptions SET state='revoked' WHERE endpoint=? AND state='active'",
                                (endpoint,))
            db.commit()
            revoked = cursor.rowcount
        finally:
            db.close()
        if not revoked:
            raise SourceError('No active push subscription for this endpoint')
        return {'endpoint': endpoint, 'revoked': revoked}

    def purge_expired(self, now=None):
        """Retire subscriptions past their expiry. Returns the retired count."""
        from .transport import parsed
        now = now or utcnow()
        retired = 0
        for row in self.list(state='active'):
            expires_at = row.get('expires_at')
            if expires_at is not None and parsed(expires_at) <= now:
                self.set_state(row['id'], 'expired', now=now)
                retired += 1
        return {'retired': retired}


def push_payload(entry):
    """The push message for one outbox row: official facts, verbatim, under 4KB intent."""
    payload = entry.get('payload') or {}
    facts = payload.get('facts') or []
    first = facts[0] if facts else {}
    title = 'WeatherGPT watch: ' + str(payload.get('hazard') or 'official warning')
    lines = []
    if payload.get('place', {}).get('name'):
        lines.append(str(payload['place']['name']))
    if first.get('label') and first.get('value'):
        lines.append(str(first['label']) + ': ' + str(first['value']))
    lines.append('A no-match result is not an all-clear.' if not payload.get('matched')
                 else 'Official product state, not an instruction.')
    body = ' · '.join(lines)[:500]
    return {'title': title[:120], 'body': body,
            'watch_id': payload.get('watch_id'), 'outbox_id': entry.get('id'),
            'checked_at_utc': payload.get('checked_at_utc')}


def send_push(entry, vapid, subscriptions):
    """Send one outbox row to its subscriptions. Never raises.

    Returns {'delivered': [...ids], 'purged': [...ids], 'errors': [...]}. A 410
    Gone or 404 marks that subscription for retirement by the caller.
    """
    from pywebpush import WebPushException, webpush
    message = json.dumps(push_payload(entry), ensure_ascii=False)
    delivered, purged, errors = [], [], []
    for sub in subscriptions:
        try:
            webpush({'endpoint': sub['endpoint'],
                     'keys': {'p256dh': sub['p256dh'], 'auth': sub['auth']}},
                    message, vapid_private_key=vapid,
                    vapid_claims={'sub': VAPID_SUBJECT}, ttl=PUSH_TTL_SECONDS)
            delivered.append(sub['id'])
        except WebPushException as exc:
            status = getattr(exc.response, 'status_code', None) if exc.response is not None else None
            if status in (404, 410):
                purged.append(sub['id'])
            else:
                errors.append({'subscription': sub['id'], 'status': status, 'detail': str(exc)[:200]})
        except Exception as exc:  # Network failure: retryable, never fatal.
            errors.append({'subscription': sub['id'], 'status': None,
                           'detail': '%s: %s' % (type(exc).__name__, str(exc)[:200])})
    return {'delivered': delivered, 'purged': purged, 'errors': errors}


def channel_sender(key_path, db_path):
    """A dispatch_outbox sender: local inbox inline, web push through subscriptions."""
    from .outbox import OutboxStore, default_sender
    def send(entry):
        if entry.get('channel') != 'web_push':
            return default_sender(entry)
        box = OutboxStore(db_path)
        store = PushStore(db_path)
        try:
            vapid, _ = vapid_keypair(key_path)
        except SourceError as exc:
            return False, 'VAPID keys unavailable: ' + str(exc)
        targets = store.active_for_watch(entry.get('watch_id'))
        if not targets:
            return False, 'No active push subscription for this watch'
        outcome = send_push(entry, vapid, targets)
        for subscription_id in outcome['purged']:
            try:
                store.set_state(subscription_id, 'expired')
            except SourceError:
                pass
        if outcome['delivered']:
            return True, 'Pushed to %d subscription(s)' % len(outcome['delivered'])
        if outcome['errors'] and not outcome['purged']:
            first = outcome['errors'][0]
            return False, 'Push failed: %s' % (first.get('detail') or 'unknown error')
        return False, 'Every push subscription for this watch expired and was retired'
    return send
