"""Local watch requests: registered, evaluated on demand, never delivered silently.

A request to be notified is a request the workspace must answer explicitly. What it can
honestly do without hosting, push or a background daemon is: record the watch with the
place and hazard it resolved, name the official products it will check, and evaluate the
watch only when it is asked to. A no-match result is not an all-clear, and a hazard the
connected official products do not carry (a flood warning, for example) is recorded as
not connected rather than mapped onto a similar-sounding product.
"""
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone

from .transport import SourceError, parsed, stamp, utcnow

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
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS watches (id TEXT PRIMARY KEY,created_at TEXT,question TEXT,place TEXT,hazard TEXT,'
                       'window_start TEXT,window_end TEXT,state TEXT,last_checked_at TEXT,result TEXT)')

    def create(self, question, place, hazard, window_start=None, window_end=None, now=None):
        now = now or utcnow()
        watch = {'id': str(uuid.uuid4()), 'created_at': stamp(now), 'question': question, 'place': place, 'hazard': hazard,
                 'window_start': window_start, 'window_end': window_end,
                 'state': 'registered_check_on_request', 'delivery': 'local_inbox_only_no_push',
                 'checked_products': ['S15 IMD district warning product', 'S06 CAP relay assessment'],
                 'not_connected': [h for h in UNCONNECTED if h == hazard]}
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO watches VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (watch['id'], watch['created_at'], question, json.dumps(place, ensure_ascii=False), hazard,
                        window_start, window_end, watch['state'], None, None))
        return watch

    def list(self, now=None):
        now = now or utcnow()
        rows = []
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            for row in db.execute('SELECT * FROM watches ORDER BY created_at DESC'):
                item = dict(row)
                item['place'] = json.loads(item['place'] or '{}')
                item['result'] = json.loads(item['result']) if item.get('result') else None
                item['expired'] = bool(item.get('window_end') and parsed(item['window_end']) < now)
                rows.append(item)
        return rows

    def mark(self, watch_id, state, last_checked_at, result):
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE watches SET state=?,last_checked_at=?,result=? WHERE id=?',
                       (state, last_checked_at, json.dumps(result, ensure_ascii=False), watch_id))

    def get(self, watch_id):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM watches WHERE id=?', (watch_id,)).fetchone()
        if row is None:
            raise SourceError('No local watch with this identifier')
        item = dict(row); item['place'] = json.loads(item['place'] or '{}')
        item['result'] = json.loads(item['result']) if item.get('result') else None
        return item


def check_watch(store, engine, watch, now=None):
    """Run the official warning tool for one watch and record the outcome."""
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
    return {'id': watch['id'], 'state': state, 'matched': outcome['matched'], 'detail': outcome['detail'],
            'packet_status': packet.get('status'), 'packet_answer': packet.get('answer')}


def check_due(store, engine, now=None):
    now = now or utcnow()
    results = []
    for watch in store.list(now=now):
        if watch.get('state') in {'expired'}:
            continue
        results.append(check_watch(store, engine, watch, now=now))
    return results
