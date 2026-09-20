"""The opening sentence of an answer: the finding first, the receipt after.

Measured 20 September 2026 (docs/117): four of seven real answers opened with a place label, a model cell,
a coordinate or a retrieval timestamp, and one carried 162 numerals across 288 words. The claim atom
already carries source, window and retrieval instant, so the sentence was repeating the receipt instead of
stating the finding.

This module owns the opening. Every kind of answer is given one sentence that names the place, the
measure, the value and the window in words; a kind that cannot answer says why in a sentence of the same
shape. The body under it is depth, and every number in it keeps its own fact, unit and citation.

Nothing here introduces a value: the composed sentence is built from the fact rows themselves, formatted
at the precision they were published with. It never rounds a value up, never turns a modelled cell into a
station and never turns a forecast into an observation.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

IST = ZoneInfo('Asia/Kolkata')
UTC = timezone.utc

# How a measure is named when it opens a sentence. Kept in one place so the opening and the depth line
# cannot drift apart in wording, and so a new parameter is added here rather than invented in a renderer.
# Units whose published spelling is a machine's rather than a reader's. The value, the precision and
# the unit's meaning are unchanged: only the glyph a sentence prints is mapped, and the fact's own unit
# spelling stays in the receipt. 'degC' is the unit column of the IMD Pune temperature table.
DISPLAY_UNITS = {'degC': '°C', 'degc': '°C', 'm3/s': 'm³/s', 'm3s': 'm³/s', 'ug/m3': 'µg/m³',
                 'US AQI': 'US AQI', 'EAQI': 'European AQI', 'USAQI': 'US AQI'}


def display_unit(unit):
    """The unit as a sentence prints it, or the unit unchanged."""
    text = str(unit or '').strip()
    return DISPLAY_UNITS.get(text, text)


MEASURE_WORDS = {
    'precipitation': 'rainfall',
    'precipitation_probability': 'the hourly rain chance',
    'precipitation_sum': 'rainfall',
    'rainfall': 'rainfall',
    'temperature_2m': 'temperature',
    'temperature_2m_max': 'the daily maximum temperature',
    'temperature_2m_min': 'the daily minimum temperature',
    'temperature_2m_mean': 'the daily mean temperature',
    'temperature': 'temperature',
    'apparent_temperature': 'the feels-like temperature',
    'relative_humidity_2m': 'relative humidity',
    'wind_speed_10m': 'wind speed',
    'wind_speed_kt': 'wind speed',
    'wind_gusts_10m': 'wind gusts',
    'wind_direction': 'wind direction',
    'visibility': 'visibility',
    'pressure_msl': 'air pressure',
    'mslp': 'air pressure',
    'wave_height': 'the significant wave height',
    'wave_period': 'the wave period',
    'wave_direction': 'the wave direction',
    'river_discharge': 'river discharge',
    'us_aqi': 'the US air-quality index',
    'european_aqi': 'the European air-quality index',
    'pm2_5': 'PM2.5',
    'pm10': 'PM10',
    'nitrogen_dioxide': 'nitrogen dioxide',
    'ozone': 'ozone',
    'carbon_monoxide': 'carbon monoxide',
    'sulphur_dioxide': 'sulphur dioxide',
    'dew_point_2m': 'the dew point',
    'temperature_c': 'temperature',
}

# Parameters that a reader asked about as an amount of water rather than a chance of it. Used only to
# keep the sentence honest about which of the two it is stating.
_SERIES = {'temperature_2m', 'apparent_temperature', 'wind_speed_10m', 'wind_gusts_10m',
           'relative_humidity_2m', 'visibility', 'pressure_msl', 'wave_height', 'wave_period',
           'wave_direction', 'river_discharge', 'pm2_5', 'pm10', 'nitrogen_dioxide', 'ozone',
           'carbon_monoxide', 'sulphur_dioxide', 'temperature_2m_max', 'temperature_2m_min'}
_PEAK = {'precipitation_probability'}
_MISSING = 'not stated'


def parsed(value):
    """A timestamp as this module reads it, or None when it does not state one."""
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def short_place(label):
    """The place as the fact carries it, shortened only for the opening clause."""
    return str(label or '').split(',')[0].split('·')[0].strip() or 'The selected point'


EARLY = datetime.min.replace(hour=2).time()


def _last_covered(first, last):
    """The last day the window actually covers.

    A window that ends in the small hours of the following day covers the day it began on, not the day
    it stopped in: the model day 21 Sep 00:30–22 Sep 00:30 is the 21st, and calling it "from 21 to 22
    September" would name a day the answer does not cover. A window ending at 00:00 is the same case.
    """
    if last > first and last.date() > first.date() and last.time() <= EARLY:
        return last - timedelta(days=1)
    return last


def window_words(start, end, now):
    """The window in the words a reader used, so the sentence does not open with a timestamp.

    Two spellings of the same window: 'when' reads after 'for' ('rain is forecast for tomorrow') and
    'where' is the adverbial form ('temperature tomorrow is 26 °C'). A window that has already begun is
    'today'; the depth line carries the exact hours.
    """
    first, last = parsed(start), parsed(end)
    if first is None:
        return '', ''
    first = first.astimezone(IST)
    last = _last_covered(first, (last or first).astimezone(IST))
    today = (now or datetime.now(IST)).astimezone(IST).date()
    span = (last.date() - first.date()).days
    if span == 0:
        offset = (first.date() - today).days
        if offset == 0:
            return 'today', 'today'
        if offset == 1:
            return 'tomorrow', 'tomorrow'
        if offset == -1:
            return 'yesterday', 'yesterday'
        if 2 <= offset <= 6:
            spelled = 'on ' + first.strftime('%A')
            return spelled, spelled
        spelled = 'on ' + first.strftime('%-d %B')
        return spelled, spelled
    if first.date().year != last.date().year:
        return ('from ' + first.strftime('%-d %B %Y') + ' to ' + last.strftime('%-d %B %Y'),
                'over that period')
    if first.month == last.month:
        return ('from ' + first.strftime('%-d') + ' to ' + last.strftime('%-d %B'),
                'over ' + first.strftime('%-d') + '–' + last.strftime('%-d %B'))
    return ('from ' + first.strftime('%-d %B') + ' to ' + last.strftime('%-d %B'),
            'over that period')


def _decimal(text):
    try:
        return Decimal(str(text))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _precision(values):
    """The number of decimal places the source published, so a range is not shown more precisely."""
    places = 0
    for value in values:
        text = str(value)
        if '.' in text:
            places = max(places, len(text.split('.')[1].rstrip('0')) or 1)
    return places


def _show(value, places):
    number = _decimal(value)
    if number is None:
        return str(value)
    if places <= 0:
        return str(number.quantize(Decimal(1)))
    return str(number.quantize(Decimal(1).scaleb(-places)))


def value_words(rows):
    """The group's value as one token: the published value, or the min–max across its rows."""
    rows = [row for row in rows if row.get('value') not in (None, '')]
    if not rows:
        return None, None
    if len(rows) == 1:
        return str(rows[0]['value']), rows[0]
    numbers = [(row, _decimal(row['value'])) for row in rows]
    numbers = [(row, number) for row, number in numbers if number is not None]
    if not numbers:
        return str(rows[0]['value']), rows[0]
    places = _precision([row['value'] for row in rows])
    low = min(numbers, key=lambda item: item[1])[0]['value']
    high = max(numbers, key=lambda item: item[1])[0]['value']
    if places <= 0 and str(low) == str(high):
        return str(low), rows[0]
    if _decimal(low) == _decimal(high):
        return _show(low, places), rows[0]
    return _show(low, places) + '–' + _show(high, places), rows[-1]


