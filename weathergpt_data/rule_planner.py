"""Rules-first interpretation for the core problem-statement shapes.

A plan is a candidate, never evidence: it names tasks and a window, and every value in the
answer still comes from a governed retrieval. This module exists so the product works when no
model is reachable, and so the common shapes are planned the same way every time.

It returns a request in the planner schema (the shape the model returns), or None when the
question is outside the recognised shapes - a follow-up, an Indic script, a rarity - in which
case the caller must use a model rather than guess.
"""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo('Asia/Kolkata')
INDIC = re.compile(r'[\u0900-\u0d7f]')
HINGLISH = re.compile(r'\b(barish|baarish|paani|kya|kitni|kitna|kal|aaj|shaam|subah|dopahar|raat|'
                      r'mausam|hogi|hoga|sambhavna|tapman|havaman|varsha|varsad)\b', re.I)
FOLLOW_UP = re.compile(r'^\s*(and|what about|how about|aur|us|iska|iske|then|also\b)', re.I)
DAY_WORDS = {'today': 0, 'aaj': 0, 'tomorrow': 1, 'kal': 1, 'tonight': 0, 'parso': 2}
WINDOWS = {'morning': ('09:30', '12:30'), 'subah': ('09:30', '12:30'),
           'afternoon': ('12:30', '18:30'), 'dopahar': ('12:30', '18:30'),
           'evening': ('18:30', '22:30'), 'shaam': ('18:30', '22:30'),
           'night': ('21:30', '23:30'), 'raat': ('21:30', '23:30'), 'tonight': ('21:30', '23:30')}
VARIABLE_WORDS = (
    (re.compile(r'\b(chance|probability|chances|possibilit|sambhavna)\b', re.I), 'precipitation_probability'),
    (re.compile(r'\b(feels like|apparent)\b', re.I), 'apparent_temperature'),
    (re.compile(r'\b(gust|gusts|gusty)\b', re.I), 'wind_gusts_10m'),
    (re.compile(r'\b(visibility|fog|mist)\b', re.I), 'visibility'),
    (re.compile(r'\b(rain|rainfall|precipitation|shower|barish|baarish|varsha|barsat|paani)\b', re.I), 'precipitation'),
    (re.compile(r'\b(temperature|temp|hot|cold|warm|cool|tapman|garmi|thand)\b', re.I), 'temperature_2m'),
    (re.compile(r'\b(humidity|humid|moisture)\b', re.I), 'relative_humidity_2m'),
    (re.compile(r'\b(wind|windy|breeze|havaman)\b', re.I), 'wind_speed_10m'),
)
PLACE = re.compile(r"\b(?:in|for|at|near|around|of)\s+((?:[A-Z][\w'\u2019.\-]+)(?:\s+(?:[A-Z][\w'\u2019.\-]+)){0,3})"
                   r"(?:\s*,\s*([A-Z][\w'\u2019.\-]+(?:\s+[A-Z][\w'\u2019.\-]+){0,2}))?")
CROP = re.compile(r'\b(cotton|wheat|rice|paddy|maize|groundnut|sugarcane|soybean|bajra|jowar|mustard|onion|'
                  r'potato|tomato|mango|banana|pulses|gram|turmeric|chilli|grapes)\b', re.I)
CROP_TOPIC = ((re.compile(r'\b(irrigation|water|irrigate|sinchai)\b', re.I), 'irrigation'),
              (re.compile(r'\b(sow|sowing|plant|planting|transplant|buvai)\b', re.I), 'sowing'),
              (re.compile(r'\b(pest|insect|disease|borer|rust|blight|fungus|weed)\b', re.I), 'pest'),
              (re.compile(r'\b(fertilis|fertiliz|nutrient|urea|manure|khaad)\b', re.I), 'nutrition'),
              (re.compile(r'\b(harvest|harvesting|cutting|threshing)\b', re.I), 'harvest'))
MARINE = re.compile(r'\b(wave|waves|swell|sea state|significant wave|sea condition|samudra|lehar)\b', re.I)
RIVER = re.compile(r'\b(river discharge|discharge|streamflow|stream flow)\b', re.I)
WARNING = re.compile(r'\b(warning|warnings|alert|alerts|red alert|orange alert|yellow alert|advisory)\b', re.I)
AVIATION = re.compile(r'\b(metar|taf|airport|aerodrome|terminal forecast)\b', re.I)
DOCUMENT = re.compile(r"\b(bulletin|advisory document|press release|special advisory|flash flood guidance|"
                      r"all india weather summary)\b", re.I)
