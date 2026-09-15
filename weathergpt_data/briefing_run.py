"""A dated briefing over named places, composed from the products that are connected.

A briefing is a reading of connected products for a named list of places at a named instant:
the official district warning day for each place, the CAP relay reported separately, the model
forecast window as retrieved, and what is not established. It is not a warning, not an all-clear,
not advice and not an impact forecast, and it is not delivered: it is written to disk by the
runner this module serves.

Two rules hold everywhere here. A quiet district-day is not an all-clear, and it is written as a
quiet day in one product rather than as "no danger". A forecast value is model output for a grid
cell, quoted as the first and last value of the retrieved series with its sample count, never
summarised into an index and never presented as an observation.
"""
import hashlib
import json
from datetime import datetime, timezone

from .transport import SourceError, parsed

SCHEMA = 'briefing-v1'
RUNNER_NOTE = ('This is a foreground run of a local prototype. Nothing is delivered, pushed or scheduled outside this '
               'process; a briefing records what the connected products published at the instant it ran.')

FORECAST_PARAMETERS = ('precipitation_probability', 'precipitation', 'temperature_2m_max', 'temperature_2m_min',
                       'wind_speed_10m', 'relative_humidity_2m')
NOT_ESTABLISHED = [
    'A briefing reads the districts the connected products publish. A point outside every published district has no district guidance here, and none is substituted.',
    'A quiet day in the district warning product is not an all-clear and says nothing about hazards that product does not carry.',
    'Forecast values are model output for a grid cell, not observations, and no skill, accuracy or impact is claimed for them.',
    'The CAP relay is reported as a separate product state; geographic applicability to a place is not computed, and an empty relay is not an all-clear.',
    'Nothing here is delivered, pushed or scheduled by the workspace itself: a run happens when the runner runs.',
]


def stamp(moment):
    return moment.replace(microsecond=0).isoformat()


def _source_ids(view):
    found = []
    for item in (view or {}).get('sources') or []:
        value = item.get('source_id') if isinstance(item, dict) else item
        if value and str(value) not in found:
            found.append(str(value))
    return found


def forecast_window(view, limit=6):
    """First and last value of each retrieved series, with its sample count. No summary is computed."""
    data = (view or {}).get('data') or {}
    parameters = {}
    for name, entry in (data.get('parameters') or {}).items():
        points = (entry or {}).get('points') or []
        if not points:
            continue
        parameters[name] = {'unit': (entry or {}).get('unit'), 'model': (entry or {}).get('model'),
                            'samples': len(points), 'first': points[0].get('v'), 'last': points[-1].get('v'),
                            'starts': points[0].get('t'), 'ends': points[-1].get('t'),
                            'locator': points[0].get('source_locator')}
        if len(parameters) >= limit:
            break
    return parameters


