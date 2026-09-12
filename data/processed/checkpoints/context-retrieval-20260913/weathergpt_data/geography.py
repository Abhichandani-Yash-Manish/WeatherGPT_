"""Versioned source identities. Name matches and source polygons are evidence, not LGD mappings."""
import hashlib
import json
import math
import sqlite3
import unicodedata
from datetime import date
from pathlib import Path

ENTITY_TYPES = {'state', 'district', 'subdistrict', 'village', 'city', 'locality',
                'urban_local_body', 'ward', 'airport', 'station', 'model_point',
                'basin', 'gauge', 'marine_region', 'historical_district', 'place'}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def identity(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def normalized(name):
    # Preserve accents, punctuation and language. Transliteration needs explicit evidence.
    return ' '.join(unicodedata.normalize('NFC', name).casefold().split())


def required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ' must be nonempty text')


def interval(start, end):
    if start is not None: date.fromisoformat(start)
    if end is not None: date.fromisoformat(end)
    if end is not None and (start is None or end <= start):
        raise ValueError('Effective interval must be ordered and half-open')


def point(latitude, longitude):
    for value, bound in [(latitude, 90), (longitude, 180)]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > bound:
            raise ValueError('Invalid WGS84 coordinate')


def geometry_status(geometry, crs):
    if geometry is None: return 'missing'
    if crs != 'EPSG:4326': return 'unsupported_crs'
    try:
        from shapely.geometry import shape
        g = shape(geometry)
        if g.geom_type not in {'Polygon', 'MultiPolygon', 'Point'} or g.is_empty or not g.is_valid:
            return 'invalid'
        a, b, c, d = g.bounds
        point(b, a); point(d, c)
        return 'valid_source_geometry'
    except (ValueError, TypeError, KeyError, OverflowError):
        return 'invalid'