HISTORY = re.compile(r'\b(\d{4})\b')
HISTORY_WORDS = re.compile(r'\b(rainfall|rain|temperature|climat|historical|annual|monsoon|decade|trend|'
                           r'record|normal|average)\b', re.I)
OBSERVATION = re.compile(r'\b(right now|currently|at the moment|live observation|observed|observation station)\b', re.I)
OUT_OF_SCOPE = re.compile(r'\b(groundwater|water table|soil moisture|soil health|population|water quality|'
                          r'pesticide dose|dosage|yield forecast)\b', re.I)
WHOLE_DOC = re.compile(r'\b(main points?|overall|summar|synoptic|whole (?:document|edition|bulletin)|'
                       r"what does .{0,60}(?:bulletin|advisory|release) say)\b", re.I)
MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
SEASONS = {'winter': 'jf', 'pre-monsoon': 'mam', 'monsoon': 'jjas', 'post-monsoon': 'ond'}


def language_of(question):
    """The question's language for the planner field, or None when rules must not guess."""
    if INDIC.search(question):
        return None
    if HINGLISH.search(question):
        return 'hi-Latn'
    return 'en'


def window_for(question, now):
    """Local IST window for the named day and part of day, with the product's boundaries."""
    lower = question.lower()
    offset = None
    basis = None
    for word, days in DAY_WORDS.items():
        if re.search(r'\b' + word + r'\b', lower):
            offset, basis = days, word
            break
    part = None
    for word in WINDOWS:
        if re.search(r'\b' + word + r'\b', lower):
            part = word
            break
    clock = re.findall(r'\b([01]?\d|2[0-3])[:.]([0-5]\d)\b', question)
    if offset is None and not clock:
        return '', '', False, None
    day = (now.astimezone(IST) + timedelta(days=offset or 0)).date()

    def stamp(hhmm, minute=None):
        hour, minute = int(hhmm[:2]), int(hhmm[3:5])
        return (datetime(day.year, day.month, day.day, hour, minute, tzinfo=IST)).isoformat()

    if clock:
        first = '%02d:%s' % (int(clock[0][0]), clock[0][1])
        if len(clock) > 1:
            last = '%02d:%s' % (int(clock[1][0]), clock[1][1])
        else:
            last = '%02d:%s' % (min(int(clock[0][0]) + 3, 23), clock[0][1])
        return stamp(first), stamp(last), True, basis or 'explicit clock times'
    start, end = WINDOWS.get(part) or ('00:30', '23:30')
    label = (str(basis) + ' ' + str(part)) if part else (str(basis) + ' whole day')
    return stamp(start), stamp(end), False, label


def places_of(question):
    """Named places with an optional state, as written; the gazetteer resolves them."""
    found = []
    for match in PLACE.finditer(question):
        name = (match.group(1) or '').strip(' .,')
        state = (match.group(2) or '').strip(' .,')
        if not name or name.lower() in {'the', 'a', 'my', 'this', 'that'} or len(name) < 3:
            continue
        if name in [item['name'] for item in found]:
            continue
        found.append({'name': name, 'state': state, 'district': '', 'kind': 'unknown'})
        if len(found) == 2:
            break
    return found


def variables_of(question):
    variables = []
    for pattern, name in VARIABLE_WORDS:
        if pattern.search(question) and name not in variables:
            variables.append(name)
    return variables


def history_years(question):
    return sorted({int(value) for value in HISTORY.findall(question) if 1800 <= int(value) <= 2200})