def place_brief(foundation, place, day=1, forecast_days=3):
    """One place: the official day, the relay kept apart, the forecast window, and what failed."""
    from . import product_api
    from .alert_brief import compose as alert_compose
    latitude, longitude = float(place['latitude']), float(place['longitude'])
    record = {'label': place.get('label') or place.get('district') or 'place', 'latitude': latitude, 'longitude': longitude,
              'requested_district': place.get('district'), 'sources': [], 'unavailable': []}
    try:
        view = product_api.warnings_place(foundation, latitude, longitude)
        try:
            relay = product_api.cap_state(foundation, refresh=False)
        except (SourceError, ValueError, OSError):
            relay = None
        brief = alert_compose(view, relay, day_number=day)
        record['district'] = (brief.get('place') or {}).get('district') or (view.get('data') or {}).get('district')
        record['state'] = (brief.get('place') or {}).get('state') or (view.get('data') or {}).get('state')
        for source in _source_ids(view) + _source_ids(relay):
            if source not in record['sources']:
                record['sources'].append(source)
        if brief.get('status') == 'ok':
            record['official_day'] = {'colour': (brief.get('day_status') or {}).get('colour'),
                                      'colour_code': (brief.get('day_status') or {}).get('colour_code'),
                                      'hazards': (brief.get('day_status') or {}).get('hazards') or [],
                                      'quiet': bool((brief.get('day_status') or {}).get('quiet')),
                                      'status_line': brief.get('status_line'),
                                      'official_wording': (brief.get('day_status') or {}).get('official_wording'),
                                      'issued_at_utc': (brief.get('issuer') or {}).get('issued_at_utc'),
                                      'retrieved_at_utc': (brief.get('issuer') or {}).get('retrieved_at_utc'),
                                      'source_id': (brief.get('issuer') or {}).get('source_id'),
                                      'day': (brief.get('day') or {}).get('day'), 'day_label': (brief.get('day') or {}).get('label'),
                                      'starts_utc': (brief.get('day') or {}).get('starts_utc'),
                                      'ends_utc': (brief.get('day') or {}).get('ends_utc')}
        else:
            record['official_day'] = None
            record['unavailable'].append({'part': 'official district warning day', 'why': brief.get('why') or 'no day matched'})
        record['relay'] = {'source_id': (brief.get('relay') or {}).get('source_id') or 'S06',
                           'messages': (brief.get('relay') or {}).get('messages'),
                           'eligible_by_lifecycle': (brief.get('relay') or {}).get('eligible_by_lifecycle'),
                           'latest_sent': (brief.get('relay') or {}).get('latest_sent'),
                           'note': (brief.get('relay') or {}).get('note')}
    except (SourceError, ValueError, OSError) as failure:
        record['official_day'] = None
        record['relay'] = None
        record['unavailable'].append({'part': 'official district warning day', 'why': str(failure)})
    try:
        forecast = product_api.forecast(foundation, latitude, longitude, days=forecast_days)
        record['forecast'] = {'source_ids': _source_ids(forecast), 'days': forecast_days,
                              'generated_at_utc': forecast.get('generated_at_utc'),
                              'window': forecast_window(forecast)}
        for source in record['forecast']['source_ids']:
            if source not in record['sources']:
                record['sources'].append(source)
    except (SourceError, ValueError, OSError) as failure:
        record['forecast'] = None
        record['unavailable'].append({'part': 'forecast window', 'why': str(failure)})
    return record


def compose(foundation, places, day=1, forecast_days=3, now=None, previous=None):
    """The briefing document: the places as read, the instant, and the change since the last run."""
    if not places:
        raise SourceError('A briefing reads a named list of places; none was given')
    moment = now or datetime.now(timezone.utc)
    records = [place_brief(foundation, place, day=day, forecast_days=forecast_days) for place in places]
    briefing = {'schema_version': SCHEMA, 'generated_at_utc': stamp(moment), 'day_number': day,
                'forecast_days': forecast_days, 'place_count': len(records), 'places': records,
                'sources': sorted({source for record in records for source in record['sources']}),
                'not_established': list(NOT_ESTABLISHED)}
    briefing['change_since_previous'] = diff(previous, briefing)
    canonical = json.dumps({key: value for key, value in briefing.items() if key != 'briefing_id'},
                           sort_keys=True, ensure_ascii=False, default=str).encode('utf-8')
    briefing['briefing_id'] = hashlib.sha256(canonical).hexdigest()
    return briefing


def _key(record):
    return str(record.get('label') or record.get('district') or (record.get('latitude'), record.get('longitude')))


def _day_state(record):
    day = record.get('official_day')
    if day is None:
        return {'state': 'not_read', 'summary': 'no official day was read for this place'}
    state = 'quiet' if day.get('quiet') else (str(day.get('colour') or '').lower() or 'colour_not_supplied')
    return {'state': state, 'summary': str(day.get('status_line') or state)}


