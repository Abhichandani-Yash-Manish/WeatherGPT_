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

from .gazetteer import norm

IST = ZoneInfo('Asia/Kolkata')
INDIC = re.compile(r'[\u0900-\u0d7f]')
HINGLISH = re.compile(r'\b(barish|baarish|paani|kya|kitni|kitna|kal|aaj|shaam|subah|dopahar|raat|'
                      r'mausam|hogi|hoga|sambhavna|tapman|havaman|varsha|varsad)\b', re.I)
FOLLOW_UP = re.compile(r'^\s*(and|what about|how about|aur|us|iska|iske|then|also\b)', re.I)
# Words that point at something already said. A first question may use them harmlessly
# ("that place in Gujarat"), but in a live conversation they mean the model must read the
# context rather than the rules inventing a fresh task from a sentence fragment.
CONTEXT_REFERENCE = re.compile(r'\b(that|this|same|those|these|it|its|there|then|too|also|as well|again|'
                               r'previous|earlier|latter|former|above)\b', re.I)
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
PLACE = re.compile(r"\b(?:in|for|at|near|around|of|off)\s+(?:the |a |an )?((?:[A-Z][\w'\u2019.\-]+)(?:\s+(?:[A-Z][\w'\u2019.\-]+)){0,3})"
                   r"(?:\s*,\s*([A-Z][\w'\u2019.\-]+(?:\s+[A-Z][\w'\u2019.\-]+){0,2}))?")
# A named administrative unit: "Ahmedabad district", "Gujarat state", "Kochi city".
PLACE_UNIT = re.compile(r"\b((?:[A-Z][\w'\u2019.\-]+)(?:\s+(?:[A-Z][\w'\u2019.\-]+)){0,2})\s+"
                        r"(district|state|city|town|village|tehsil|taluk)\b")
# Hinglish marks the place after the name: "Ahmedabad me", "Surat ke liye".
PLACE_HINGLISH = re.compile(r"\b((?:[A-Z][\w'\u2019.\-]+)(?:\s*,?\s+(?:[A-Z][\w'\u2019.\-]+)){0,2})\s+"
                            r"(?:me|mein|men|par|ka|ki|ke)\b")
# A coast, a sea or coastal waters: a region, never a settlement to search for.
SEA_WORDS = re.compile(r'\b(?:coast|coastal|sea|waters?|shore|offshore)\b', re.I)
PLACE_NOISE = {'the', 'a', 'an', 'this', 'that', 'my', 'our', 'whole', 'latest', 'said'}
# A capitalised day or part-of-day word at the start of a sentence is not part of a place name:
# "Kal Ahmedabad me" is Ahmedabad, and "Aaj Delhi me" is Delhi.
PLACE_LEAD_NOISE = {'kal', 'aaj', 'parso', 'tomorrow', 'today', 'tonight', 'subah', 'shaam', 'raat',
                    'dopahar', 'morning', 'evening', 'afternoon', 'night'}
CROP = re.compile(r'\b(cotton|wheat|rice|paddy|maize|groundnut|sugarcane|soybean|bajra|jowar|mustard|onion|'
                  r'potato|tomato|mango|banana|pulses|gram|turmeric|chilli|grapes)\b', re.I)
CROP_TOPIC = ((re.compile(r'\b(irrigation|water|irrigate|sinchai)\b', re.I), 'irrigation'),
              (re.compile(r'\b(sow|sowing|plant|planting|transplant|buvai)\b', re.I), 'sowing'),
              (re.compile(r'\b(pest|insect|disease|borer|rust|blight|fungus|weed)\b', re.I), 'pest'),
              (re.compile(r'\b(fertilis|fertiliz|nutrient|urea|manure|khaad)\b', re.I), 'nutrition'),
              (re.compile(r'\b(harvest|harvesting|cutting|threshing)\b', re.I), 'harvest'))
