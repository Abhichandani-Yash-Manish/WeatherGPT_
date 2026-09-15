"""Cross-product comparison: what two published products say about the same window.

A turn can retrieve an official district warning, a model forecast and a published bulletin at
once. Each product answers a different question, and the workspace never ranks them or turns a
comparison into a score. What this module does is state, in plain terms, where two products
speak about the same place and window and whether they point the same way - or say honestly
that they cannot be compared, with the reason.

Readings are deterministic and narrow on purpose:

- consistent: the official day names a rain or storm hazard and the overlapping model forecast
  shows rain in the same window (or the bulletin names rain and the forecast shows rain).
- differ: the official day names a rain or storm hazard while the forecast shows no rain in the
  overlapping window, or the bulletin text names rain while the forecast total is zero.
- not_comparable: a quiet day (which is not a forecast of no rain), a hazard this forecast does
  not measure (heat, fog, cold), or no overlapping window at all.
"""
from datetime import datetime

RAIN_HAZARD = ('rain', 'thunder', 'squall', 'lightning', 'hail', 'shower', 'storm', 'wind', 'gust', 'cyclone')
RAIN_TEXT = ('rain', 'thunder', 'shower', 'squall', 'heavy', 'downpour', 'hail')
OTHER_HAZARD = ('heat', 'fog', 'cold', 'frost', 'hot', 'humid')
MAX_ITEMS = 4
NOTE = ('Both products are named here and neither is ranked; a comparison is not a score, a '
        'skill measurement or a warning. Only the official product speaks about warnings, and a '
        'quiet day in it is not a forecast of no rain.')
MEASURED = ('precipitation', 'precipitation_probability', 'wind_speed_10m', 'wind_gusts_10m')
DISCLAIMER = ('Products compared: {summary} Both products are named and neither is ranked; this '
              'comparison is not a score and not an all-clear.')