def peak_row(rows):
    """The row carrying the largest value in a group, for a chance or a gust."""
    numbers = [(row, _decimal(row.get('value'))) for row in rows]
    numbers = [(row, number) for row, number in numbers if number is not None]
    if not numbers:
        return None
    return max(numbers, key=lambda item: item[1])[0]


def _clock(fact):
    moment = parsed(fact.get('sample_at') or fact.get('start'))
    return moment.astimezone(IST).strftime('%H:%M') if moment else ''


def _observed_at(fact):
    moment = parsed(fact.get('observed_at') or fact.get('sample_at') or fact.get('start'))
    return moment.astimezone(IST).strftime('%d %b, %H:%M') if moment else ''


def _place_phrase(packet):
    """The place to name in the opening, from the resolution the turn itself recorded."""
    for entry in (packet.get('resolved_points') or {}).values():
        if isinstance(entry, dict) and entry.get('label'):
            return short_place(entry['label'])
    label = ((packet.get('now_reading') or {}).get('label') or '')
    if label:
        return short_place(label)
    for place in ((packet.get('plan') or {}).get('places') or []):
        if place.get('name'):
            return short_place(place['name'])
    fact = next(iter(packet.get('facts') or []), None)
    return short_place(fact.get('place')) if fact else 'The selected point'