def rule_request(question, now, history=None):
    """A planner request for a recognised shape, or None to fall through to a model."""
    if not isinstance(question, str) or not question.strip():
        return None
    language = language_of(question)
    if language is None:
        return None
    if FOLLOW_UP.search(question):
        return None
    places = places_of(question)
    start, end, explicit, basis = window_for(question, now)
    quote = question.strip()
    tasks = []

    def task(kind, operation, parameters, **extra):
        entry = {'request_quote': quote[:400], 'kind': kind, 'operation': operation,
                 'parameters': parameters, 'years': [], 'period': 'annual',
                 'start_local': start, 'end_local': end, 'place_indices': list(range(len(places)))}
        entry.update(extra)
        return entry

    years = history_years(question)
    if OUT_OF_SCOPE.search(question) and not (WARNING.search(question) or DOCUMENT.search(question)):
        tasks.append(task('research', 'lookup', []))
    elif WARNING.search(question) and not DOCUMENT.search(question):
        tasks.append(task('warning', 'lookup', ['official_warning']))
    elif HISTORY_WORDS.search(question) and years and not DOCUMENT.search(question):
        parameter = 'temperature' if re.search(r'\btemperature\b', question, re.I) else 'rainfall'
        operation = 'lookup'
        if re.search(r'\b(trend|warming|changing)\b', question, re.I):
            operation = 'trend'
        elif len(years) > 1 and re.search(r'\b(compare|comparison|versus|vs|difference)\b', question, re.I):
            operation = 'compare'
        elif len(years) > 1:
            operation = 'series'
        entry = task('history', operation, [parameter], years=years[:2] if operation == 'compare' else years)
        entry['start_local'] = ''
        entry['end_local'] = ''
        for name in MONTHS:
            if re.search(r'\b' + name + r'\b', question, re.I):
                entry['period'] = name
                break
        for name, code in SEASONS.items():
            if name in question.lower():
                entry['period'] = code
                break
        tasks.append(entry)
    elif MARINE.search(question):
        parameters = ['wave_height']
        if re.search(r'\b(direction)\b', question, re.I):
            parameters = ['wave_direction']
        elif re.search(r'\b(period|interval)\b', question, re.I):
            parameters = ['wave_period']
        tasks.append(task('marine', 'lookup', parameters))
    elif RIVER.search(question):
        tasks.append(task('river', 'lookup', ['river_discharge']))
    elif AVIATION.search(question):
        code = re.search(r'\b([A-Z]{4})\b', question)
        parameters = ['taf'] if re.search(r'\btaf\b', question, re.I) else ['metar']
        entry = task('aviation', 'lookup', parameters)
        if code and code.group(1) not in [item['name'].upper() for item in places]:
            places = places + [{'name': code.group(1), 'state': '', 'district': '', 'kind': 'unknown'}]
            entry['place_indices'] = [len(places) - 1]
        elif code:
            entry['place_indices'] = [index for index, item in enumerate(places)
                                      if item['name'].upper() == code.group(1)]
        tasks.append(entry)
    elif DOCUMENT.search(question):
        family = ''
        for word, name in (('all india weather summary', 'national_bulletin'), ('flash flood', 'flash_flood_national'),
                           ('extended range', 'extended_range'), ('press release', 'press_release'),
                           ('special advisory', 'special_advisory'), ('agromet', 'state_agromet'),
                           ('district bulletin', 'state_district_bulletin'), ('sea area', 'sea_area_bulletin'),
                           ('coastal', 'coastal_bulletin')):
            if word in question.lower():
                family = name
                break
        scope = ''
        if family in {'state_agromet', 'state_district_bulletin'}:
            scope = 'state'
        elif family in {'national_bulletin', 'extended_range', 'press_release', 'erf_marquee',
                        'flash_flood_national', 'flash_flood_sasia'}:
            scope = 'national'
        elif family:
            scope = 'marine'
        request = {'query': quote[:1500], 'family': family, 'scope': scope}
        if WHOLE_DOC.search(question):
            request['whole_document'] = True
        tasks.append(task('document', 'lookup', ['published_document'], corpus_request=request))
    elif CROP.search(question) or re.search(r'\b(crop|field|farm|kisan|fasal)\b', question, re.I):
        found = CROP.search(question)
        topic = 'general'
        for pattern, name in CROP_TOPIC:
            if pattern.search(question):
                topic = name
                break
        mode = 'decision_support' if re.search(r'\b(should i|can i|is it safe|my (crop|field))\b', question, re.I) else 'source_lookup'
        request = {'query': quote[:1500], 'crop': found.group(1).lower() if found else '',
                   'growth_stage': '', 'topic': topic, 'mode': mode}
        tasks.append(task('agriculture', 'lookup', ['agricultural_advisory'], document_request=request))
    elif OBSERVATION.search(question):
        tasks.append(task('observation', 'lookup', []))
    else:
        variables = variables_of(question)
        if not variables:
            return None
        tasks.append(task('forecast', 'lookup', variables))
    assumptions = []
    if basis:
        assumptions.append('Time window read from the question: ' + str(basis) + '.')
    return {'language': language, 'places': places, 'assumptions': assumptions, 'clarification': '',
            'explicit_times': explicit, 'tasks': tasks, 'context_action': 'new',
            'changed_fields': ['places', 'time', 'parameters']}