def _parsed(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def _overlaps(left, right):
    if not left or not right:
        return False
    start_a, end_a = left
    start_b, end_b = right
    return start_a < end_b and start_b < end_a


def _warning_days(result):
    days = []
    for block in result.get('warning_evidence') or []:
        for district in block.get('district_warnings') or []:
            for day in district.get('days') or []:
                days.append({'place': district.get('place') or district.get('district'),
                             'label': day.get('label') or ('day ' + str(day.get('day'))),
                             'colour': day.get('colour'), 'hazards': day.get('hazards') or [],
                             'quiet': bool(day.get('quiet')), 'starts': _parsed(day.get('starts_utc')),
                             'ends': _parsed(day.get('ends_utc'))})
    return days


def _forecast_facts(result):
    facts = []
    for fact in result.get('facts') or []:
        if fact.get('parameter') not in MEASURED:
            continue
        facts.append({'parameter': fact.get('parameter'), 'value': fact.get('value'),
                      'unit': fact.get('unit'), 'place': fact.get('place'), 'source_id': fact.get('source_id'),
                      'starts': _parsed(fact.get('start')), 'ends': _parsed(fact.get('end')),
                      'label': fact.get('label')})
    return facts


def _total(facts):
    values = []
    for fact in facts:
        try:
            values.append(float(str(fact['value']).split()[0]))
        except (TypeError, ValueError, IndexError):
            return None
    return sum(values) if values else None


def _hazard_kind(hazards):
    lowered = ' '.join(hazards).lower()
    if any(word in lowered for word in RAIN_HAZARD):
        return 'rain_or_storm'
    if any(word in lowered for word in OTHER_HAZARD):
        return 'other'
    return 'unknown'


def warning_and_forecast(warning, forecast):
    """One item comparing an official district-warning day with model forecast facts."""
    window = (warning['starts'], warning['ends'])
    overlapping = [fact for fact in forecast if _overlaps(window, (fact['starts'], fact['ends']))]
    if not overlapping:
        return None
    kind = _hazard_kind(warning['hazards'])
    if warning['quiet'] or kind == 'unknown':
        return None
    place = warning.get('place') or (overlapping[0].get('place') or 'the selected point')
    statement = (', '.join(str(item) for item in warning['hazards'][:3]) or 'no hazard text published')
    official = {'source_id': 'S15', 'product': 'IMD district warning product',
                'statement': (warning['colour'] or 'colour not supplied') + ' · ' + statement}
    if kind == 'other':
        return {'kind': 'official_warning_and_forecast', 'place': place,
                'window': {'label': warning['label']},
                'products': [official, {'source_id': overlapping[0].get('source_id'),
                                        'product': 'Model forecast',
                                        'statement': overlapping[0]['parameter'] + ' measured for the same window'}],
                'reading': 'not_comparable',
                'why': ('the official day names ' + statement + ', which this forecast does not measure; the '
                        'official product is the only one that speaks about the warning'),
                'note': NOTE}
    rain = [fact for fact in overlapping if fact['parameter'] == 'precipitation']
    if not rain:
        return {'kind': 'official_warning_and_forecast', 'place': place, 'window': {'label': warning['label']},
                'products': [official, {'source_id': overlapping[0].get('source_id'), 'product': 'Model forecast',
                                        'statement': 'no forecast rainfall total was retrieved for this window'}],
                'reading': 'not_comparable',
                'why': 'the forecast retrieved for this window carries no rainfall total to compare',
                'note': NOTE}
    total = _total(rain)
    forecast_statement = ('rainfall ' + ('not stated' if total is None else format(total, '.1f')) +
                          ' ' + (rain[0].get('unit') or 'mm') + ' across ' + str(len(rain)) + ' forecast value(s)')
    products = [official, {'source_id': rain[0].get('source_id'), 'product': 'Model forecast',
                           'statement': forecast_statement}]
    if total is None:
        return {'kind': 'official_warning_and_forecast', 'place': place, 'window': {'label': warning['label']},
                'products': products, 'reading': 'not_comparable',
                'why': 'the forecast total could not be read as a number, so nothing was compared', 'note': NOTE}
    if total > 0:
        return {'kind': 'official_warning_and_forecast', 'place': place, 'window': {'label': warning['label']},
                'products': products, 'reading': 'consistent',
                'why': 'both name rain in this window', 'note': NOTE}
    return {'kind': 'official_warning_and_forecast', 'place': place, 'window': {'label': warning['label']},
            'products': products, 'reading': 'differ',
            'why': ('the official product carries a rain or storm hazard for this window while the model '
                    'forecast shows no rain in it; neither product is a measurement of the other'),
            'note': NOTE}


def bulletin_and_forecast(passage, forecast):
    """One item comparing a published passage that names rain with model forecast facts."""
    text = ' '.join(str(passage.get('text') or '').split())
    if not text or not any(word in text.lower() for word in RAIN_TEXT):
        return None
    if not forecast or not passage.get('physical_page'):
        return None
    rain = [fact for fact in forecast if fact['parameter'] == 'precipitation']
    if not rain:
        return None
    total = _total(rain)
    excerpt = text[:200] + (' …' if len(text) > 200 else '')
    products = [{'source_id': passage.get('source_id'), 'product': 'Published ' + str(passage.get('family') or 'document'),
                 'statement': 'page ' + str(passage.get('physical_page')) + ': “' + excerpt + '”'},
                {'source_id': rain[0].get('source_id'), 'product': 'Model forecast',
                 'statement': 'rainfall ' + ('not stated' if total is None else format(total, '.1f')) + ' ' +
                              (rain[0].get('unit') or 'mm') + ' for the same place'}]
    reading = 'not_comparable' if total is None else ('consistent' if total > 0 else 'differ')
    why = ('the published text names rain and the forecast shows rain in the same window' if reading == 'consistent'
           else 'the published text names rain while the forecast shows none in the same window'
           if reading == 'differ' else 'the forecast total could not be read as a number')
    return {'kind': 'bulletin_and_forecast', 'place': passage.get('district') or passage.get('region') or 'the document',
            'window': {'label': 'printed issue ' + str(passage.get('issue_date') or 'not stated')},
            'products': products, 'reading': reading, 'why': why, 'note': NOTE}


def compare_products(result):
    """The comparison items for one turn, or an empty list when there is nothing to compare."""
    warning_days = _warning_days(result)
    forecast = _forecast_facts(result)
    passages = result.get('passages') or []
    items = []
    if warning_days and forecast:
        for day in warning_days:
            item = warning_and_forecast(day, forecast)
            if item:
                items.append(item)
            if len(items) >= MAX_ITEMS:
                break
    if passages and forecast and len(items) < MAX_ITEMS:
        for passage in passages:
            item = bulletin_and_forecast(passage, forecast)
            if item:
                items.append(item)
            if len(items) >= MAX_ITEMS:
                break
    return items


def summarise(items):
    """One bounded sentence for the answer text, naming both sides and refusing to rank them."""
    if not items:
        return None
    first = items[0]
    sides = ' and '.join(product['product'] for product in first['products'][:2])
    readings = sorted({item['reading'] for item in items})
    summary = (str(first['place']) + ' (' + str(first['window'].get('label')) + '): ' + sides + ' are '
               + ('consistent' if readings == ['consistent'] else 'not directly comparable'
                  if readings == ['not_comparable'] else 'not saying the same thing') + ' — ' + first['why'] + '.')
    if len(items) > 1:
        summary += ' ' + str(len(items) - 1) + ' further comparison(s) are in the receipt.'
    return DISCLAIMER.format(summary=summary)
