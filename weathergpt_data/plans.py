"""Plan Watch: a plan a person described, and the official categories it is checked against.

A plan is built from the person's own words: a place, a day and time or "always", and the
activity that decides which official hazard categories matter. The activity never produces
advice. It only selects which of IMD's own district warning categories are worth telling the
person about, and the person can add or drop one in words.

This module holds the vocabulary, the slot parsers and the local store. The watcher that
reads the official product lives in plan_watcher.py, and the conversation turn in
plan_intake.py.
"""
import json
import re
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from .adapters import HAZARDS
from .rule_planner import CROP, DAY_WORDS, IST, WINDOWS, WORD_EDGE, boundary_pattern
from .transport import SourceError, stamp, utcnow

ALL_CATEGORIES = list(range(2, 18))


def _words(pattern):
    """A whole-word pattern that also works in scripts whose vowel signs are combining marks."""
    return re.compile('(?<!' + WORD_EDGE + ')(?:' + pattern + ')(?!' + WORD_EDGE + ')', re.I)


# Which official categories each activity watches. Templates choose what is relevant to
# report; they never say whether the activity should go ahead. Order matters: the first
# matching activity wins, so "fishing trip" is fishing rather than travel.
ACTIVITIES = {
    'fishing': {'label': 'fishing trip', 'codes': [],
                'not_connected': ('No official sea-area or coastal bulletin is connected to this workspace, so a fishing '
                                  'plan cannot be checked against an official marine warning.'),
                'pattern': _words(r'fishing|fisherm[ae]n|go to sea|boat trip|machhli|मछली|માછીમારી')},
    'spraying': {'label': 'spraying', 'codes': [2, 4, 8, 16, 17],
                 'pattern': _words(r'spray\w*|pesticides?|insecticides?|fungicides?|herbicides?|fertili[sz]\w*|urea|'
                                   r'khaad|khad|dawa|chhidkav|छिड़काव|खाद|દવા|ખાતર')},
    'harvest': {'label': 'harvest', 'codes': [2, 4, 5, 16, 17],
                'pattern': _words(r'harvest\w*|threshing|drying|katai|कटाई|લણણી')},
    'irrigation': {'label': 'irrigation', 'codes': [2, 16, 17],
                   'pattern': _words(r'irrigat\w*|sinchai|सिंचाई|સિંચાઈ')},
    'outdoor_event': {'label': 'outdoor event', 'codes': [2, 4, 6, 9, 16, 17],
                      'pattern': _words(r'wedding|marriage|shaadi|shadi|party|function|event|mela|fair|picnic|match|'
                                        r'शादी|લગ્ન')},
    'travel': {'label': 'travel', 'codes': [2, 4, 15, 16, 17],
               'pattern': _words(r'travel\w*|trip|journey|drive|driving|commute|flight|train|safar|yatra|यात्रा|મુસાફરી')},
    'home': {'label': 'home', 'codes': ALL_CATEGORIES,
             'pattern': _words(r'(?:my|our)\s+(?:home|house|village|farm|field)|ghar|gaon|khet')},
}

# Hazard words a person may name directly. A group with no codes is a product this workspace
# does not connect; it is named so the plan can say so, never mapped onto a similar product.
HAZARD_GROUPS = [
    ('flood', None, 'flood', _words(r'floods?|flooding|inundation|बाढ़|પૂર')),
    ('cyclone', None, 'cyclone', _words(r'cyclones?|storm surge|चक्रवात|ચક્રવાત')),
    ('heavy_rain', {2, 16, 17}, 'heavy rain', _words(r'(?:very |extremely )?heavy rain\w*|rain|rains|rainfall|raining|barish|baarish|'
                                                    r'बारिश|वर्षा|વરસાદ')),
    ('thunderstorm', {4}, 'thunderstorm & lightning', _words(r'thunder\w*|lightning|squall|आंधी|तूफान|વાવાઝોડું')),
    ('hail', {5}, 'hailstorm', _words(r'hail\w*|ओले|કરા')),
    ('dust', {6, 7}, 'dust storm', _words(r'dust\w*')),
    ('wind', {8}, 'strong surface winds', _words(r'strong winds?|high winds?|gusts?|wind warning|wind|हवा|પવન')),
    ('heat', {9, 10, 11}, 'heat', _words(r'heat ?waves?|heatwave|hot day|warm night|heat|loo|लू|गर्मी|ગરમી')),
    ('cold', {12, 13, 14}, 'cold', _words(r'cold ?waves?|cold day|ground frost|frost|cold|शीतलहर|ठंड|ઠંડી')),
    ('fog', {15}, 'fog', _words(r'fog\w*|mist|कोहरा|ધુમ્મસ')),
    ('snow', {3}, 'heavy snow', _words(r'snow\w*|बर्फ')),
]

