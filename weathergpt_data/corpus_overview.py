"""The published document index as a read model: what this machine holds and in what state.

Read-only over the corpus index. A document whose body has left the retention window keeps its
identity, its printed issue date and its passages and is reported as pruned, because that is a
different state from a document that was never published. Nothing here is a claim of nationwide
coverage: the list is what was ingested on this machine.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

from .bulletin_index import EXTRACTION_VERSION
from .corpus_tools import family_label, family_registered

BODY_AVAILABLE = 'available'
BODY_PRUNED = 'pruned'
BODY_UNKNOWN = 'unknown'


def index_path(runtime_root):
    """The one path convention for the corpus index under a runtime root."""
    return Path(runtime_root) / 'ingestion' / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite'


def _printed_date(value):
    text = str(value or '').strip()
    if len(text) < 10 or text[4] != '-' or text[7] != '-':
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _age_days(issue_date, retrieved_at_utc):
    """Days from the printed issue date to the retrieval date, or None when either is unknown.

    This is the definition the corpus uses everywhere: currency is measured from the printed issue
    date against the retrieval date, and stays unknown when the document states no printed date.
    """
    issued = _printed_date(issue_date)
    retrieved = _printed_date(retrieved_at_utc)
    if issued is None or retrieved is None or retrieved < issued:
        return None
    return (retrieved - issued).days


def holdings(runtime_root, family='district_agromet', state=None, query=None, limit=200, now=None):
    """What advisory editions this machine holds, one row per published region.

    The advisories surface used to show the publisher's directory and nothing else: a reader could see
    that the publisher lists 36 states and still find no advisory text anywhere on the page, although
    564 district editions and 6,187 passages were indexed here. This is the missing half - the holdings,
    per region, with the edition's own printed date, its measured age and its passage count.

    A printed date is never borrowed from the retrieval instant: a document that states none keeps
    issue_date None and age None, and says so. Counts describe the index, not a coverage claim.
    """
    path = index_path(runtime_root)
    empty = {'regions': [], 'states': [], 'families': [], 'counts': {'regions': 0, 'documents': 0, 'passages': 0},
             'filters': {'family': family or '', 'state': state or '', 'q': query or '', 'listed': 0}}
    if not path.exists():
        return {'status': 'unavailable', 'index': str(path),
                'reason': 'No corpus index is present under this runtime root.', **empty}
    try:
        with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(
                "SELECT COALESCE(region, '') region, MAX(family) family, MAX(scope) scope, COUNT(*) passages, "
                "COUNT(DISTINCT document_sha) documents, MIN(json_extract(payload,'$.issue_date')) oldest_issue_date, "
                "MAX(json_extract(payload,'$.issue_date')) newest_issue_date, "
                "GROUP_CONCAT(DISTINCT json_extract(payload,'$.language')) languages, "
                "GROUP_CONCAT(DISTINCT json_extract(payload,'$.source_id')) sources "
                "FROM passages WHERE family = ? GROUP BY region", (family,)).fetchall()
            documents = db.execute('SELECT sha, payload FROM documents').fetchall()
    except sqlite3.Error as error:
        return {'status': 'unavailable', 'index': str(path),
                'reason': 'The corpus index could not be read: ' + type(error).__name__ + ' ' + str(error)[:120], **empty}
    # The state each document names is the publisher's own field; the region carries it when the document
    # states one, so a district row can be grouped by its state without inventing a mapping.
    state_by_region = {}
    body_by_region = {}
    retrieved_by_region = {}
    for record in documents:
        try:
            payload = json.loads(record['payload'])
        except (TypeError, ValueError):
            continue
        region = str(payload.get('district') or payload.get('region') or '').strip()
        named = str(payload.get('state') or payload.get('source_state') or '').strip()
        if region and named:
            state_by_region.setdefault(region.lower(), named)
        if region:
            body_by_region.setdefault(region.lower(), body_state(payload, runtime_root))
            provenance = payload.get('provenance') or {}
            when = str(provenance.get('retrieved_at_utc') or provenance.get('checked_at_utc') or '')
            if when and when > retrieved_by_region.get(region.lower(), ''):
                retrieved_by_region[region.lower()] = when
    entries = []
    for row in rows:
        region = str(row['region'] or '').strip()
        issue = _printed_date(row['newest_issue_date'])
        entries.append({
            'region': region or None,
            'state': state_by_region.get(region.lower()),
            'family': row['family'],
            'scope': row['scope'],
            'documents': row['documents'],
            'passages': row['passages'],
            'oldest_issue_date': (str(_printed_date(row['oldest_issue_date'])) if _printed_date(row['oldest_issue_date']) else None),
            'newest_issue_date': (str(issue) if issue else None),
            # Currency is measured from the printed issue date against the retrieval instant of the
            # edition itself, the way the corpus measures it everywhere; never against the wall clock.
            'retrieved_at_utc': retrieved_by_region.get(region.lower()),
            'age_days': _age_days(issue, retrieved_by_region.get(region.lower())),
            'languages': sorted({part for part in str(row['languages'] or '').split(',') if part}),
            'source_ids': sorted({part for part in str(row['sources'] or '').split(',') if part}),
            'body': body_by_region.get(region.lower()),
        })
    needle = str(query or '').strip().lower()
    state_filter = str(state or '').strip().lower()
    selected = [entry for entry in entries
                if (not needle or needle in ' '.join(str(entry[key] or '') for key in ('region', 'state')).lower())
                and (not state_filter or str(entry['state'] or '').lower() == state_filter)]
    ordered = sorted(selected, key=lambda entry: (str(entry['newest_issue_date'] or ''), entry['region'] or ''), reverse=True)
    shown = ordered[:max(1, min(int(limit or 200), 1000))]
    states = {}
    for entry in entries:
        name = entry['state'] or 'state not stated in the held editions'
        bucket = states.setdefault(name, {'state': name, 'regions': 0, 'documents': 0, 'passages': 0, 'newest_issue_date': None})
        bucket['regions'] += 1
        bucket['documents'] += entry['documents']
        bucket['passages'] += entry['passages']
        if entry['newest_issue_date'] and (bucket['newest_issue_date'] is None or entry['newest_issue_date'] > bucket['newest_issue_date']):
            bucket['newest_issue_date'] = entry['newest_issue_date']
    families = {}
    for entry in entries:
        bucket = families.setdefault(entry['family'], {'family': entry['family'], 'label': family_label(entry['family']),
                                                       'registered': family_registered(entry['family']),
                                                       'regions': 0, 'documents': 0, 'passages': 0, 'newest_issue_date': None})
        bucket['regions'] += 1
        bucket['documents'] += entry['documents']
        bucket['passages'] += entry['passages']
        if entry['newest_issue_date'] and (bucket['newest_issue_date'] is None or entry['newest_issue_date'] > bucket['newest_issue_date']):
            bucket['newest_issue_date'] = entry['newest_issue_date']
    undated = len([entry for entry in entries if not entry['newest_issue_date']])
    return {'status': 'ok' if entries else 'unavailable', 'index': str(path),
            'regions': shown, 'states': sorted(states.values(), key=lambda entry: (-entry['regions'], entry['state'])),
            'families': sorted(families.values(), key=lambda entry: (-entry['documents'], entry['family'])),
            'counts': {'regions': len(entries), 'regions_listed': len(shown), 'regions_matching': len(ordered),
                       'documents': sum(entry['documents'] for entry in entries),
                       'passages': sum(entry['passages'] for entry in entries),
                       'states_named': len([name for name in states if name != 'state not stated in the held editions']),
                       'regions_without_a_printed_issue_date': undated},
            'filters': {'family': family or '', 'state': state or '', 'q': query or '', 'listed': len(shown)},
            'reason': ''}

def body_state(payload, runtime_root):
    """Whether the source body is still held, measured by the two publication forms.

    A document can be published as a chunk publication (a raw file on disk) or as a passage
    publication (a blob under the document store). The body is reported as pruned only when a
    location is recorded and the file is gone; a payload that records no location is unknown.
    """
    provenance = payload.get('provenance') or {}
    raw = str(provenance.get('raw_file') or '')
    if raw and Path(raw).exists():
        return BODY_AVAILABLE
    blob = str(provenance.get('blob') or '')
    if blob:
        return BODY_AVAILABLE if (Path(runtime_root) / 'documents' / blob).exists() else BODY_PRUNED
    return BODY_UNKNOWN


def _quarantined(payload):
    rows = payload.get('quarantined_passages') or []
    return len(rows) if isinstance(rows, list) else 0


def documents(runtime_root, family=None, query=None, limit=50):
    """Every indexed document, newest printed edition first, with its measured state.

    Filters: an exact family name, and a case-insensitive substring over the region, state,
    district, family label and source address. limit is applied after filtering and sorting, so
    the counts always describe the whole index rather than the returned page.
    """
    path = index_path(runtime_root)
    empty = {'documents': [], 'families': [], 'counts': {'documents': 0, 'documents_listed': 0,
                                                         'passages': 0, 'regions': 0, 'pruned': 0}}
    if not path.exists():
        return {'status': 'unavailable', 'index': str(path), 'reason': 'No corpus index is present under this runtime root.', **empty}
    try:
        with sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            stored = db.execute('SELECT sha, payload FROM documents').fetchall()
            counted = {row['document_sha']: dict(row) for row in db.execute(
                "SELECT document_sha, COUNT(*) passages, MIN(json_extract(payload,'$.physical_page')) first_page, "
                "MAX(json_extract(payload,'$.physical_page')) last_page, MAX(region) region, MAX(family) family, "
                "MAX(scope) scope, MAX(json_extract(payload,'$.language')) language, "
                "MAX(json_extract(payload,'$.issue_date')) issue_date, "
                "MAX(json_extract(payload,'$.source_id')) source_id "
                "FROM passages GROUP BY document_sha")}
    except sqlite3.Error as error:
        return {'status': 'unavailable', 'index': str(path),
                'reason': 'The corpus index could not be read: ' + type(error).__name__ + ' ' + str(error)[:120], **empty}
    rows = []
    for record in stored:
        try:
            payload = json.loads(record['payload'])
        except (TypeError, ValueError):
            continue
        sha = str(record['sha'])
        counted_row = counted.get(sha) or {}
        provenance = payload.get('provenance') or {}
        issue_date = payload.get('issue_date') or counted_row.get('issue_date')
        retrieved = provenance.get('retrieved_at_utc') or provenance.get('checked_at_utc')
        state = payload.get('state') or payload.get('source_state') or ''
        district = payload.get('district') or ''
        region = counted_row.get('region') or district or state or ''
        rows.append({
            'sha256': sha,
            'sha_prefix': sha[:12],
            'family': counted_row.get('family') or payload.get('family') or 'family not stated',
            'family_label': family_label(counted_row.get('family') or payload.get('family') or ''),
            'family_registered': family_registered(counted_row.get('family') or payload.get('family') or ''),
            'intake_family': payload.get('family'),
            'scope': counted_row.get('scope') or payload.get('scope'),
            'region': region or None,
            'state': state or None,
            'district': district or None,
            'issue_date': issue_date,
            'language': payload.get('language') or counted_row.get('language') or None,
            'pages': payload.get('pages'),
            'passages': counted_row.get('passages') or 0,
            'first_page': counted_row.get('first_page'),
            'last_page': counted_row.get('last_page'),
            'source_id': provenance.get('source_id') or counted_row.get('source_id'),
            'address': provenance.get('url'),
            'retrieved_at_utc': provenance.get('retrieved_at_utc'),
            'checked_at_utc': provenance.get('checked_at_utc'),
            'age_days': _age_days(issue_date, retrieved),
            'currency_recorded_at_intake': payload.get('currency'),
            'body': body_state(payload, runtime_root),
            'quarantined_passages': _quarantined(payload),
            'extraction_status': payload.get('extraction_status') or None,
        })
    needle = str(query or '').strip().lower()
    selected = [row for row in rows if (not family or row['family'] == family) and (
        not needle or needle in ' '.join(str(row[key] or '') for key in ('family', 'family_label', 'region', 'state', 'district', 'address', 'sha256')).lower())]
    # Newest printed edition first; a document that states no printed issue date sorts last rather
    # than being given a date it did not print.
    ordered = sorted(selected, key=lambda row: (str(row['issue_date'] or ''), row['family'], row['sha256']), reverse=True)
    shown = ordered[:max(1, min(int(limit or 50), 200))]
    families = {}
    for row in rows:
        entry = families.setdefault(row['family'], {'family': row['family'], 'label': row['family_label'],
                                                    'registered': row['family_registered'],
                                                    'documents': 0, 'passages': 0, 'newest_issue_date': None})
        entry['documents'] += 1
        entry['passages'] += row['passages']
        if row['issue_date'] and (entry['newest_issue_date'] is None or row['issue_date'] > entry['newest_issue_date']):
            entry['newest_issue_date'] = row['issue_date']
    return {'status': 'ok' if rows else 'unavailable', 'index': str(path),
            'documents': shown,
            'families': sorted(families.values(), key=lambda entry: (-entry['documents'], entry['family'])),
            'counts': {'documents': len(rows), 'documents_listed': len(shown), 'documents_matching': len(ordered),
                       'passages': sum(row['passages'] for row in rows),
                       'regions': len({row['region'] for row in rows if row['region']}),
                       'pruned': len([row for row in rows if row['body'] == BODY_PRUNED]),
                       'bodies_available': len([row for row in rows if row['body'] == BODY_AVAILABLE]),
                       'documents_without_a_printed_issue_date': len([row for row in rows if not row['issue_date']]),
                       'documents_in_an_unregistered_family': len([row for row in rows if not row['family_registered']]),
                       'unregistered_families': sorted({row['family'] for row in rows if not row['family_registered']})},
            'reason': '' if rows else 'The index holds no document yet.'}