def diff(previous, current):
    """What changed since the previous briefing, measured against its record, never remembered."""
    if not previous:
        return {'reading': 'no_previous_run', 'detail': 'This is the first briefing in this series, so nothing is compared.',
                'places_added': [], 'places_removed': [], 'day_changes': [], 'forecast_changes': []}
    before = {_key(record): record for record in previous.get('places') or []}
    after = {_key(record): record for record in current.get('places') or []}
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    day_changes, forecast_changes = [], []
    for key in sorted(set(before) & set(after)):
        was, now = _day_state(before[key]), _day_state(after[key])
        if was['state'] == now['state'] and was['summary'] == now['summary']:
            day_changes.append({'place': key, 'reading': 'same', 'state': now['state'], 'summary': now['summary']})
        elif was['state'] == 'not_read' or now['state'] == 'not_read':
            day_changes.append({'place': key, 'reading': 'not_comparable', 'from': was, 'to': now,
                                'detail': 'One of the two runs did not read an official day for this place, so the two are not compared.'})
        else:
            day_changes.append({'place': key, 'reading': 'changed', 'from': was, 'to': now})
        old_window = ((before[key].get('forecast') or {}).get('window') or {})
        new_window = ((after[key].get('forecast') or {}).get('window') or {})
        if not old_window or not new_window:
            forecast_changes.append({'place': key, 'reading': 'not_comparable',
                                     'detail': 'One of the two runs holds no forecast window for this place.'})
        elif old_window == new_window:
            forecast_changes.append({'place': key, 'reading': 'same', 'detail': 'The retrieved window matches the previous run.'})
        else:
            shifted = sorted(set(new_window) - set(old_window)) or ['values']
            forecast_changes.append({'place': key, 'reading': 'changed',
                                     'detail': 'The retrieved forecast window differs from the previous run in: ' + ', '.join(shifted)})
    changed = [item for item in day_changes if item['reading'] == 'changed']
    incomparable = [item for item in day_changes if item['reading'] == 'not_comparable']
    if added or removed or changed:
        reading = 'changed'
    elif incomparable or any(item['reading'] == 'not_comparable' for item in forecast_changes):
        reading = 'partly_not_comparable'
    else:
        reading = 'same'
    return {'reading': reading, 'previous_briefing_id': previous.get('briefing_id'),
            'previous_generated_at_utc': previous.get('generated_at_utc'), 'places_added': added, 'places_removed': removed,
            'day_changes': day_changes, 'forecast_changes': forecast_changes,
            'detail': 'Compared against the previous run in this series, by place label, using that run record rather than a memory of it.'}

def summary_line(briefing):
    """One line a runner can print: what the run read, and what it did not."""
    day_states = [_day_state(record)['state'] for record in briefing.get('places') or []]
    quiet = day_states.count('quiet')
    not_read = day_states.count('not_read')
    return ('%d place(s) · official day read for %d · quiet in the product for %d · not read for %d · change: %s'
            % (briefing.get('place_count') or 0, len(day_states) - not_read, quiet, not_read,
               (briefing.get('change_since_previous') or {}).get('reading')))


def load_previous(path):
    """The previous run in this series, read from its own record, or None."""
    if not path or not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return record.get('briefing') if isinstance(record, dict) and 'briefing' in record else record