ADVISORY = re.compile(r'\b(advisory|advice|guidance|recommend|should i|can i|is it safe|when to|bulletin)\b', re.I)
MARINE = re.compile(r'\b(wave|waves|swell|sea state|significant wave|sea condition|samudra|lehar)\b', re.I)
RIVER = re.compile(r'\b(river discharge|discharge|streamflow|stream flow)\b', re.I)
WARNING = re.compile(r'\b(warning|warnings|alert|alerts|red alert|orange alert|yellow alert|advisory)\b', re.I)
# A warning word that is about a warning, as opposed to the generic word "advisory", which
# the farm vocabulary also uses. Measured need: "What does the Ahmedabad district agromet
# advisory say for cotton?" was planned as a district warning lookup. The strong warning
# words still win, so "any warning for cotton farmers?" keeps the warning route.
WARNING_STRONG = re.compile(r'\b(warnings?|alerts?|red alert|orange alert|yellow alert)\b', re.I)
# A question that asks to compare forecast sources or check another model is the crosscheck
# operation, which exists and carries its own caveat: a best-match source may share GFS
# lineage, so agreement is not independent confirmation. Measured on 15 September 2026, only
# the model planner recognised this shape.
CROSSCHECK = re.compile(r'\b(?:another model|other models?|compare (?:the )?(?:models?|sources?|forecasts?)|'
                        r'model (?:comparison|agreement)|gfs (?:vs|versus)|(?:vs|versus) (?:gfs|ecmwf|icon|best[- ]match)|'
                        r'check another (?:model|source)|do the models agree)\b', re.I)

AGROMET_DOCUMENT = re.compile(r'\b(agromet|agro-met|agricultural advisory|crop advisory|kisan|fasal|krishi|kheti)\b', re.I)
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
    span = re.search(r'\bnext\s+(?:(\d{1,2}|one|two|three|four|five|six|seven|a|an)\s*)?(day|days|week|weeks)\b', lower)
    if offset is None and not clock and not span:
        return '', '', False, None
    if span:
        words = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'a': 1, 'an': 1}
        token = span.group(1) or 'one'
        count = int(token) if token.isdigit() else words.get(token, 1)
        if span.group(2).startswith('week'):
            count *= 7
        count = max(1, min(count, 7))
        first_day = (now.astimezone(IST) + timedelta(days=offset or 0)).date()
        last_day = first_day + timedelta(days=count - 1)
        return (str(first_day) + 'T00:30:00+05:30', str(last_day) + 'T23:30:00+05:30', False,
                'the next ' + str(count) + ' day(s)')
    day = (now.astimezone(IST) + timedelta(days=offset or 0)).date()

    def stamp(hhmm, minute=None, next_day=False):
        hour, minute = int(hhmm[:2]), int(hhmm[3:5])
        target = day + timedelta(days=1) if next_day else day
        return (datetime(target.year, target.month, target.day, hour, minute, tzinfo=IST)).isoformat()

    if clock:
        first = '%02d:%s' % (int(clock[0][0]), clock[0][1])
        if len(clock) > 1:
            last = '%02d:%s' % (int(clock[1][0]), clock[1][1])
        else:
            last = '%02d:%s' % (min(int(clock[0][0]) + 3, 23), clock[0][1])
        return stamp(first), stamp(last), True, basis or 'explicit clock times'
    if not part:
        # A whole day is read as the source's own day, which starts at :30 IST: 00:30 to the
        # next day's 00:30 exclusive. That is 24 complete contained hours, not 23.
        return (stamp('00:30'), stamp('00:30', next_day=True), False, str(basis) + ' whole day')
    start, end = WINDOWS[part]
    label = (str(basis) + ' ' + str(part)) if part else (str(basis) + ' whole day')
    return stamp(start), stamp(end), False, label


def places_of(question):
    """Named places with an optional state or unit word, as written; the gazetteer resolves them."""
    found = []

    def add(name, state='', kind='unknown'):
        sea = SEA_WORDS.search(name or '') if name else None

        name = (name or '').strip(' .,')
        # "Ahmedabad, Gujarat mein" is one place with its state, not the state alone: the
        # qualifier is what disambiguates the name, so it is kept as the state rather than
        # thrown away and resolved as a separate place.
        if ',' in name and not state:
            head, _, tail = name.partition(',')
            head, tail = head.strip(' .,'), tail.strip(' .,')
            if head and tail:
                name, state = head, tail
        if sea:
            # A coast or a sea area is a region, not a settlement. The region word is kept
            # as context and the place is marked so the resolver asks for a point on it.
            stripped=' '.join(SEA_WORDS.sub(' ',name).split()).strip(' .,')
            if stripped:
                name=stripped
                if kind=='unknown':kind='sea_area'
        tokens = name.split()
        while tokens and (tokens[0].lower() in PLACE_NOISE or tokens[0].lower() in PLACE_LEAD_NOISE):
            tokens = tokens[1:]
        name = ' '.join(tokens)
        if not name or len(name) < 3 or name.lower() in PLACE_NOISE:
            return
        if not name or name in [item['name'] for item in found]:
            return
        found.append({'name': name, 'state': state, 'district': '', 'kind': kind})

    for match in PLACE.finditer(question):
        # The captured name stops at the last capitalised word, so a following region
        # word ('the Kerala coast', 'the Arabian Sea') is read from what comes next.
        tail=question[match.end():].lstrip(' .,')
        add(match.group(1), (match.group(2) or '').strip(' .,'),
            kind='sea_area' if SEA_WORDS.match(tail) else 'unknown')
        if len(found) == 2:
            return found
    for match in PLACE_UNIT.finditer(question):
        unit = match.group(2).lower()
        kind = 'district' if unit in {'district', 'tehsil', 'taluk'} else ('state' if unit == 'state' else 'unknown')
        add(match.group(1), kind=kind)
        if len(found) == 2:
            return found
    for match in PLACE_HINGLISH.finditer(question):
        add(match.group(1))
        if len(found) == 2:
            return found
    return found