def _group(facts, parameters=None):
    """The rows a lead is composed from: the first requested measure that has rows."""
    if parameters:
        for parameter in parameters:
            rows = [fact for fact in facts if fact.get('parameter') == parameter]
            if rows:
                return parameter, rows
    parameter = facts[0].get('parameter') if facts else None
    return parameter, [fact for fact in facts if fact.get('parameter') == parameter]


def _forecast_sentence(place, parameter, rows, when, where):
    value, row = value_words(rows)
    unit = (row or {}).get('unit') or ''
    unit_text = (' ' + unit) if unit and unit not in {'index'} else ''
    if parameter == 'precipitation_probability':
        peak = peak_row(rows) or row
        if not peak:
            return None
        return (place + ': ' + where + ' the highest hourly rain chance is ' + str(peak.get('value')) +
                '% at ' + _clock(peak) + ' IST.')
    if value in (None, ''):
        return None
    if parameter == 'precipitation':
        return (place + ': rainfall of ' + str(value) + (unit_text or ' mm') + ' is forecast ' + when + '.')
    if parameter == 'precipitation_sum':
        return (place + ': ' + where + ' the daily rainfall total is ' + str(value) + (unit_text or ' mm') + '.')
    if parameter in _SERIES or parameter == 'temperature_2m':
        return (place + ': ' + MEASURE_WORDS.get(parameter, parameter) + ' ' + where + ' is ' +
                value + unit_text + '.')
    return (place + ': ' + where + ' ' + MEASURE_WORDS.get(parameter, 'the forecast value') + ' is ' +
            str(value) + unit_text + '.')


def _forecast_clause(parameter, rows):
    """One measure as a clause of a multi-measure sentence: the same values as the single-measure
    opening, in a shape that can be joined with the measures beside it."""
    value, row = value_words(rows)
    unit = (row or {}).get('unit') or ''
    unit_text = (' ' + unit) if unit and unit not in {'index'} else ''
    if parameter == 'precipitation_probability':
        peak = peak_row(rows) or row
        if not peak:
            return None
        return ('the highest hourly rain chance is ' + str(peak.get('value')) + '% at ' +
                _clock(peak) + ' IST')
    if value in (None, ''):
        return None
    if parameter == 'precipitation':
        return 'rainfall of ' + str(value) + (unit_text or ' mm') + ' is forecast'
    if parameter == 'precipitation_sum':
        return 'the daily rainfall total is ' + str(value) + (unit_text or ' mm')
    if parameter == 'wind_gusts_10m':
        return 'the wind gusts reach ' + value + unit_text
    if parameter in _SERIES or parameter == 'temperature_2m':
        return MEASURE_WORDS.get(parameter, parameter) + ' is ' + value + unit_text
    return MEASURE_WORDS.get(parameter, 'the forecast value') + ' is ' + str(value) + unit_text


