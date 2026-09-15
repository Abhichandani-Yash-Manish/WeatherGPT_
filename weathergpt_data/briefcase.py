"""The local briefcase: composed briefs kept, reopened and exported.

Only briefs the workspace itself composed are kept, so a stored brief can never be a claim
no source backs. Each entry carries its kind, its place, its window, the sources it names,
the content hash of what was stored and the instant it was saved. Nothing here is delivered
or pushed: an export writes a Markdown file the reader can keep, and the entry stays in the
local store until it is deleted.
"""
import hashlib
import json
import sqlite3
import uuid

from .transport import SourceError, parsed, utcnow

KINDS = ('alert_brief', 'advisory_brief')
KIND_LABELS = {'alert_brief': 'Alert brief', 'advisory_brief': 'Advisory brief'}
NO_DELIVERY = ('Kept in the local store. Nothing is delivered, pushed or published from here; '
               'an export is a file you keep.')


def stamp(moment):
    return moment.replace(microsecond=0).isoformat()


def content_hash(brief):
    """The brief's own identity when the composer gave one, else the hash of what is stored."""
    given = brief.get('brief_id')
    if isinstance(given, str) and len(given) >= 16:
        return given
    canonical = json.dumps(brief, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def sources_of(brief):
    """The named sources, as identifiers, from either brief shape. Never invented."""
    found = []
    for item in brief.get('sources') or []:
        if isinstance(item, dict):
            value = item.get('source_id') or item.get('id') or item.get('label')
        else:
            value = item
        if value and str(value) not in found:
            found.append(str(value))
    for passage in ((brief.get('published_advice') or {}).get('passages') or []):
        value = passage.get('source_id')
        if value and str(value) not in found:
            found.append(str(value))
    return found


def place_of(brief):
    place = brief.get('place') or {}
    if place:
        return {'district': place.get('district'), 'state': place.get('state'),
                'label': place.get('label') or place.get('district'),
                'latitude': place.get('latitude'), 'longitude': place.get('longitude')}
    request = brief.get('request') or {}
    advice = brief.get('published_advice') or {}
    return {'district': advice.get('region') or request.get('region'), 'state': request.get('state'),
            'label': advice.get('region') or request.get('region')}


def window_of(brief):
    day = brief.get('day') or {}
    if day.get('starts_utc') or day.get('ends_utc'):
        return {'starts_utc': day.get('starts_utc'), 'ends_utc': day.get('ends_utc'),
                'label': day.get('label'), 'day': day.get('day')}
    request = brief.get('request') or {}
    return {'label': request.get('window'), 'day': None, 'starts_utc': None, 'ends_utc': None}


def title_of(kind, brief):
    label = KIND_LABELS.get(kind, 'Brief')
    if kind == 'alert_brief':
        place = place_of(brief)
        head = str(place.get('district') or 'district not stated')
        if place.get('state') and place['state'] != place.get('district'):
            head += ', ' + str(place['state'])
    else:
        request = brief.get('request') or {}
        head = str(request.get('crop') or 'crop not named')
        if request.get('growth_stage'):
            head += ' · ' + str(request['growth_stage'])
        head += ' · ' + str((brief.get('published_advice') or {}).get('region') or 'region not stated')
    if brief.get('status') != 'ok':
        return label + ' (not available) — ' + head
    return label + ' — ' + head


def evidence_of(brief):
    """What the brief rests on, and what it says is not established. Kept with the entry."""
    return {'sources': sources_of(brief),
            'not_established': [str(item) for item in brief.get('not_established') or []][:12],
            'why': brief.get('why') if brief.get('status') != 'ok' else None,
            'notes': [str(item) for item in brief.get('notes') or []][:8]}


class BriefStore:
    def __init__(self, path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS briefs (id TEXT PRIMARY KEY,saved_at TEXT,kind TEXT,title TEXT,'
                       'place TEXT,window TEXT,content_sha256 TEXT,sources TEXT,payload TEXT)')

    def save(self, kind, brief, now=None):
        """Keep one composed brief. A payload with no provenance is refused, not stored."""
        if kind not in KINDS:
            raise SourceError('Keep an alert brief or an advisory brief')
        if not isinstance(brief, dict) or not brief:
            raise SourceError('There is no composed brief to keep')
        evidence = evidence_of(brief)
        if not evidence['sources'] and not evidence['not_established']:
            raise SourceError('A brief that names no source and states no limit is not kept')
        now = now or utcnow()
        entry = {'id': str(uuid.uuid4()), 'saved_at': stamp(now), 'kind': kind, 'title': title_of(kind, brief),
                 'place': place_of(brief), 'window': window_of(brief),
                 'content_sha256': content_hash(brief), 'sources': evidence['sources'],
                 'status': brief.get('status'), 'evidence': evidence, 'payload': brief,
                 'delivery': 'local_only_no_delivery'}
        with sqlite3.connect(self.path) as db:
            db.execute('INSERT INTO briefs VALUES (?,?,?,?,?,?,?,?,?)',
                       (entry['id'], entry['saved_at'], kind, entry['title'],
                        json.dumps(entry['place'], ensure_ascii=False), json.dumps(entry['window'], ensure_ascii=False),
                        entry['content_sha256'], json.dumps(entry['sources'], ensure_ascii=False),
                        json.dumps(brief, ensure_ascii=False, default=str)))
        return entry

    def list(self):
        entries = []
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            for row in db.execute('SELECT * FROM briefs ORDER BY saved_at DESC, rowid DESC'):
                entries.append(self._entry(dict(row)))
        return entries

    def get(self, brief_id):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute('SELECT * FROM briefs WHERE id=?', (brief_id,)).fetchone()
        if row is None:
            raise SourceError('No kept brief has this identifier')
        return self._entry(dict(row))

    def delete(self, brief_id):
        with sqlite3.connect(self.path) as db:
            removed = db.execute('DELETE FROM briefs WHERE id=?', (brief_id,)).rowcount
        if not removed:
            raise SourceError('No kept brief has this identifier')
        return {'deleted': brief_id, 'detail': 'The kept brief was removed from the local store. Nothing was delivered from it.'}

    def _entry(self, row):
        payload = json.loads(row['payload'])
        return {'id': row['id'], 'saved_at': row['saved_at'], 'kind': row['kind'], 'title': row['title'],
                'place': json.loads(row['place'] or '{}'), 'window': json.loads(row['window'] or '{}'),
                'content_sha256': row['content_sha256'], 'sources': json.loads(row['sources'] or '[]'),
                'evidence': evidence_of(payload), 'payload': payload, 'delivery': 'local_only_no_delivery'}


def markdown(entry):
    """The export: what was composed, when it was kept, and what it rests on."""
    if entry['kind'] == 'alert_brief':
        from .alert_brief import markdown as body
    else:
        from .advisory import markdown as body
    lines = ['<!-- Kept in the local WeatherGPT briefcase. Nothing was delivered or published. -->', '',
             '**Kept:** ' + str(entry['saved_at']) + ' · **Entry:** ' + str(entry['id'])[:8] +
             ' · **Content hash:** sha256 ' + str(entry['content_sha256'])[:16],
             '**Sources named:** ' + (', '.join(entry['sources']) if entry['sources'] else 'none named in this brief'), '', '---', '']
    try:
        rendered = body(entry['payload'])
    except (KeyError, TypeError, ValueError):
        rendered = chr(10).join(['## The stored payload could not be re-rendered by this version', '',
                               'The entry is kept as it was stored. This version of the renderer does not recognise it, so the payload is '
                               'quoted rather than paraphrased:', '',
                               '    ' + json.dumps(entry['payload'], ensure_ascii=False, indent=2, default=str
                                                 ).replace(chr(10), chr(10) + '    ')])
    lines += rendered.splitlines()
    return chr(10).join(lines) + chr(10)