def variables_of(question):
    variables = []
    for pattern, name in VARIABLE_WORDS:
        if pattern.search(question) and name not in variables:
            variables.append(name)
    return variables


def history_years(question):
    return sorted({int(value) for value in HISTORY.findall(question) if 1800 <= int(value) <= 2200})


CLAUSE_BREAK = re.compile(r'\s*;\s*|\?\s+|\s*,\s*and\s+|\s*,\s*also\s+|\s+and also\s+|\s*,\s*as well as\s+', re.I)


def clauses_of(question):
    """Split a compound question on safe boundaries, keeping every clause a substring.

    A comma alone is not a boundary: "Patna, Bihar" is one place. The boundaries here are
    punctuation and conjunctions that join requests, and each resulting clause is checked to
    be a substring of the question so the task quotes stay verifiable.
    """
    if not isinstance(question, str):
        return []
    parts = [part.strip() for part in CLAUSE_BREAK.split(question) if part and part.strip()]
    return [part for part in parts if part in question]


def rule_request(question, now, history=None):
    """A planner request for a recognised shape, or None to fall through to a model.

    A compound question is planned clause by clause, so "will it rain tomorrow, and is there a
    warning?" becomes two tasks and the answer can compare the two products. When fewer than
    two clauses plan, the single-shape path below decides.
    """
    if not isinstance(question, str) or not question.strip():
        return None
    pieces = clauses_of(question)
    if len(pieces) > 1:
        requests = [single_request(piece, now, history) for piece in pieces]
        requests = [request for request in requests if request]
        if len(requests) >= 2:
            return merge_requests(requests)
    request = single_request(question, now, history)
    if request and 'and' in question.lower() and dropped_conjunction_place(question, request['places']):
        # "Will it rain in Surat and Vadodara?" names two places; the rules planned one. A
        # silent omission is worse than a model call, so the turn falls through instead.
        return None
    return request


def dropped_conjunction_place(question, places):
    """True when a place after a conjunction was named but not planned."""
    planned = {norm(place['name']) for place in (places or [])}
    for match in re.finditer(r'\band\s+((?:[A-Z][\w\u2019.\-]+)(?:\s+[A-Z][\w\u2019.\-]+){0,2})', question):
        candidate = match.group(1).split(',')[0].strip()
        if len(candidate) < 3 or candidate.lower() in PLACE_NOISE:
            continue
        if norm(candidate) not in planned:
            return True
    return False


def merge_requests(requests):
    """One request from several: tasks in order, places deduplicated, windows kept per task."""
    merged = {'language': requests[0]['language'], 'places': [], 'assumptions': [],
              'clarification': '', 'explicit_times': any(r['explicit_times'] for r in requests),
              'tasks': [], 'context_action': 'new', 'changed_fields': ['places', 'time', 'parameters']}
    seen_places, seen_tasks = {}, []
    for request in requests:
        for place in request['places']:
            if place['name'] not in seen_places:
                seen_places[place['name']] = len(merged['places'])
                merged['places'].append(place)
    for request in requests:
        index = {place['name']: position for position, place in enumerate(request['places'])}
        for task in request['tasks']:
            task = dict(task)
            task['place_indices'] = [seen_places[request['places'][position]['name']]
                                     for position in task.get('place_indices', []) if position in index]
            key = (task['kind'], task['operation'], tuple(task['parameters']), tuple(task['place_indices']),
                   task.get('start_local'), task.get('end_local'))
            if key in seen_tasks:
                continue
            seen_tasks.append(key)
            merged['tasks'].append(task)
        for note in request.get('assumptions') or []:
            if note not in merged['assumptions']:
                merged['assumptions'].append(note)
    # A clause that names no place of its own is about the place the question named:
    # "will it rain in Patna tomorrow, and is there any warning?" is one place and two
    # questions, not an unplaced warning request.
    if merged['places']:
        for task in merged['tasks']:
            if not task['place_indices']:
                task['place_indices'] = list(range(len(merged['places'])))
    return merged