def _forecast_multi(place, groups, when, where):
    """A question that asked for several measures is answered for all of them: one clause per measure,
    in the order the facts carry them. Past four measures the sentence states three and names the rest
    rather than reciting a spreadsheet — the rows themselves stay in the evidence."""
    clauses = []
    shown = groups[:3] if len(groups) > 4 else groups[:4]
    for parameter, rows in shown:
        clause = _forecast_clause(parameter, rows)
        if clause:
            clauses.append(clause)
    if not clauses:
        return None
    if len(groups) > len(shown):
        clauses.append(str(len(groups) - len(shown)) + ' more asked measures are in the evidence below')
    joined = ', '.join(clauses[:-1]) + (' and ' if len(clauses) > 1 else '') + clauses[-1]
    return place + ': ' + (where + ', ' if where else '') + joined + '.'


def _station_sentence(packet, rows, now, when):
    """A station report is a measurement at one place and instant; it is never the city's weather.

    The station's own name and distance are read from the line the fact already carries, so the sentence
    cannot invent a nearer station than the evidence did.
    """
    key = {'temperature_c': 0, 'temperature_2m': 0, 'wind_speed_kt': 1, 'wind_speed_10m': 1,
           'relative_humidity_2m': 2, 'mslp': 3, 'wind_direction': 4}
    rows = sorted(rows, key=lambda row: key.get(str(row.get('parameter')), 9))
    lead = rows[0] if rows else None
    if lead is None:
        return None
    line = str(lead.get('place') or '')
    station, _, tail = line.partition('·')
    station = station.strip() or 'Station'
    distance = tail.split('km')[0].strip() if 'km' in tail else ''
    requested = _place_phrase(packet)
    fields = {}
    for row in rows:
        if str(row.get('place') or '').split('·')[0].strip() != station:
            continue
        fields.setdefault(str(row.get('parameter')), row)
    parts = []
    temperature = fields.get('temperature_c') or fields.get('temperature_2m')
    if temperature is not None:
        parts.append(str(temperature.get('value')) + ' °C')
    wind = fields.get('wind_speed_kt') or fields.get('wind_speed_10m')
    if wind is not None:
        unit = 'kt' if str(wind.get('parameter')).endswith('_kt') else str(wind.get('unit') or '')
        parts.append(str(wind.get('value')) + (' ' + unit if unit else '') + ' wind')
    humidity = fields.get('relative_humidity_2m')
    if humidity is not None:
        parts.append(str(humidity.get('value')) + '% humidity')
    pressure = fields.get('mslp')
    if pressure is not None and len(parts) < 2:
        unit = str(pressure.get('unit') or '')
        parts.append(str(pressure.get('value')) + (' ' + unit if unit else '') + ' pressure')
    if not parts:
        return None
    at = _observed_at(lead)
    where = str(station) + ((' ' + str(round(float(distance), 1)) + ' km away') if distance else '')
    return ('The nearest station to ' + requested + ', ' + where + ', reported ' + ' and '.join(parts) +
            (' at ' + at + ' IST' if at else '') + '.')


def _window(packet, now):
    plan = packet.get('plan') or {}
    start, end = plan.get('start_local'), plan.get('end_local')
    if not start:
        fact = next(iter(packet.get('facts') or []), None)
        if fact:
            start, end = fact.get('start'), fact.get('end')
    return window_words(start, end, now)


