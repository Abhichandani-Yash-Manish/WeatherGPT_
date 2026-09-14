"""Official IMD district warning applicability, anchored on the bulletin date.

This reads the S15 snapshot that adapters.warnings already parses and turns it
into a place-specific statement built only from IMD's own product fields:
district identity, the bulletin issue time, the day index, IMD's colour code and
the official hazard names.

Three things it deliberately refuses to do:

* It never turns a green day, an absent feature or a quarantined record into an
  all-clear. Code 1 means "no warning in this product", which is weaker than
  "nothing will happen".
* It never invents a validity interval. IMD publishes day indices against a
  bulletin date and does not publish a per-day validity field, so the windows
  are derived and labelled as derived.
* It never merges this forecast warning product with a CAP alert. A CAP alert
  and a district warning are different official products with different
  coverage, and they are reported side by side, never as one verdict.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .transport import SourceError

IST = ZoneInfo('Asia/Kolkata')
DAY_COUNT = 5
# Recorded on every parsed row so a reader can see why a day window exists at all.
DAY_BOUNDARY_DAY_KIND = 'day_anchored_on_bulletin_date'
QUIET_COLOUR_CODE = 4
COLOUR_ORDER = {'red': 0, 'orange': 1, 'yellow': 2, 'green': 3}

# IMD's district warning page labels its day selector with the bulletin date and
# each following date in turn, and reads the same Day_1..Day_5 fields this
# snapshot carries. So day n is the nth IST calendar day counted from the
# bulletin date. The product carries no per-day validity field, so this window
# is derived, and every answer says so.
DAY_BOUNDARY_BASIS = ('Day n is the nth IST calendar day counted from the bulletin date, matching the day '
                      'selector on the IMD district warning page. Derived from the bulletin date; IMD does not '
                      'publish a per-day validity field in this product.')


def anchor(record):
    """Return the IST midnight that day 1 starts from, plus the issue instant."""
    issued = record.get('issued_at_utc')
    if not issued:
        raise SourceError('Warning record has no issue timestamp')
    try:
        at = datetime.fromisoformat(issued).astimezone(IST)
    except ValueError as exc:
        raise SourceError('Warning record issue timestamp is unreadable') from exc
    return at.replace(hour=0, minute=0, second=0, microsecond=0), at


def day_rows(record, now=None):
    """Ordered day rows with derived IST windows. Raises if the record is unusable."""
    start, issued = anchor(record)
    moment = (now or datetime.now(timezone.utc)).astimezone(IST)
    rows = []
    for day in sorted(record.get('days') or [], key=lambda item: item['source_day']):
        index = int(day['source_day'])
        if not 1 <= index <= DAY_COUNT:
            continue
        opens = start + timedelta(days=index - 1)
        closes = opens + timedelta(days=1)
        codes = [int(code) for code in (day.get('hazard_codes') or [])]
        hazards = [name for name in (day.get('hazards') or []) if name]
        source_text = (day.get('source_text') or '').strip()
        rows.append({
            'day': index,
            'date_local': opens.date().isoformat(),
            'label': opens.strftime('%d %b %Y'),
            'colour': day.get('colour'),
            'colour_code': day.get('colour_code'),
            'hazard_codes': codes,
            'hazards': hazards,
            'quiet': bool(codes) and all(code == 1 for code in codes) and not source_text,
            'starts_utc': opens.astimezone(timezone.utc).isoformat(),
            'ends_utc': closes.astimezone(timezone.utc).isoformat(),
            'is_today': opens.date() == moment.date(),
            'is_past': closes <= moment,
            'source_text': source_text,
        })
    if not rows:
        raise SourceError('Warning record carries no usable day fields')
    return rows, issued


def select(records, lat, lon):
    """Every record whose official geometry covers the point. Empty means no district applies."""
    if lat is None or lon is None:
        raise SourceError('Both coordinates are required to resolve a warning district')
    from shapely.geometry import Point, shape
    point = Point(float(lon), float(lat))
    hits = []
    for record in records or []:
        geometry = record.get('geometry')
        if not isinstance(geometry, dict):
            continue
        try:
            area = shape(geometry)
        except (ValueError, TypeError, KeyError, AttributeError):
            continue
        if area.is_empty or not area.is_valid:
            continue
        if area.covers(point):
            hits.append(record)
    return hits


def severity(rows):
    """The most severe colour present, and whether any day carries a hazard."""
    ranked = [row for row in rows if row['colour'] in COLOUR_ORDER]
    if not ranked:
        return None, False
    best = min(ranked, key=lambda row: COLOUR_ORDER[row['colour']])
    return best['colour'], any(not row['quiet'] for row in rows)


def hazard_text(row):
    if row['source_text']:
        return row['source_text']
    if row['hazards']:
        return ', '.join(row['hazards'])
    if row['hazard_codes']:
        return ', '.join('code ' + str(code) for code in row['hazard_codes'])
    return 'No hazard code was supplied'


def facts(record, rows, issued, citation_id, place_label):
    """One fact per forecast day, in the conversation packet shape."""
    named = record.get('district_label') or 'Unnamed district'
    facts = []
    for row in rows:
        if row['quiet']:
            value, label = 'No warning in this product', 'Day ' + str(row['day']) + ' \u00b7 ' + row['label']
        else:
            value, label = row['colour'] or 'colour not supplied', 'Day ' + str(row['day']) + ' \u00b7 ' + row['label'] + ' \u00b7 ' + hazard_text(row)
        facts.append({
            'label': label,
            'value': value,
            'unit': 'IMD district warning colour',
            'place': named + ('' if not place_label or place_label == named else ' (' + place_label + ')'),
            'start': row['starts_utc'],
            'end': row['ends_utc'],
            'source_id': 'S15',
            'parameter': 'official_district_warning',
            'method': 'IMD district warning day fields, read as hazard codes',
            'entity_id': record.get('source_district_id') and ('imd-district:' + str(record['source_district_id'])) or None,
            'citation_ids': [citation_id],
            'evidence_kind': 'forecast',
            'day': row['day'],
            'colour_code': row['colour_code'],
            'hazard_codes': row['hazard_codes'],
            'quiet': row['quiet'],
            'source_locator': record.get('source_locator'),
        })
    return facts


def summary(record, rows, issued):
    """A deterministic statement of the official product, with no verdict beyond it."""
    named = record.get('district_label') or 'this district'
    today = [row for row in rows if row['is_today']]
    lead = today[0] if today else rows[0]
    parts = ['IMD district warning for ' + named + ', bulletin of ' + issued.strftime('%d %b %Y %H:%M IST') + '.']
    if today:
        parts.append('Day ' + str(lead['day']) + ' covers today, ' + lead['label'] + ': ' +
                     (lead['colour'] or 'colour not supplied') + ' - ' +
                     ('no warning in this product' if lead['quiet'] else hazard_text(lead)) + '.')
    else:
        parts.append('Its first published day is ' + lead['label'] + ', not today.')
    others = [row for row in rows if row is not lead and not row['quiet']]
    if others:
        parts.append('Other published days: ' + '; '.join(
            'day ' + str(row['day']) + ' ' + row['label'] + ' ' + (row['colour'] or 'colour not supplied') + ' ' + hazard_text(row)
            for row in others) + '.')
    elif len(rows) > 1:
        parts.append('Every other published day in this bulletin is also no warning in this product.')
    parts.append('This is IMD district-level warning guidance. It is not a flood warning, not an all-clear, '
                 'and not a CAP alert; a CAP alert covering the same area is reported separately.')
    return ' '.join(parts)