NOTIFY = re.compile(
    r"\b(?:notify|alert|warn|inform|update|remind)\s+(?:me|us)\b"
    r"|\blet\s+(?:me|us)\s+know\b"
    r"|\bkeep\s+(?:an?\s+)?(?:eye|watch)\s+on\b"
    r"|\bkeep\s+(?:me|us)\s+(?:posted|updated|informed)\b"
    r"|\btell\s+(?:me|us)\s+(?:if|when|whenever|in case)\s+(?!it\s+will\b|there\s+will\b|it\s+is\s+going\b|it'?s\s+going\b)"
    r"|\bbata(?:na|dena|dijiye|iye|te\s+rehna)\b|बता(?:ना|देना|इए|ते रहना)|सूचित|જણાવ(?:જો|શો)",
    re.I)

ALWAYS = _words(r'always|every ?day|daily|whenever|any ?time|all the time|hamesha|हमेशा|હંમેશા|'
                r'keep (?:an? )?(?:eye|watch) on|(?:my|our) (?:farm|field|home|house|village)')

WEEKDAYS = {'monday': 0, 'mon': 0, 'somvar': 0, 'सोमवार': 0, 'સોમવાર': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1, 'mangalvar': 1, 'मंगलवार': 1, 'મંગળવાર': 1,
            'wednesday': 2, 'wed': 2, 'budhvar': 2, 'बुधवार': 2, 'બુધવાર': 2,
            'thursday': 3, 'thu': 3, 'thurs': 3, 'guruvar': 3, 'गुरुवार': 3, 'ગુરુવાર': 3,
            'friday': 4, 'fri': 4, 'shukravar': 4, 'शुक्रवार': 4, 'શુક્રવાર': 4,
            'saturday': 5, 'shanivar': 5, 'शनिवार': 5, 'શનિવાર': 5,
            'sunday': 6, 'ravivar': 6, 'रविवार': 6, 'રવિવાર': 6}
WEEKDAY_NAMES = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
MONTHS = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10,
          'nov': 11, 'dec': 12}