def markdown(briefing):
    """The briefing as Markdown: what each product said, and what it did not say."""
    lines = ['# Briefing — ' + str(briefing.get('generated_at_utc')), '',
             '- Briefing identity: sha256 ' + str(briefing.get('briefing_id'))[:16] + ' (the content hash of this briefing)',
             '- Places: ' + str(briefing.get('place_count')) + ' · Official day: day ' + str(briefing.get('day_number')) +
             ' of the published product · Forecast days: ' + str(briefing.get('forecast_days')),
             '- Sources named: ' + (', '.join(briefing.get('sources') or []) or 'none'),
             '- This is a reading of published products for named places. It is not a warning, not an all-clear, not advice and not delivered.',
             '']
    for record in briefing.get('places') or []:
        lines.append('## ' + str(record.get('label')))
        lines.append('')
        where = str(record.get('district') or 'no district matched')
        if record.get('state'):
            where += ', ' + str(record['state'])
        lines.append('- Place: ' + where + ' (' + str(record.get('latitude')) + ', ' + str(record.get('longitude')) + ')')
        day = record.get('official_day')
        if day:
            lines.append('- Official district warning day: ' + str(day.get('status_line')) +
                         ' · colour code ' + str(day.get('colour_code')) + ' · source ' + str(day.get('source_id')) +
                         ' · issued ' + str(day.get('issued_at_utc')) + ' · retrieved ' + str(day.get('retrieved_at_utc')))
            lines.append('- Day window: ' + str(day.get('day_label')) + ' (' + str(day.get('starts_utc')) + ' to ' + str(day.get('ends_utc')) + ')')
            if day.get('official_wording'):
                lines.append('- Printed wording: "' + str(day['official_wording']) + '"')
            elif day.get('quiet'):
                lines.append('- Printed wording: the product states a colour and hazard codes for this district-day and no free-text wording is recorded.')
        relay = record.get('relay')
        if relay:
            lines.append('- CAP relay (a separate product, never merged with the day above): ' +
                         ('not read' if relay.get('messages') is None else str(relay.get('messages')) + ' message(s), ' +
                          str(relay.get('eligible_by_lifecycle')) + ' eligible by lifecycle') + '. ' + str(relay.get('note') or ''))
        forecast = record.get('forecast')
        if forecast and forecast.get('window'):
            lines.append('- Forecast window (model output for a grid cell, not an observation; first and last value of the retrieved series):')
            for name, entry in forecast['window'].items():
                lines.append('    - ' + name + ': ' + str(entry.get('first')) + ' → ' + str(entry.get('last')) +
                             (' ' + str(entry['unit']) if entry.get('unit') else '') + ' across ' + str(entry.get('samples')) +
                             ' sample(s) · ' + str(entry.get('model') or 'model not stated'))
        for item in record.get('unavailable') or []:
            lines.append('- Not read: ' + str(item.get('part')) + ' — ' + str(item.get('why')))
        lines.append('')
    change = briefing.get('change_since_previous') or {}
    lines += ['## Change since the previous run', '', '- Reading: ' + str(change.get('reading')) + ' · ' + str(change.get('detail')), '']
    if change.get('previous_generated_at_utc'):
        lines.append('- Compared with the run of ' + str(change['previous_generated_at_utc']) + ' (sha256 ' +
                     str(change.get('previous_briefing_id'))[:16] + ')')
    for item in change.get('day_changes') or []:
        if item.get('reading') == 'changed':
            lines.append('- ' + str(item['place']) + ': ' + str((item.get('from') or {}).get('summary')) + ' → ' +
                         str((item.get('to') or {}).get('summary')))
        elif item.get('reading') == 'not_comparable':
            lines.append('- ' + str(item['place']) + ': not comparable between these two runs — ' + str(item.get('detail')))
    if change.get('places_added'):
        lines.append('- Places added: ' + ', '.join(change['places_added']))
    if change.get('places_removed'):
        lines.append('- Places removed: ' + ', '.join(change['places_removed']))
    lines += ['', '## What is not established here', '']
    lines += ['- ' + item for item in briefing.get('not_established') or []]
    return chr(10).join(lines) + chr(10)

def resolve_place(place, gazetteer=None):
    """A place name to a point, through the indexed gazetteer and its stated preference."""
    from .gazetteer import Gazetteer, preferred_match
    index = gazetteer or Gazetteer()
    name, _, state = str(place).partition(',')
    matches = index.search(name.strip(), state.strip())
    if not matches:
        raise SourceError('No indexed place matches: ' + str(place))
    chosen, why = preferred_match(matches)
    if chosen is None:
        raise SourceError('More than one place matches ' + str(place) + ' (' + str(why) +
                          '). Add the state or district to the place name.')
    admin1 = str(chosen.get('admin1') or '')
    return {'label': chosen.get('label') or chosen.get('name'), 'district': chosen.get('admin2') or chosen.get('name'),
            'state': admin1.removeprefix('State of ').strip(), 'latitude': chosen['coordinates']['latitude'],
            'longitude': chosen['coordinates']['longitude'], 'why': why}


def latest(directory):
    """The newest briefing record in a series directory, or None. Never guesses an order."""
    import pathlib
    folder = pathlib.Path(directory)
    if not folder.exists():
        return None
    records = sorted(folder.glob('record-*.json'))
    if not records:
        return None
    newest = records[-1]
    try:
        payload = json.loads(newest.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    markdown_path = newest.with_name(newest.name.replace('record-', 'briefing-')).with_suffix('.md')
    payload['markdown_path'] = str(markdown_path)
    payload['markdown'] = markdown_path.read_text(encoding='utf-8') if markdown_path.exists() else None
    payload['record_path'] = str(newest)
    return payload