def single_request(question, now, history=None):
    language = language_of(question)
    if language is None:
        return None
    if FOLLOW_UP.search(question):
        return None
    question = question.strip().rstrip('?').strip() or question
    mid_conversation = any(isinstance(message, dict) and message.get('context_state') is not None
                           for message in (history or []))
    if mid_conversation and CONTEXT_REFERENCE.search(question):
        # "Compare it with GFS too", "the same morning period": the rules cannot see the
        # context, so they must not claim the turn. A self-contained follow-up that names its
        # own place, day or year is still planned by rules.
        own_place = bool(places_of(question))
        own_time = bool(window_for(question, now)[0]) or bool(history_years(question))
        if not (own_place and own_time):
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
    elif (WARNING.search(question) and not DOCUMENT.search(question)
          and (WARNING_STRONG.search(question) or not (AGROMET_DOCUMENT.search(question)
                                                       or (CROP.search(question) and ADVISORY.search(question))))):
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
    elif (CROP.search(question) or re.search(r'\b(crop|field|farm|kisan|fasal)\b', question, re.I)) and \
            (ADVISORY.search(question) or DOCUMENT.search(question)):
        # A crop with an advisory, a bulletin or a decision is the agriculture shape, and its
        # request carries the crop, the topic and whether the user wants the published advice
        # or an answer about their own field. A crop named in a plain weather question is not
        # an advisory and falls through to the forecast shape below.
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
    elif DOCUMENT.search(question):
        lowered = question.lower()
        family = ''
        if 'agromet' in lowered or 'agri' in lowered or 'krishi' in lowered:
            if 'district' in lowered:
                family = 'district_agromet'
            elif 'state district' in lowered:
                family = 'state_district_bulletin'
            else:
                family = 'state_agromet'
        else:
            for word, name in (('all india weather summary', 'national_bulletin'), ('flash flood', 'flash_flood_national'),
                               ('extended range', 'extended_range'), ('press release', 'press_release'),
                               ('special advisory', 'special_advisory'),
                               ('district bulletin', 'state_district_bulletin'), ('sea area', 'sea_area_bulletin'),
                               ('coastal', 'coastal_bulletin')):
                if word in lowered:
                    family = name
                    break
        scope = ''
        if family == 'district_agromet':
            scope = 'district'
        elif family in {'state_agromet', 'state_district_bulletin'}:
            scope = 'state'
        elif family in {'national_bulletin', 'extended_range', 'press_release', 'erf_marquee',
                        'flash_flood_national', 'flash_flood_sasia'}:
            scope = 'national'
        elif family:
            scope = 'marine'
        request = {'query': quote[:1500], 'family': family, 'scope': scope}
        from .corpus_tools import whole_document_question
        if whole_document_question(question):
            request['whole_document'] = True
        tasks.append(task('document', 'lookup', ['published_document'], corpus_request=request))
    elif OBSERVATION.search(question) and re.search(r'\b[A-Z]{4}\b', question):
        # A four-letter station code in a right-now question is an airport report request: the
        # station's own product answers it, with the airport tool's provenance. Measured on
        # 15 September 2026, "what is being observed at VOBL right now" was planned as a
        # settlement observation and asked for a place.
        code = re.search(r'\b([A-Z]{4})\b', question)
        entry = task('aviation', 'lookup', ['metar'])
        if code.group(1) not in [item['name'].upper() for item in places]:
            places = places + [{'name': code.group(1), 'state': '', 'district': '', 'kind': 'unknown'}]
            entry['place_indices'] = [len(places) - 1]
        tasks.append(entry)
    elif OBSERVATION.search(question):
        tasks.append(task('observation', 'lookup', []))
    else:
        variables = variables_of(question)
        if not variables:
            return None
        operation = 'crosscheck' if CROSSCHECK.search(question) else 'lookup'
        tasks.append(task('forecast', operation, variables))

    assumptions = []
    if basis:
        assumptions.append('Time window read from the question: ' + str(basis) + '.')
    return {'language': language, 'places': places, 'assumptions': assumptions, 'clarification': '',
            'explicit_times': explicit, 'tasks': tasks, 'context_action': 'new',
            'changed_fields': ['places', 'time', 'parameters']}