MONTH = r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?'
DATE_DAY_FIRST = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+' + MONTH + r'(?:\s+(\d{4}))?\b', re.I)
DATE_MONTH_FIRST = re.compile(r'\b' + MONTH + r'\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b', re.I)
DATE_NUMERIC = re.compile(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b')

ALL_DAY = _words(r'all day|whole day|full day|entire day|pura din|poora din|din bhar|दिन भर|पूरा दिन|આખો દિવસ')
CLOCK_12 = re.compile(r'\b(1[0-2]|0?[1-9])(?:[:.]([0-5]\d))?\s*(am|pm|a\.m\.|p\.m\.)', re.I)
CLOCK_24 = re.compile(r'\b([01]?\d|2[0-3])[:.]([0-5]\d)\b')
PART_NAMES = {('09:30', '12:30'): 'morning', ('12:30', '18:30'): 'afternoon', ('18:30', '22:30'): 'evening',
              ('21:30', '23:30'): 'night'}
LABEL_NOUNS = _words(r'wedding|marriage|party|function|event|picnic|match|fair|mela|trip|journey|commute|flight|'
                     r'farm|field|home|house|village|orchard|garden|nursery')


def notify_intent(text):
    """True when the person asked to be kept informed, not only answered once."""
    return bool(NOTIFY.search(text or ''))


def activity_of(text):
    for name, template in ACTIVITIES.items():
        if template['pattern'].search(text or ''):
            return name
    return None


def label_of(text):
    """What the person calls the thing the plan is for: a crop first, then an event or place noun."""
    crop = CROP.search(text or '')
    if crop:
        return crop.group(1).lower()
    noun = LABEL_NOUNS.search(text or '')
    return noun.group(0).lower() if noun else None


def explicit_hazards(text):
    """Official category codes the person named, plus a named hazard no connected product carries."""
    codes, unconnected = set(), None
    for name, group, _, pattern in HAZARD_GROUPS:
        if not pattern.search(text or ''):
            continue
        if group is None:
            unconnected = unconnected or name
        else:
            codes |= group
    return sorted(codes), unconnected


def hazard_phrase(codes):
    """Readable names for a set of official categories, grouped the way people say them."""
    chosen = set(codes or [])
    if chosen >= set(ALL_CATEGORIES):
        return 'all official warning categories'
    names = [display for _, group, display, _ in HAZARD_GROUPS if group and group & chosen]
    if not names:
        return 'no connected warning category'
    return names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' and ' + names[-1]


ADMIN_PREFIX = re.compile(r'^(?:state of|union territory of|national capital territory of|nct of)\s+', re.I)


def plain_place_label(label):
    """A readable place label: repeated parts dropped, 'State of' removed, diacritics folded.

    GeoNames labels read 'Rājkot, Rājkot, State of Gujarāt'; a plan summary says 'Rajkot, Gujarat'.
    The source label is kept on the place record for the receipt.
    """
    parts = []
    for part in str(label or '').split(','):
        folded = ''.join(char for char in unicodedata.normalize('NFKD', part.strip()) if not unicodedata.combining(char))
        folded = ADMIN_PREFIX.sub('', folded).strip()
        if folded and (not parts or folded.casefold() != parts[-1].casefold()):
            parts.append(folded)
    return ', '.join(parts)


def _today(now):
    return now.astimezone(IST).date()


def parse_day(text, now):
    """The plan's day: an explicit date, a relative day, a weekday, or a standing plan."""
    text = text or ''
    today = _today(now)
    for pattern, order in ((DATE_DAY_FIRST, 'dmy'), (DATE_MONTH_FIRST, 'mdy'), (DATE_NUMERIC, 'numeric')):
        match = pattern.search(text)
        if not match:
            continue
        try:
            if order == 'dmy':
                day, month, year = int(match.group(1)), MONTHS[match.group(2).lower()[:3]], match.group(3)
            elif order == 'mdy':
                month, day, year = MONTHS[match.group(1).lower()[:3]], int(match.group(2)), match.group(3)
            else:
                day, month, year = int(match.group(1)), int(match.group(2)), match.group(3)
            year = int(year) if year else today.year
            if year < 100:
                year += 2000
            when = date(year, month, day)
        except (ValueError, KeyError):
            continue
        kind = 'past' if when < today else 'once'
        return {'kind': kind, 'date': when.isoformat(), 'basis': match.group(0).strip()}
    for word, offset in DAY_WORDS.items():
        if boundary_pattern(word).search(text):
            return {'kind': 'once', 'date': (today + timedelta(days=offset)).isoformat(), 'basis': word}
    for word, index in WEEKDAYS.items():
        if boundary_pattern(word).search(text):
            ahead = (index - today.weekday()) % 7
            return {'kind': 'once', 'date': (today + timedelta(days=ahead)).isoformat(), 'basis': WEEKDAY_NAMES[index]}
    if ALWAYS.search(text):
        return {'kind': 'always'}
    return None


def parse_time(text):
    """The part of day or clock time, in the product's own windows."""
    text = text or ''
    if ALL_DAY.search(text):
        return {'start': '00:30', 'end': '00:30', 'next_day_end': True, 'label': 'all day'}
    match = CLOCK_12.search(text)
    if match:
        hour = int(match.group(1)) % 12 + (12 if match.group(3).lower().startswith('p') else 0)
        minute = int(match.group(2) or 0)
        return _clock_slot(hour, minute)
    match = CLOCK_24.search(text)
    if match:
        return _clock_slot(int(match.group(1)), int(match.group(2)))
    for word, (start, end) in WINDOWS.items():
        if boundary_pattern(word).search(text):
            return {'start': start, 'end': end, 'next_day_end': False, 'label': PART_NAMES.get((start, end), word)}
    return None


def _clock_slot(hour, minute):
    end_hour = min(hour + 3, 23)
    return {'start': '%02d:%02d' % (hour, minute), 'end': '%02d:%02d' % (end_hour, minute if end_hour > hour else 59),
            'next_day_end': False, 'label': 'from %02d:%02d' % (hour, minute)}


def window_of(day, slot):
    """IST start and end instants for a calendar day and a time slot."""
    when = date.fromisoformat(day)

    def at(hhmm, target):
        return datetime(target.year, target.month, target.day, int(hhmm[:2]), int(hhmm[3:5]), tzinfo=IST)

    start = at(slot['start'], when)
    end = at(slot['end'], when + timedelta(days=1) if slot.get('next_day_end') else when)
    if end <= start:
        end = at(slot['end'], when + timedelta(days=1))
    return start.isoformat(), end.isoformat()


def settle_date(day, slot, now):
    """A weekday whose window has already passed today means the same weekday next week."""
    if not day or day.get('kind') != 'once' or not slot or day.get('basis') not in WEEKDAY_NAMES:
        return day
    _, end = window_of(day['date'], slot)
    if datetime.fromisoformat(end) <= now:
        moved = date.fromisoformat(day['date']) + timedelta(days=7)
        return dict(day, date=moved.isoformat())
    return day


def day_phrase(day_iso):
    when = date.fromisoformat(day_iso)
    return WEEKDAY_NAMES[when.weekday()].capitalize() + ' ' + str(when.day) + ' ' + when.strftime('%b')


class PlanStore:
    """Plans, their notifications and the watcher's own bookkeeping, in one local SQLite file."""

    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, created_at TEXT, payload TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id TEXT, '
                       'kind TEXT, dedupe_key TEXT UNIQUE, created_at TEXT, visible_at TEXT, title TEXT, text TEXT, '
                       'receipt TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)')

    @contextmanager
    def _connect(self):
        # A sqlite3 connection used as a context manager commits but never closes, which
        # leaves the file open; the watcher thread and HTTP threads each open their own.
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create(self, fields):
        plan = dict(fields)
        plan['id'] = str(uuid.uuid4())
        plan.setdefault('created_at', stamp(utcnow()))
        plan.setdefault('saved_at', plan['created_at'])
        with self._connect() as db:
            db.execute('INSERT INTO plans VALUES (?,?,?)', (plan['id'], plan['created_at'], json.dumps(plan, ensure_ascii=False)))
        return plan

    def get(self, plan_id):
        with self._connect() as db:
            row = db.execute('SELECT payload FROM plans WHERE id=?', (str(plan_id),)).fetchone()
        if row is None:
            raise SourceError('No saved plan with this identifier')
        return json.loads(row[0])

    def list(self, include_ended=True):
        with self._connect() as db:
            rows = db.execute('SELECT payload FROM plans ORDER BY created_at DESC').fetchall()
        plans = [json.loads(row[0]) for row in rows]
        return plans if include_ended else [plan for plan in plans if plan.get('state') != 'ended']

    def update(self, plan_id, **fields):
        plan = self.get(plan_id)
        plan.update(fields)
        with self._connect() as db:
            db.execute('UPDATE plans SET payload=? WHERE id=?', (json.dumps(plan, ensure_ascii=False), plan['id']))
        return plan

    def delete(self, plan_id):
        with self._connect() as db:
            gone = db.execute('DELETE FROM plans WHERE id=?', (str(plan_id),)).rowcount
            db.execute('DELETE FROM notifications WHERE plan_id=?', (str(plan_id),))
        return bool(gone)

    def add_notification(self, plan_id, kind, dedupe_key, title, text, receipt, created_at, visible_at):
        """Write a notification once; a repeated deduplication key writes nothing and returns None."""
        with self._connect() as db:
            cursor = db.execute('INSERT OR IGNORE INTO notifications (plan_id,kind,dedupe_key,created_at,visible_at,title,text,receipt) '
                                'VALUES (?,?,?,?,?,?,?,?)',
                                (plan_id, kind, dedupe_key, created_at, visible_at, title, text,
                                 json.dumps(receipt or {}, ensure_ascii=False)))
            return cursor.lastrowid if cursor.rowcount else None

    def notifications(self, limit=50):
        with self._connect() as db:
            db.row_factory = sqlite3.Row
            rows = db.execute('SELECT * FROM notifications ORDER BY id DESC LIMIT ?', (int(limit),)).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item['receipt'] = json.loads(item['receipt'] or '{}')
            items.append(item)
        return items

    def meta_get(self, key):
        with self._connect() as db:
            row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return row[0] if row else None

    def meta_set(self, key, value):
        with self._connect() as db:
            db.execute('INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))