class Geography:
    def __init__(self, database, readonly=False):
        path = Path(database).resolve()
        if readonly:
            self.db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        if not readonly:
            self.db.executescript('''
                CREATE TABLE IF NOT EXISTS entities (
                    entity_id TEXT PRIMARY KEY, namespace TEXT NOT NULL, kind TEXT NOT NULL,
                    source_code TEXT NOT NULL, version TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS entity_source ON entities(namespace, kind, source_code, version);
                CREATE TABLE IF NOT EXISTS aliases (
                    entity_id TEXT NOT NULL REFERENCES entities(entity_id), name TEXT NOT NULL,
                    language TEXT NOT NULL, normalized TEXT NOT NULL,
                    PRIMARY KEY(entity_id, name, language));
                CREATE INDEX IF NOT EXISTS alias_search ON aliases(normalized);
                CREATE TABLE IF NOT EXISTS relationships (
                    relationship_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL REFERENCES entities(entity_id),
                    object TEXT NOT NULL REFERENCES entities(entity_id), kind TEXT NOT NULL,
                    payload TEXT NOT NULL);
            ''')

    def close(self): self.db.close()

    def add(self, *, namespace, kind, source_code, version, label, evidence,
            locator, aliases=(), effective_from=None, effective_to=None,
            geometry=None, crs=None, status='source_record', attributes=None):
        for field, value in [('namespace', namespace), ('source_code', source_code),
                             ('version', version), ('label', label), ('locator', locator)]:
            required_text(value, field)
        if kind not in ENTITY_TYPES: raise ValueError('Unknown entity type')
        if status not in {'source_record', 'quarantined'}: raise ValueError('Unknown entity state')
        if not isinstance(evidence, dict) or not evidence.get('sha256') or not evidence.get('source_id'):
            raise ValueError('Source identity and evidence hash required')
        interval(effective_from, effective_to)
        eid = identity([namespace, kind, source_code, version, locator])
        names = [{'name': label, 'language': 'und'}] + list(aliases)
        for a in names:
            required_text(a['name'], 'alias'); required_text(a['language'], 'language')
        payload = dict(entity_id=eid, namespace=namespace, kind=kind, source_code=source_code,
                       version=version, label=label, source_locator=locator, evidence=evidence,
                       effective_from=effective_from, effective_to=effective_to,
                       effective_dates_known=effective_from is not None,
                       geometry=geometry, crs=crs, geometry_status=geometry_status(geometry, crs),
                       status=status, attributes=attributes or {}, aliases=names)
        encoded = canonical(payload)
        old = self.db.execute('SELECT payload FROM entities WHERE entity_id=?', (eid,)).fetchone()
        if old and old[0] != encoded: raise ValueError('Immutable entity version changed; create a new version')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO entities VALUES (?,?,?,?,?,?)',
                            (eid, namespace, kind, source_code, version, encoded))
            self.db.executemany('INSERT OR IGNORE INTO aliases VALUES (?,?,?,?)',
                                [(eid, a['name'], a['language'], normalized(a['name'])) for a in names])
        return eid

    def get(self, entity_id):
        row = self.db.execute('SELECT payload FROM entities WHERE entity_id=?', (entity_id,)).fetchone()
        if row is None: raise ValueError('Unknown entity ID')
        return json.loads(row[0])

    def resolve(self, name, namespace=None, kind=None, version=None, on_date=None):
        required_text(name, 'name')
        if on_date is not None: date.fromisoformat(on_date)
        sql = 'SELECT DISTINCT e.payload FROM entities e JOIN aliases a USING(entity_id) WHERE a.normalized=?'
        args = [normalized(name)]
        for column, value in [('namespace', namespace), ('kind', kind), ('version', version)]:
            if value is not None: sql += ' AND e.' + column + '=?'; args.append(value)
        candidates = []
        for row in self.db.execute(sql, args):
            p = json.loads(row[0])
            if p['status'] == 'quarantined': continue
            if on_date and (not p['effective_dates_known'] or p['effective_from'] > on_date or
                            (p['effective_to'] is not None and on_date >= p['effective_to'])): continue
            candidates.append({k: v for k, v in p.items() if k not in {'geometry', 'aliases'}})
        candidates.sort(key=lambda p: p['entity_id'])
        return {'status': 'unresolved' if not candidates else ('single_source_candidate' if len(candidates) == 1 else 'needs_selection'),
                'candidates': candidates, 'administrative_mapping': 'not_established_by_name_search',
                'limitation': 'No fuzzy, transliteration or cross-provider identity inference; unknown effective dates fail dated resolution.'}

    def relate(self, subject, object, kind, evidence, *, status='candidate',
               effective_from=None, effective_to=None, reviewer=None):
        self.get(subject); self.get(object)
        if kind not in {'listed_under', 'same_identity', 'located_in', 'sampled_at', 'successor_of'}:
            raise ValueError('Unsupported relationship')
        if status not in {'candidate', 'reviewed'}: raise ValueError('Unknown mapping status')
        if not evidence: raise ValueError('Relationship evidence required')
        interval(effective_from, effective_to)
        if status == 'reviewed' and (not reviewer or effective_from is None):
            raise ValueError('Reviewed mapping needs reviewer, dated validity and evidence')
        if status == 'reviewed' and any(self.get(e)['status'] == 'quarantined' for e in [subject, object]):
            raise ValueError('Quarantined entities cannot receive reviewed mappings')
        # Different spatial supports cannot be made identical by a reviewed name match.
        if kind == 'same_identity' and self.get(subject)['kind'] != self.get(object)['kind']:
            raise ValueError('Different entity types cannot be identical')
        payload = dict(subject=subject, object=object, kind=kind, evidence=evidence,
                       status=status, effective_from=effective_from, effective_to=effective_to, reviewer=reviewer)
        rid = identity(payload)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO relationships VALUES (?,?,?,?,?)',
                            (rid, subject, object, kind, canonical(payload)))
        return rid

    def mappings(self, subject, on_date, kind='same_identity'):
        self.get(subject); date.fromisoformat(on_date)
        rows = [json.loads(x[0]) for x in self.db.execute(
            'SELECT payload FROM relationships WHERE subject=? AND kind=?', (subject, kind))]
        rows = [r for r in rows if r['status'] == 'reviewed' and r['effective_from'] <= on_date
                and (r['effective_to'] is None or on_date < r['effective_to'])]
        return {'status': 'unresolved' if not rows else ('mapped' if len(rows) == 1 else 'ambiguous'), 'mappings': rows}

    def areas_at(self, latitude, longitude, namespace, version):
        """Diagnostic point-in-source-polygon only. Boundary matches remain ambiguous."""
        from shapely.geometry import Point, shape
        point(latitude, longitude)
        query = Point(longitude, latitude); matches = []; excluded = 0; total = 0
        for row in self.db.execute('SELECT payload FROM entities WHERE namespace=? AND version=?', (namespace, version)):
            p = json.loads(row[0]); total += 1
            if p['status'] == 'quarantined' or p['geometry_status'] != 'valid_source_geometry':
                excluded += 1; continue
            g = shape(p['geometry'])
            if g.geom_type not in {'Polygon', 'MultiPolygon'}: continue
            if g.covers(query):
                matches.append({'entity_id': p['entity_id'], 'label': p['label'], 'on_boundary': g.boundary.covers(query)})
        return {'status': 'unresolved' if not matches else ('ambiguous' if len(matches) > 1 or matches[0]['on_boundary'] else 'source_polygon_match'),
                'matches': matches, 'source_records': total, 'excluded_records': excluded,
                'administrative_mapping': 'unverified', 'actionable_current_alerts': False,
                'limitation': 'Geometric match only; source CRS/boundary edition, validity and complete coverage need independent acceptance.'}
