"""The district nowcast: what IMD says is happening in the next few hours.

A nowcast and a district warning are different products and the difference is the whole reason this
exists. The warning layer is a five-day outlook keyed to the bulletin day; the nowcast is a
short-validity statement - Pune's on 22 September 2026 was issued 16:00 and valid to 19:00. Asking
"is a storm about to hit" and being answered from the five-day outlook is answering a different
question, which is what happened while S03 sat blocked behind a credential.

Nothing here is a dissemination authorisation, an all-clear, or a hazard this workspace named. The
publisher's own message is carried verbatim; its category codes are carried as codes, because no
legend is published with the layer (see adapters.nowcast).
"""
from datetime import date, datetime, time as dt_time, timedelta, timezone
from zoneinfo import ZoneInfo

from .geography import identity
from .transport import SourceError, parsed, stamp

IST = ZoneInfo('Asia/Kolkata')
COLOURS = {'1': 'red', '2': 'orange', '3': 'yellow', '4': 'green'}


def clock_label(value):
    """The publisher writes its times as HHMM strings; they are shown as printed."""
    text = str(value or '').strip()
    if len(text) == 4 and text.isdigit():
        return text[:2] + ':' + text[2:] + ' IST'
    return text or None


def render(result):
    records = result.get('nowcast_records') or []
    if not records:
        return ('No district nowcast is published for that point at this read. That is not an all-clear: '
                'a district absent from the layer has no current nowcast entry, which is a different thing '
                'from a nowcast saying nothing is expected.')
    lines = []
    for record in records:
        where = record['district_label'] + (', ' + str(record['state']) if record.get('state') else '')
        colour = COLOURS.get(str(record.get('colour')), str(record.get('colour') or 'not stated'))
        window = ' '.join(part for part in [
            'issued ' + (clock_label(record.get('time_of_issue')) or 'time not stated'),
            'on ' + str(record.get('issue_date') or 'date not stated'),
            'valid to ' + (clock_label(record.get('valid_until')) or 'not stated')] if part)
        lines.append('IMD nowcast for ' + where + ' · colour ' + colour + ' · ' + window + '.')
        if record.get('message'):
            lines.append('The publisher\'s own wording: "' + record['message'] + '"')
        if record.get('impact'):
            lines.append('Stated impact: "' + record['impact'] + '"')
        if record.get('action'):
            lines.append('Stated action: "' + record['action'] + '"')
        if record.get('hazard_category_codes'):
            lines.append('Category codes set on this entry: ' +
                         ', '.join(str(code) for code in record['hazard_category_codes']) +
                         '. No legend is published with this layer, so they are not named here.')
        if record.get('issuing_centre'):
            lines.append('Issued by ' + str(record['issuing_centre']) + '.')
    lines.append('A nowcast is the publisher\'s very-short-range statement, not the five-day district warning '
                 'and not a forecast computed here. It is reference only: no dissemination is authorised and '
                 'an absence is not an all-clear.')
    return '\n'.join(lines)


def execute_nowcast(engine, result, plan, task, resolved, coordinates):
    foundation = engine.workspace.foundation()
    points = engine.resolve_points(result, plan, resolved, coordinates)
    if points is None:
        return result
    result['nowcast_records'] = []
    missing, limitations = [], []
    for place in points:
        try:
            data = foundation.nowcast_snapshot(place['coordinates']['latitude'],
                                               place['coordinates']['longitude'])
        except (SourceError, ValueError, OSError) as exc:
            missing.append(place['label'] + ': ' + str(exc))
            continue
        meta = data['provenance']
        citation = 'c-' + meta['sha256']
        result['citations'].append({
            'id': citation, 'source_id': data['source_id'],
            'provider': 'India Meteorological Department',
            'product': 'IMD district nowcast (NowcastWarningDistrict)', 'url': meta['url'],
            'response_sha256': meta['sha256'], 'retrieved_at_utc': meta['retrieved_at_utc'],
            'requested_point': place['coordinates'], 'returned_grid': None,
            'grid_distance_km': None, 'model_run_time': None})
        if place.get('citation'):
            result['citations'].append(place['citation'])
        for limitation in data.get('limitations') or []:
            if limitation not in limitations:
                limitations.append(limitation)
        result['trace']['tools'].append({'name': 'imd_district_nowcast',
                                         'features': (data.get('coverage') or {}).get('source_features'),
                                         'matched': data['count'], 'source_sha256': meta['sha256']})
        for record in data['records']:
            result['nowcast_records'].append({**record, 'place': place['label'],
                                              'entity_id': place.get('selection_id') or identity(place['coordinates']),
                                              'citation_ids': [citation]})
        if not data['records']:
            missing.append(place['label'] + ': no district nowcast entry covers this point at this read')
        # A NOWCAST EXPIRES WHEN THE PUBLISHER SAYS IT DOES.
        #
        # This first set the expiry to the RETRIEVAL time, which is already in the past by the time
        # the answer is assembled, so every nowcast came back 'stale' with its evidence intact -
        # measured on the first live run. The publisher prints its own validity (`vupto`, an HHMM
        # IST clock on the issue date); that is the honest expiry, and the retrieval clock is only
        # the fallback for a row that does not print one.
        expiry = None
        for record in data['records']:
            printed = str(record.get('valid_until') or '').strip()
            day = str(record.get('issue_date') or '').strip()
            if len(printed) == 4 and printed.isdigit() and day:
                try:
                    closes = datetime.combine(date.fromisoformat(day),
                                              dt_time(int(printed[:2]) % 24, int(printed[2:]) % 60),
                                              tzinfo=IST)
                except ValueError:
                    continue
                moment = closes.astimezone(timezone.utc)
                if expiry is None or moment < expiry:
                    expiry = moment
        if expiry is None or expiry <= parsed(meta['retrieved_at_utc']):
            # No printed validity, or one that has already passed: the reading is still what the
            # publisher is serving now, so it stands for the layer's own refresh interval and says
            # the printed window in the answer either way.
            expiry = parsed(meta['retrieved_at_utc']) + timedelta(minutes=30)
        if result['expires_at_utc'] is None or expiry < parsed(result['expires_at_utc']):
            result['expires_at_utc'] = stamp(expiry)
    result['notes'] += missing
    for limitation in limitations:
        if limitation not in result['notes']:
            result['notes'].append(limitation)
    held = ('A nowcast is the publisher\'s very-short-range statement, not the five-day district warning '
            'and not a forecast computed here. An absence is not an all-clear and no dissemination is authorised.')
    if held not in result['notes']:
        result['notes'].append(held)
    result.setdefault('held_clauses', []).append(held)
    result['status'] = 'answered' if result['nowcast_records'] else 'unavailable'
    result['answer'] = render(result)
    return result