def _air_quality_sentence(packet, facts, when, where):
    """An index is the source's own index; the sentence states it and never grades it.

    The provider's current hour is the freshest thing the product holds, so it leads when present, and
    the day's own series is stated as a range behind it rather than recited hour by hour.
    """
    place = _place_phrase(packet)
    def rows_for(parameter):
        return [row for row in facts if row.get('parameter') == parameter]
    index = None
    for name in ('us_aqi_current', 'us_aqi', 'european_aqi_current', 'european_aqi'):
        rows = rows_for(name)
        if rows:
            index = (name, rows)
            break
    if index is None:
        for name in ('pm2_5_current', 'pm2_5', 'pm10_current', 'pm10'):
            rows = rows_for(name)
            if rows:
                index = (name, rows)
                break
    if index is None:
        return None
    name, rows = index
    row = rows[0]
    current = name.endswith('_current')
    unit = str(row.get('unit') or '')
    label = MEASURE_WORDS.get(name.replace('_current', ''), name.replace('_current', ''))
    at = _observed_at(row)
    sentence = (place + ': ' + label + ' is ' + str(row.get('value')) +
                ((' ' + unit) if unit and unit not in {'index'} else '') +
                (' at ' + at + ' IST' if at else '') +
                (' (the provider\'s current hour)' if current else '') + '.')
    series = [item for item in rows_for(name.replace('_current', '')) if not current or item is not row]
    if series and not current:
        value, _row = value_words(series)
        if value and '–' in str(value):
            tail = ' ' + unit if unit and unit not in {'index'} else ''
            sentence += ' Across ' + (where or 'the day') + ' it runs ' + str(value) + tail + '.'
    return sentence


def _specialist_sentence(packet, place, parameter, rows, when, where):
    """Marine and river products always name the answering cell and never stand in for an observation."""
    value, row = value_words(rows)
    if value is None:
        return None
    unit = (row or {}).get('unit') or ''
    citation = next(iter(packet.get('citations') or []), None)
    answered = ''
    if isinstance(citation, dict) and citation.get('grid_distance_km') is not None:
        answered = ' (answering cell ' + str(round(float(citation['grid_distance_km']), 1)) + ' km away)'
    measure = MEASURE_WORDS.get(parameter, parameter)
    if parameter == 'river_discharge':
        return (place + ': modelled river discharge is ' + value + (' ' + unit if unit else '') + answered +
                '. This is a modelled flow volume, not an observed water level, gauge reading or danger level.')
    if parameter == 'wave_height':
        return (place + ': ' + measure + ' is forecast at ' + value + (' ' + unit if unit else '') + answered + '.')
    return (place + ': ' + measure + ' is forecast at ' + value + (' ' + unit if unit else '') + answered + '.')


def _reanalysis_window(rows):
    """The IST calendar span these daily rows actually cover, for a sentence that must not overstate it."""
    from .transport import parsed
    try:
        first, last = parsed(rows[0]['start']), parsed(rows[-1]['end'])
    except (KeyError, TypeError, ValueError):
        return ''
    first, last = first.astimezone(IST), last.astimezone(IST) - timedelta(days=1)
    if first.date() == last.date():
        return 'on ' + first.strftime('%d %b %Y')
    if (first.year, first.month) == (last.year, last.month):
        return 'from ' + first.strftime('%d') + ' to ' + last.strftime('%d %b %Y')
    return 'from ' + first.strftime('%d %b') + ' to ' + last.strftime('%d %b %Y')


def _history_sentence(place, parameter, rows, packet):
    row = rows[0]
    year = row.get('year')
    period = str(row.get('period') or '').replace('_', ' ')
    # A daily reanalysis window is not an entry in the curated annual series, and must not borrow its
    # words. Measured 20 September 2026: a seven-day ERA5 window opened "Ahmedabad: the annual rainfall
    # was 0.4-94.3 mm (published record)" - that range is the spread of DAILY values, the window was a
    # week, and "published record" names the 1901-2010 table this number did not come from. The cause is
    # structural rather than about span: point-task facts carry no `period` and no `year`, so the
    # annual default below fired on absence. These rows get their own sentence instead.
    if row.get('evidence_kind') == 'reanalysis' and not year and not period:
        value, _representative = value_words(rows)
        if value is None:
            return None
        unit = (' ' + row['unit']) if row.get('unit') else ''
        measure = MEASURE_WORDS.get(parameter, parameter)
        when = _reanalysis_window(rows)
        if len(rows) == 1:
            return (place + ': ' + measure + ' was ' + value + unit + (' ' + when if when else '') +
                    ' (ERA5 reanalysis, not a gauge reading).')
        # "How much rain did Ahmedabad get in August" is asking for a total, so the sentence opens with
        # the total when the tool computed one, and keeps the daily spread as the second clause. Leading
        # with the spread answers a question the reader did not ask.
        # Matched on the fact's OWN place label, not the short name in the sentence: with two places in
        # one answer, a looser match would attribute one city's total to the other.
        owner = str(row.get('place') or '')
        total = next((c for c in (packet.get('calculations') or [])
                      if owner and str(c.get('label', '')).startswith(owner + ' \u00b7 ')
                      and 'total' in str(c.get('label', '')).lower()), None)
        if total and total.get('value') is not None:
            return (place + ': ' + str(total['value']) + ((' ' + total['unit']) if total.get('unit') else '') +
                    ' of ' + measure + ' in total ' + (when + ' ' if when else '') +
                    '(ERA5 reanalysis, not a gauge reading). Daily values ranged ' + value + unit + '.')
        return (place + ': daily ' + measure + ' ranged ' + value + unit + (' ' + when if when else '') +
                ' (ERA5 reanalysis, not a gauge reading).')
    when = str(year) if year else ''
    unit = row.get('unit') or ''
    value, _representative = value_words(rows)
    if value is None:
        return None
    measure = MEASURE_WORDS.get(parameter, parameter)
    if period and period.lower() not in {'annual', ''}:
        measure = period + ' ' + measure
    else:
        measure = 'annual ' + measure if not str(measure).startswith('annual') else measure
    unit_text = (' ' + unit) if unit else ''
    if parameter == 'rainfall':
        return (place + ': recorded rainfall was ' + value + unit_text + (' in ' + when if when else '') +
                ' (published record, not a forecast).')
    return (place + ': the ' + measure + ' was ' + value + unit_text +
            (' in ' + when if when else '') + ' (published record).')


def _aviation_sentence(packet, place, rows):
    report = next(iter(packet.get('airport_reports') or []), None)
    station = (report or {}).get('station') or place
    at = ''
    if report:
        at = _observed_at({'observed_at': report.get('observed_at_utc')})
    temperature = next((row for row in rows if row.get('parameter') == 'temperature_c'), None)
    wind = next((row for row in rows if row.get('parameter') == 'wind_speed_kt'), None)
    parts = []
    if temperature is not None:
        parts.append(str(temperature.get('value')) + ' °C')
    if wind is not None:
        parts.append(str(wind.get('value')) + ' kt wind')
    if not parts:
        return None
    return (str(station) + ': the airport report states ' + ' and '.join(parts) +
            (' at ' + at + ' IST' if at else '') + '.')


def _document_sentence(packet, place):
    evidence = next(iter(packet.get('document_evidence') or []), None)
    passages = packet.get('passages') or []
    if not evidence and not passages:
        return None
    district = (evidence or {}).get('district') or place
    issue = (evidence or {}).get('issue_date') or ''
    count = len(passages)
    return (str(district) + ' district: the published agricultural bulletin' +
            (' dated ' + str(issue) if issue else '') + ' carries ' + str(count) +
            ' matching passage' + ('' if count == 1 else 's') + ' from the source edition.')


def _ensemble_sentence(packet, place, parameter, rows, when, where):
    value, row = value_words(rows)
    if value is None:
        return None
    unit = (row or {}).get('unit') or ''
    members = len({str(item.get('member') or item.get('source_locator') or index)
                   for index, item in enumerate(rows)})
    measures = {item.get('parameter') for item in rows}
    measure = MEASURE_WORDS.get(parameter, parameter)
    return (place + ': ' + where + ' the ensemble spreads ' + measure + ' across ' + value +
            (' ' + unit if unit else '') + ' in ' + str(members) + ' members, one measure at a time.')


def lead_sentence(packet, kind=None, clock=None, language='en', now=None):
    """The one sentence that opens this answer, or None when the packet states no finding.

    A packet with a key 'lead' already composed keeps it: the sentence is owned here and is not
    recomposed by whichever renderer happens to run next. A turn whose answer is not written in English
    composes nothing here rather than opening a Hindi or Gujarati answer with an English sentence; those
    templates are owned by the language path, where the value-invariant check also lives.
    """
    if not isinstance(packet, dict):
        return None
    if packet.get('lead'):
        return packet['lead']
    if str(language or 'en').lower().split('-')[0] not in {'en', ''}:
        return None
    facts = [fact for fact in packet.get('facts') or [] if isinstance(fact, dict)]
    if not facts:
        return None
    kind = kind or (packet.get('plan') or {}).get('intent') or ''
    place = _place_phrase(packet)
    now = clock or now or parsed(packet.get('answered_at_utc')) or datetime.now(IST)
    when, where = _window(packet, now)
    if kind == 'aviation':
        return _aviation_sentence(packet, place, facts)
    if kind == 'observation':
        return _station_sentence(packet, facts, now, when)
    if kind in {'marine', 'river'}:
        parameter, rows = _group(facts)
        return _specialist_sentence(packet, place, parameter, rows, when, where)
    if kind in {'document', 'agriculture'}:
        return _document_sentence(packet, place)
    if kind in {'history', 'research'}:
        parameter, rows = _group(facts)
        return _history_sentence(place, parameter, rows, packet)
    if kind == 'air_quality' or any(str(fact.get('parameter') or '').endswith('_current') for fact in facts):
        return _air_quality_sentence(packet, facts, when, where)
    parameter, rows = _group(facts)
    if parameter is None:
        return None
    if str(parameter).endswith(('_aqi', '_current')) or parameter in {'pm2_5', 'pm10', 'nitrogen_dioxide',
                                                                     'ozone', 'carbon_monoxide', 'sulphur_dioxide',
                                                                     'us_aqi', 'european_aqi'}:
        return _air_quality_sentence(packet, facts, when, where)
    if kind == 'ensemble':
        return _ensemble_sentence(packet, place, parameter, rows, when, where)
    groups = []
    for fact in facts:
        name = fact.get('parameter')
        if name not in {group[0] for group in groups}:
            groups.append((name, [item for item in facts if item.get('parameter') == name]))
    if len(groups) > 1:
        sentence = _forecast_multi(place, groups, when, where)
        if sentence:
            return sentence
    sentence = _forecast_sentence(place, parameter, rows, when, where)
    if sentence:
        return sentence
    value, row = value_words(rows)
    if value is None:
        return None
    unit = (row or {}).get('unit') or ''
    return (place + ': ' + where + ' ' + MEASURE_WORDS.get(parameter, parameter) + ' is ' + value +
            (' ' + unit if unit else '') + '.')


def join_lead_tail(lead, tail):
    """The answer a reader gets: the tool-owned opening, then the model's continuation.

    A continuation that restates the opening is dropped rather than printed twice: the model was told the
    opening is fixed, and the first eight words repeating is the model ignoring that, not a second fact.
    """
    import re as _re
    opening = str(lead or '').strip()
    body = str(tail or '').strip()
    if not opening:
        return body
    if not body:
        return opening
    words = _re.sub(r'[^a-z0-9]+', ' ', opening.lower()).split()
    if len(words) >= 4:
        head = ' '.join(words[:8])
        if head in _re.sub(r'[^a-z0-9]+', ' ', body.lower()):
            return opening
    return opening + ' ' + body


def numeral_ratio(text):
    """Numerals per word in a composed answer. A serving decision, not a measurement of quality."""
    words = len(str(text or '').split())
    if not words:
        return 0.0
    digits = 0
    token = ''
    for character in str(text):
        if character.isdigit() or (character == '.' and token):
            token += character
        else:
            if token:
                digits += 1
            token = ''
    if token:
        digits += 1
    return digits / words


def within_budget(text, limit=0.34, floor_words=40):
    """Whether a composed answer recites more than it states.

    The forecast answers measured on 20 September 2026 sit at 0.39 numerals per word and read as a
    sentence; the ensemble answer sits at 0.56 and reads as a spreadsheet. The threshold is a serving
    decision with the same standing as the type floor: past it, the tail belongs in the fold.
    """
    words = len(str(text or '').split())
    if words <= floor_words:
        return True
    return numeral_ratio(text) <= limit