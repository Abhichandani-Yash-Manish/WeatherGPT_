"""Whole-document retrieval over the indexed published corpus.

The corpus is a record of what publishers issued, not a picture of what applies now.
Every answer here therefore carries the printed issue date, the retrieval instant and
the measured currency of each document, keeps warning-related text in its own section
with an explicit not-a-current-warning qualification, retires earlier editions of the
same product and region from current retrieval, and never lets a document become an
all-clear, a forecast or personalized advice.

Passage text is retained in full on the passage records; the answer quotes a bounded
excerpt so a reader gets the point before the evidence drawer.
"""
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .document_ingest import ALL_FAMILIES
from .gazetteer import near_names, norm
from .transport import SourceError
from .bulletin_context import qualification_flags

IST = ZoneInfo('Asia/Kolkata')
NATIONAL_OR_MARINE = {'national_bulletin', 'extended_range', 'erf_marquee', 'press_release',
                      'flash_flood_national', 'flash_flood_sasia', 'special_advisory',
                      'sea_area_bulletin', 'coastal_bulletin'}
STATE_FAMILIES = {'state_agromet', 'state_district_bulletin'}
CROP_FAMILIES = {'district_agromet', 'state_agromet'}
WARNING_MARKERS = re.compile(
    r'(?<!no )(?<!not an )(?<!not a )\b(?:weather warnings?|warnings?|alerts?|orange alert|red alert|'
    r'yellow alert|port signal|storm surge|swell surge|heavy rain warning|thunderstorm warning)\b', re.I)
FORECAST_MARKERS = re.compile(r'\b(?:forecast|outlook|likely|expected|probability|synoptic|depression|cyclone)\b', re.I)
HISTORICAL_QUERY = re.compile(r'\b(?:archive|archived|previous|earlier|historical|history|superseded|last (?:week|month|year))\b', re.I)
EXCERPT_LIMIT = 520
STOPWORDS = set(('the a an of for in on at to and or is are was were be been with about what which who how when where '
                 'why does do did say says said latest current today yesterday tomorrow this that these those from by '
                 # Words that carry no topic: measured 15 September 2026, "Is there any warning in the latest
                 # sea area bulletin?" left "there" and "any" as its topic words.
                 'there any all some more most also please me my i you we it its if').split())
INDIC_SCRIPT = re.compile(r'[\u0900-\u0d7f]')
# A question about the document as a whole, not about a topic inside it. This is matched
# deterministically so the behaviour does not depend on the planner's wording that day.
# A question about the document as a whole, not about a topic inside it. The strong markers
# settle it; the weaker "what does X say" phrasing only counts when the question carries no
# topic of its own, so "what does the bulletin say about heavy rainfall" stays a topic search.
WHOLE_DOCUMENT_STRONG = re.compile(
    r"\b(?:main points?|overall|summar(?:y|ise|ize|ising|izing)|synoptic|synopsis|highlights?|key points?|gist|"
    r"whole (?:document|edition|bulletin)|in general|general (?:advice|situation|context))\b", re.I)
WHOLE_DOCUMENT_WEAK = re.compile(
    r"\bwhat does (?:the|this) [^?]{0,60}(?:document|edition|bulletin|release|advisory|guidance) say\b|"
    r"\bwhat (?:is|are) in (?:the|this) [^?]{0,60}(?:document|edition|bulletin|release|advisory|guidance)\b", re.I)
WHOLE_DOCUMENT_GENERIC = set((
    'what does do say says the a an latest national state district regional weather bulletin bulletins advisory '
    'advisories release press document edition summary about in of and for from this that today yesterday issued '
    'published all india according give me tell show').split())


def whole_document_question(question):
    """True when the question asks about the edition itself rather than a topic inside it."""
    if not isinstance(question, str):
        return False
    if WHOLE_DOCUMENT_STRONG.search(question):
        return True
    if not WHOLE_DOCUMENT_WEAK.search(question):
        return False
    leftover = [token for token in re.findall(r'[a-z]{3,}', question.lower()) if token not in WHOLE_DOCUMENT_GENERIC]
    return not leftover


WHOLE_DOCUMENT_QUERY = re.compile(
    r"\b(?:main points?|overall|summar(?:y|ise|ize|ising|izing)|synoptic|synopsis|highlights?|key points?|gist|"
    r"whole (?:document|edition|bulletin)|full (?:document|edition|bulletin)|in general|general (?:advice|situation|context)|"
    r"what does (?:the|this) [^?]{0,60}(?:document|edition|bulletin|release|advisory) say|"
    r"what (?:is|are) in (?:the|this) [^?]{0,60}(?:document|edition|bulletin|release|advisory))\b", re.I)
EDITION_DIFFERENCE_SECTION_LIMIT = 3
EDITION_SIMILARITY_FLOOR = 0.62
# A question that asks what changed needs an answer even when there is nothing to
# compare: "one edition is held" is a fact, and it is not a statement that nothing changed.
CHANGE_QUERY = re.compile(r'\b(?:what (?:changed|is new|has changed)|changed|changes|updated|update|'
                          r'compare|compared|comparison|differs?|difference|differences)\b', re.I)


def query_tokens(query):
    """Content words a passage must actually contain before it is served.

    The index always returns its top k by fused rank, and a dense score is never zero,
    so rank alone cannot say "the document does not mention this". An evidence tool
    prefers an honest no-match to quoting an unrelated passage, so a hit has to share
    at least one exact content word with the question. Semantic-only matches are not
    discarded silently; they are simply not served yet.
    """
    return [token for token in re.findall(r'[a-z0-9\u0900-\u0aff]+', norm(query))
            if token not in STOPWORDS and (len(token) > 2 or token.isdigit())]


DOCUMENT_WORDS = set((
    'document documents bulletin bulletins advisory advisories agromet agro met district districts state states '
    'regional national release releases press news summary summarise summarised highlights issue issued publish '
    'published pdf page pages report reports change changed update updates edition editions say says said mention '
    'mentions regarding crop crops forecast guidance special sea area coastal weather climate '
    'show shows tell give gives list lists read print display open provide provides find').split())


def topic_tokens(query, plan=None, region=None):
    """The words that name a topic, with the place and the document words removed.

    A district edition repeats its own district name in every passage, so a question about
    grapes was answered with the edition's pearl-millet and paddy passages: all eight matches
    shared the word "Nashik" and only one mentioned grapes (measured 15 September 2026). The
    place names of the request and the words every published document shares are removed, and
    what remains is what the question is about.
    """
    place_words = set()
    for place in ((plan or {}).get('places') or []):
        for key in ('name', 'state', 'district'):
            place_words.update(re.findall(r'[a-z0-9\u0900-\u0aff]+', norm(place.get(key) or '')))
    if region:
        place_words.update(re.findall(r'[a-z0-9\u0900-\u0aff]+', norm(region)))
    return [token for token in query_tokens(query) if token not in DOCUMENT_WORDS and token not in place_words]


def lexically_supported(hit, tokens):
    if not tokens:
        return True
    haystack = norm((hit.get('section') or '') + ' ' + (hit.get('text') or ''))
    return any(re.search(r'(?<!\w)' + re.escape(token), haystack) for token in tokens)


def family_spec(family):
    if family in ALL_FAMILIES:
        return ALL_FAMILIES[family]
    raise SourceError('Unknown published document family: ' + str(family))


def family_label(family):
    return family_spec(family).get('label') or family


def directory_states(district):
    """States whose publisher directory lists this district, from the dated snapshot."""
    from .document_ingest import district_states as states_of
    return states_of(district)


def evidence_class(passage):
    """What a passage is, from its family, section and text. A retrieval-time label."""
    section = passage.get('section') or ''
    if WARNING_MARKERS.search(section) or WARNING_MARKERS.search((passage.get('text') or '')[:1200]):
        return 'warning_reference'
    if passage.get('family') in CROP_FAMILIES:
        return 'crop_advisory'
    if FORECAST_MARKERS.search(section) or FORECAST_MARKERS.search((passage.get('text') or '')[:600]):
        return 'forecast_text'
    return 'general_text'


def excerpt(text, limit=EXCERPT_LIMIT):
    text = ' '.join((text or '').split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for stop in ('. ', '; ', ', '):
        position = cut.rfind(stop)
        if position > limit // 2:
            return cut[:position + 1].rstrip() + ' … [excerpt; full passage retained in evidence]'
    return cut.rstrip() + ' … [excerpt; full passage retained in evidence]'


def printed_validity(document):
    """The printed valid-till instant, anchored on the printed issue date, or None."""
    times = document.get('printed_times') or {}
    raw = str(times.get('valid_till') or '').strip()
    match = re.fullmatch(r'(\d{2})(\d{2})\s*(IST|UTC)', raw)
    issue = document.get('issue_date')
    if not match or not issue:
        return None
    try:
        day = datetime.fromisoformat(issue).date()
        # `tzinfo` takes a tzinfo, not an offset. Passing the timedelta raised on every
        # document that states a valid-till time: measured on 15 September 2026, the
        # national flash flood guidance question failed the whole turn with a TypeError.
        zone = timezone(timedelta(hours=5, minutes=30)) if match[3] == 'IST' else timezone.utc
        return datetime(day.year, day.month, day.day, int(match[1]), int(match[2]), tzinfo=zone)
    except ValueError:
        return None


def indexed_regions(index, family):
    """Region names with at least one indexed passage for this family."""
    with index.connection() as db:
        rows = db.execute('SELECT DISTINCT region FROM passages WHERE family=? AND region IS NOT NULL',
                          (family,)).fetchall()
    return sorted({row[0] for row in rows if row[0]})


def region_exists(index, family, region):
    with index.connection() as db:
        row = db.execute('SELECT region FROM passages WHERE family=? AND lower(region)=lower(?) LIMIT 1',
                         (family, region)).fetchone()
    return row[0] if row else None


def district_states(index, region):
    """Document-recorded states, falling back to the dated publisher directory."""
    with index.connection() as db:
        rows = db.execute(
            "SELECT DISTINCT json_extract(d.payload,'$.source_state') FROM passages p JOIN documents d ON p.document_sha=d.sha "
            "WHERE p.family='district_agromet' AND lower(p.region)=lower(?)", (region,)).fetchall()
    states = sorted({row[0] for row in rows if row[0]})
    return states or directory_states(region)


def _same_state(left, right):
    clean = lambda value: norm(str(value or '').replace('State of ', '').replace('state of ', ''))
    return clean(left) == clean(right)


def resolved_names(place, resolved):
    """The English names the gazetteer resolved for this place, most useful first.

    A reader writes the name in their own script and the index stores the publisher's English
    one: measured 15 September 2026, "નાસિક જિલ્લાની કૃષિ સલાહમાં …" extracted નાસિક and the
    corpus answered that no edition was indexed under that name, although the Nashik edition is
    held. The resolved record carries the English name and its administrative parent.
    """
    match = (resolved or {}).get(place.get('name')) or {}
    names = []
    for value in (match.get('name'), match.get('admin2'), match.get('admin1'),
                  (place.get('district') or '').strip(), place.get('name')):
        if not value:
            continue
        clean = str(value).replace('State of ', '').replace('state of ', '').strip()
        if clean and clean not in names:
            names.append(clean)
    return names


def resolve_region(index, plan, family, scope, resolved=None):
    """(stored region, expected state, problem) for the requested filters.

    `problem` is None, 'place', 'district_absent', 'state' or 'state_absent'. It is
    returned instead of guessed: a document must never be attached to a district or
    state the publisher did not print.
    """
    places = plan.get('places') or []
    if family in NATIONAL_OR_MARINE or (not family and scope in {'national', 'regional', 'marine'}):
        return None, None, None
    wants_district = family == 'district_agromet' or scope == 'district'
    wants_state = family in STATE_FAMILIES or (scope == 'state' and not wants_district)
    if wants_district:
        if not places or len(places) > 1:
            return None, None, 'place'
        place = places[0]
        if place['kind'] in {'country', 'state', 'relative'}:
            return None, None, 'place'
        # The publisher's English name is tried before the reader's own spelling, and the name the
        # reader wrote is tried last rather than first.
        stored = None
        for candidate in resolved_names(place, resolved):
            stored = region_exists(index, 'district_agromet', candidate)
            if stored:
                break
        if not stored:
            return None, None, 'district_absent'
        states = district_states(index, stored)
        supplied = (place.get('state') or '').strip()
        if supplied:
            matches = [state for state in states if _same_state(state, supplied)]
            if not matches:
                return None, supplied, 'state_absent'
            return stored, matches[0], None
        if len(states) > 1:
            return None, None, 'state'
        return stored, (states[0] if states else None), None
    if wants_state:
        if not places:
            return None, None, 'place'
        supplied = ''
        for place in places:
            if place['kind'] == 'state' and place['name']:
                supplied = place['name']
                break
        if not supplied:
            # A state named in another script: the resolved record carries the English name.
            for place in places:
                for candidate in resolved_names(place, resolved):
                    if any(region_exists(index, family_name, candidate)
                           for family_name in ('state_agromet', 'state_district_bulletin')):
                        supplied = candidate
                        break
                if supplied:
                    break
        if not supplied:
            # A state named without the word 'state' is still a state when the indexed
            # editions carry that region. Measured on 15 September 2026: "Rajasthan ki
            # agromet advisory me sinchai ke baare me kya likha hai?" asked which state
            # was meant, although Rajasthan is one of the five editions now held.
            for place in places:
                name = place.get('name') or ''
                if name and any(region_exists(index, family_name, name)
                                for family_name in ('state_agromet', 'state_district_bulletin')):
                    supplied = name
                    break
        if not supplied:
            for place in places:
                if place.get('state'):
                    supplied = place['state']
                    break
        if not supplied:
            # A state the publisher's own directory covers, with no edition held here, is
            # an absent edition rather than a missing place. Measured on 15 September 2026:
            # "What changed in the latest state agromet bulletin for Maharashtra?" was
            # answered by asking which state was meant, although Maharashtra is one of the
            # directory's states and simply has no indexed edition.
            from .document_ingest import directory_state_names
            known = {norm(name): name for name in directory_state_names()}
            for place in places:
                name = (place.get('name') or '').strip()
                if name and norm(name) in known:
                    return None, known[norm(name)], 'state_absent'
        if not supplied:
            return None, None, 'place'
        state = supplied.removeprefix('State of ').removeprefix('state of ')
        if family:
            local = region_exists(index, family, state)
        else:
            local = region_exists(index, 'state_agromet', state) or region_exists(index, 'state_district_bulletin', state)
        if not local:
            return None, state, 'state_absent'
        return local, state, None
    return None, None, None


def newest_issue(index, family, region):
    """The newest printed issue date indexed for this product and region, or None.

    Read from the passage index, not from the hit set: a newer edition that does not
    contain the asked words still supersedes the one that does.
    """
    with index.connection() as db:
        row = db.execute(
            "SELECT max(json_extract(payload,'$.issue_date')) FROM passages "
            "WHERE family=? AND ((region IS NULL AND ? IS NULL) OR lower(region)=lower(?))",
            (family, region, region or '')).fetchone()
    return row[0] if row else None


def printed_order(passage):
    """Sort key for one passage: the printed page, then its position on that page."""
    def number(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    return (number(passage.get('physical_page')), number(passage.get('passage_index')))


def edition_passages(index, sha):
    """Every indexed passage of one edition, in printed order."""
    return sorted(index.document_passages(sha), key=printed_order)


def whole_document_hits(index, sha, limit=8):
    """One passage per printed section of one edition, in printed order.

    The point of this mode is the edition's own structure: what it contains, in the order
    it printed it, with the page. Sections are not filtered by keyword, because the
    question is about the document rather than about a topic inside it.
    """
    rows = edition_passages(index, sha)
    seen, selected = set(), []
    for row in rows:
        key = norm(row.get('section') or '(no printed section heading)')
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
    hits = []
    for rank, row in enumerate(selected[:limit]):
        hits.append({**row, 'retrieval': {'rank': rank + 1, 'match_basis': 'whole_document_sections',
                                          'scores_are_confidence': False}})
    return hits, {'passages_indexed': len(rows), 'sections_indexed': len(seen),
                  'passages_served': len(hits), 'sections_served': len({norm(row.get('section') or '') for row in selected[:limit]})}


def edition_comparison(index, family, region, limit=EDITION_DIFFERENCE_SECTION_LIMIT):
    """What the newest edition dropped or changed against the one before it.

    Named, never judged: the newer edition is not treated as correct and the older one is
    not treated as superseded for reading. Only sections that exist in both editions are
    compared for wording; a section the newer edition does not carry at all is reported as
    absent rather than as withdrawn. When only one edition is indexed the result says so,
    because an absent comparison is not evidence that nothing changed.
    """
    import difflib
    clause = 'family=? AND ((region IS NULL AND ? IS NULL) OR lower(region)=lower(?))'
    with index.connection() as db:
        dates = [row[0] for row in db.execute(
            'SELECT DISTINCT json_extract(payload,\'$.issue_date\') FROM passages WHERE ' + clause +
            ' ORDER BY 1 DESC LIMIT 2', (family, region, region or '')) if row[0]]
    comparison = {'items': [], 'editions_indexed': len(dates),
                  'newest_issue': dates[0] if dates else None,
                  'previous_issue': dates[1] if len(dates) > 1 else None}
    if len(dates) < 2:
        return comparison
    newer_date, older_date = dates[0], dates[1]

    def sections(date):
        with index.connection() as db:
            shas = [row[0] for row in db.execute(
                'SELECT DISTINCT document_sha FROM passages WHERE ' + clause +
                ' AND json_extract(payload,\'$.issue_date\')=?', (family, region, region or '', date))]
        out = {}
        for sha in shas:
            try:
                rows = edition_passages(index, sha)
            except (SourceError, ValueError, OSError):
                continue
            for row in rows:
                key = norm(row.get('section') or '(no printed section heading)')
                if key and key not in out:
                    out[key] = {'section': row.get('section') or '(no printed section heading)',
                                'page': row.get('physical_page'),
                                'text': ' '.join(str(row.get('text') or '').split()),
                                'issue_date': date}
        return out

    newer, older = sections(newer_date), sections(older_date)
    if not newer or not older:
        comparison['items_unreadable'] = True
        return comparison
    absent, changed = [], []
    for key, item in older.items():
        if key not in newer:
            absent.append({'kind': 'section_absent_from_newer', 'section': item['section'],
                           'nearer': {'issue_date': newer_date, 'page': None, 'excerpt': None},
                           'earlier': {'issue_date': older_date, 'page': item['page'], 'excerpt': excerpt(item['text'], 240)}})
            continue
        ratio = difflib.SequenceMatcher(None, item['text'][:4000].lower(), newer[key]['text'][:4000].lower()).ratio()
        if ratio < EDITION_SIMILARITY_FLOOR:
            changed.append({'kind': 'section_text_differs', 'section': item['section'],
                            'nearer': {'issue_date': newer_date, 'page': newer[key]['page'], 'excerpt': excerpt(newer[key]['text'], 240)},
                            'earlier': {'issue_date': older_date, 'page': item['page'], 'excerpt': excerpt(item['text'], 240)},
                            'similarity': round(ratio, 2)})
    changed.sort(key=lambda item: item['similarity'])
    items = (absent + changed)[:limit]
    for item in items:
        item['note'] = ('Both editions are retained and none is ranked: the workspace does not decide which edition is '
                        'current or correct, and a section missing from a later edition is not a withdrawal.')
    comparison['items'] = items
    return comparison


def translated_query(query):
    """The question in English, for retrieval only, or None when no key is configured.

    A publisher prints in one language and the reader may ask in another: measured 15 September
    2026, "भारी बारिश के बारे में राष्ट्रीय मौसम बुलेटिन क्या कहता है?" shared no exact word with
    the English bulletin, so only semantic matches could be served. The translation is used to
    *find* passages. It never becomes an answer: the passages served are the source's own words,
    the basis is disclosed, and the turn is partial because a generative step now sits between the
    question and the index.

    The source language is read from the script, which is coarser than the language: Assamese is
    written in the Bengali script and is read as Bengali here. That is recorded on the result
    rather than presented as a measured language identification.
    """
    from . import speech
    from .languages import sarvam_code
    from .rule_planner import language_of
    if not speech.configured():
        return None
    try:
        code = sarvam_code(language_of(query))
        # The same question asked again is the common case; the rendering of the masked question
        # is cached locally, and a hit is recorded on the coverage record.
        rendered, meta = speech.translate(query, 'en', code, cache=True)
    except (SourceError, ValueError, OSError):
        # A refusal, a timeout or an unconfigured service is a state of the retrieval, not an
        # error the reader should see: the disclosed semantic-only basis still applies.
        return None
    if not rendered or not rendered.strip():
        return None
    return {'text': rendered.strip(), 'source_language': code,
            'service': (meta or {}).get('service', 'language service'),
            'model': (meta or {}).get('model', 'not stated'),
            'script_read_as': language_of(query)}


def execute_corpus(engine, result, plan, task, resolved=None):
    result.update(passages=[], document_evidence=[], pending_slots=[])
    request = task.get('corpus_request') or {}
    query = (request.get('query') or task.get('request_quote') or result.get('question') or '').strip()
    family = request.get('family') or ''
    scope = request.get('scope') or ''
    if not query:
        result.update(status='needs_clarification', answer='Which published document or topic should I look up?')
        return result
    index = engine.workspace.document_index()
    if not resolved and getattr(engine, 'gazetteer', None) is not None:
        # No place was resolved for this task, so the tool resolves the names it was given: a
        # document question does not need coordinates, which is why nothing had grounded them.
        # Measured 15 September 2026: "નાસિક જિલ્લાની કૃષિ સલાહમાં …" answered that no edition was
        # indexed under નાસિક, although the gazetteer resolves that name to the Nashik edition held
        # here. The choice is disclosed on the answer like any other reading of a place.
        from .gazetteer import preferred_match
        resolved = {}
        for place in plan.get('places') or []:
            name = (place.get('name') or '').strip()
            if not name or name in resolved:
                continue
            chosen, why = preferred_match(engine.gazetteer.search(name, place.get('state') or '',
                                                                  place.get('district') or ''))
            if not chosen:
                continue
            resolved[name] = chosen
            note = ('Place read as ' + str(chosen.get('label') or chosen.get('name')) +
                    ' for the published document' + ((' — ' + str(why)) if why else '') + '.')
            if note not in result.setdefault('notes', []):
                result['notes'].append(note)
    region, expected_state, problem = resolve_region(index, plan, family, scope, resolved)
    if problem == 'place':
        if family == 'district_agromet' or scope == 'district':
            reason = 'A source district is needed for this document family'
            answer = 'Which source district should I check? The indexed district agromet editions are keyed by the publisher\'s district name.'
        else:
            reason = 'A state is needed for this document family'
            answer = 'Which state should I check? This document family is published per state.'
        result['pending_slots'] = [{'field': 'place', 'reason': reason}]
        result.update(status='needs_clarification', answer=answer)
        return result
    if problem == 'district_absent':
        # The name is kept as the reader wrote it and the close spellings are offered as a
        # hint. Nothing is substituted: 571 district editions are indexed, and a near name
        # is a reason to ask rather than a reason to answer for a district nobody named.
        held = indexed_regions(index, 'district_agromet')
        places = plan.get('places') or []
        asked = ((places[0].get('district') or places[0].get('name')) if places else '') or ''
        close = near_names(held, asked)
        answer = ('No district agromet edition is indexed under that name. The corpus is keyed by the publisher\'s own '
                  'district names; no edition for another district was substituted. ' +
                  (str(len(held)) + ' district names are indexed; the closest to that request ' +
                   ('are ' if len(close) > 1 else 'is ') + ', '.join(close) + ' — name one and I will read its edition.'
                   if close else str(len(held)) + ' district names are indexed and none is close to that request.'))
        result.update(status='unavailable', answer=answer)
        return result
    if problem == 'state':
        result['pending_slots'] = [{'field': 'place', 'reason': 'More than one state publishes a district with this name'}]
        result.update(status='needs_clarification',
                      answer='That district name is published by more than one state. Which state should I check?')
        return result
    if problem == 'state_absent':
        held = indexed_regions(index, family) if family else sorted(set(indexed_regions(index, 'state_agromet')) |
                                                                    set(indexed_regions(index, 'state_district_bulletin')))
        answer = ('No indexed document is published for ' + str(expected_state) + ' in this family. ' +
                  ('The state editions held here are ' + ', '.join(held) + '. ' if held else '') +
                  'A same-named district or document from another state was not substituted.')
        result.update(status='unavailable', answer=answer)
        return result
    # Judged from the document request's own query (the planner copies the user's words
    # into it) or an explicit planner flag, never from a topic query that merely happens
    # to sit inside a wider question.
    change_question = bool(CHANGE_QUERY.search(query))
    whole_document = (bool(request.get('whole_document')) or whole_document_question(query)
                      # "What changed in this bulletin?" is a question about the edition, and a
                      # keyword search for the word "changed" would find nothing in it.
                      or (change_question and bool(family)))
    whole = None
    if whole_document and not family:
        # Several products could be meant. Naming them, with their newest printed issue
        # date, is more useful than guessing one and answering from the wrong document.
        listing = []
        for name, meta in index.document_families().items():
            if meta.get('scope') not in ('national', 'marine'):
                continue
            try:
                newest = newest_issue(index, name, None)
            except (SourceError, ValueError):
                newest = None
            listing.append((newest or '', name))
        listing.sort(reverse=True)
        if listing:
            result['pending_slots'] = [{'field': 'product', 'reason': 'More than one published product could be summarised'}]
            result['retrieval_coverage'] = {'candidates': len(listing), 'returned': 0, 'match_basis': 'whole_document_needs_product',
                                            'filters': {'family': None, 'scope': scope or None, 'region': region},
                                            'scope': 'No document was opened; the question names no product.',
                                            'scores_are_confidence': False}
            result.update(status='needs_clarification',
                          answer=('More than one published product could be meant. Name one and I will read its sections in printed order: '
                                  + '; '.join(family_label(name) + (', newest printed issue ' + date if date else ', issue date not stated')
                                              for date, name in listing[:6]) + '.'))
            return result
    if whole_document and family:
        try:
            head = index.document_head(family, region)
        except (SourceError, ValueError, OSError):
            head = None
        if head:
            try:
                section_hits, totals = whole_document_hits(index, head['sha'])
            except (SourceError, ValueError, OSError) as error:
                result.update(status='unavailable', answer='Published document retrieval is unavailable: ' + str(error))
                return result
            if section_hits:
                hits = section_hits
                method = {'mode': 'whole_document_sections', 'candidates': totals['passages_indexed'],
                          'edited': head['sha'], 'scores_are_confidence': False}
                whole = {'edition_sha256': head['sha'], 'passages_indexed': totals['passages_indexed'],
                         'sections_indexed': totals['sections_indexed'], 'passages_served': totals['passages_served'],
                         'sections_served': totals['sections_served'],
                         'scope': ('One passage per printed section, in printed order. That is a bounded reading of the edition, '
                                   'not the whole text; every passage is retained and the saved document opens from each passage.')}
    if not whole:
        try:
            hits, method = index.search_passages(query, family=family or None, scope=scope or None, region=region, limit=10)
        except (SourceError, ValueError) as error:
            result.update(status='unavailable', answer='Published document retrieval is unavailable: ' + str(error))
            return result
    # A question asked in one language is answered from documents printed in another. The
    # translation is used to find passages, never to state anything: what is served is still the
    # source's own words, with the basis and the translated query recorded.
    translation = translated_query(query) if (not whole and INDIC_SCRIPT.search(query)) else None
    lexical_query = translation['text'] if translation else query
    tokens = query_tokens(lexical_query)
    supported = [hit for hit in hits if lexically_supported(hit, tokens)]
    if translation and not supported:
        # The fused top-k was ranked on the original wording. Search again on the translation.
        try:
            again, more_method = index.search_passages(lexical_query, family=family or None, scope=scope or None,
                                                       region=region, limit=10)
        except (SourceError, ValueError):
            again = []
        supported = [hit for hit in again if lexically_supported(hit, tokens)]
        if supported:
            hits, method = again, more_method
    lexical_support = len(supported)
    match_basis = 'translated_query_lexical_overlap' if (translation and supported) else 'lexical_overlap'
    topics = []
    topic_matched = True
    if supported and not whole:
        topics = topic_tokens(lexical_query, plan, region)
        on_topic = [hit for hit in supported if lexically_supported(hit, topics)] if topics else []
        if on_topic:
            supported = on_topic
            match_basis = 'translated_query_lexical_overlap' if translation else 'lexical_overlap_topic'
        elif topics:
            # Shared wording is all that matched. Served as the top fused matches with the
            # missing topic word stated, rather than as an answer to the question.
            topic_matched = False
            match_basis = ('translated_query_without_the_topic_word' if translation
                           else 'lexical_overlap_without_the_topic_word')
    if whole:
        # The question is about the edition, so shared wording is not the retrieval rule.
        supported = hits
        lexical_support = 0
        match_basis = 'whole_document_sections'
    elif not supported and hits and INDIC_SCRIPT.search(query):
        # A question in an Indic script shares no exact words with English documents.
        # The multilingual embedding can still rank them, so the top semantic matches
        # are served with the lack of wording support stated, never as a verified match.
        supported = sorted(hits, key=lambda hit: -((hit.get('retrieval') or {}).get('semantic_score') or 0))[:3]
        match_basis = 'semantic_only_indic_script_disclosed'
    hits = supported

    documents, views, order, filtered_out, unverified = {}, {}, [], [], []
    for hit in hits:
        sha = hit['document_sha256']
        if sha in filtered_out:
            continue
        if sha not in documents:
            try:
                document = index.passage_document(sha)
            except (SourceError, ValueError, OSError) as error:
                unverified.append({'document_sha256': sha, 'reason': str(error)})
                filtered_out.append(sha)
                continue
            state = document.get('source_state') or document.get('state')
            if hit.get('family') == 'district_agromet' and not state:
                states = directory_states(hit.get('region') or '')
                state = states[0] if len(states) == 1 else None
            if hit.get('family') == 'district_agromet' and expected_state and state and not _same_state(state, expected_state):
                filtered_out.append(sha)
                continue
            documents[sha] = document
            views[sha] = {'family': hit.get('family'), 'scope': hit.get('scope'), 'region': hit.get('region'),
                          'source_id': hit.get('source_id') or document.get('source_id'),
                          'family_label': family_label(hit.get('family')),
                          'state': state, 'issue_date': document.get('issue_date') or hit.get('issue_date'),
                          'age_days': document.get('age_days'), 'currency': document.get('currency'),
                          'extraction_status': document.get('extraction_status') or 'family_extraction_reviewed_in_intake',
                          'printed_times': document.get('printed_times') or {},
                          'pages': document.get('pages'), 'is_shared_edition': document.get('is_shared_edition'),
                          'selected_for_regions': document.get('selected_for_regions') or []}
            order.append(sha)
        if sha in views:
            documents[sha].setdefault('_hits', []).append(hit)

    kept_order = [sha for sha in order if documents[sha].get('_hits')]
    if not kept_order:
        result['retrieval_coverage'] = {'candidates': method.get('candidates', 0), 'returned': 0,
                                        'lexically_supported': 0, 'lexical_overlap_required': True,
                                        'match_basis': 'none',
                                        'filters': {'family': family or None, 'scope': scope or None, 'region': region},
                                        'scope': 'Whole-document passage index; no passage from another product, district or state was substituted.',
                                        'scores_are_confidence': False}
        result.update(status='unavailable',
                      answer=('No indexed passage matches that request' +
                              (' in ' + ' / '.join(part for part in [family_label(family) if family else None, region, scope] if part) if (family or region or scope) else '') +
                              '. The corpus holds what publishers issued; it is not a complete archive and nothing was substituted.'))
        return result

    historical = bool(HISTORICAL_QUERY.search(query))
    superseded = set()
    for sha in kept_order:
        view = views[sha]
        if view.get('issue_date'):
            newest = newest_issue(index, view['family'], view.get('region'))
            if newest and view['issue_date'] < newest:
                superseded.add(sha)
    if historical:
        kept, retired = kept_order, []
    else:
        kept = [sha for sha in kept_order if sha not in superseded]
        retired = [sha for sha in kept_order if sha in superseded]
    if not kept:
        # Every matching passage belongs to an edition a newer printed edition has
        # superseded. Current retrieval must not serve it as though it were current.
        result['retrieval_coverage'] = {'candidates': method.get('candidates', 0), 'returned': 0,
                                        'filters': {'family': family or None, 'scope': scope or None, 'region': region},
                                        'superseded_retired': len(retired),
                                        'scope': 'Whole-document passage index; earlier editions are retired from current retrieval.',
                                        'scores_are_confidence': False}
        result.update(status='unavailable',
                      answer=('The only matching passage belongs to an earlier edition that a newer printed edition of the same '
                              'product and region has superseded. The newer edition does not contain this match, and the earlier '
                              'one is not served as current. Ask for the historical edition explicitly to read it.'))
        return result

    comparison = {'items': [], 'editions_indexed': 0, 'newest_issue': None, 'previous_issue': None}
    if kept and not historical:
        first = views[kept[0]]
        try:
            comparison = edition_comparison(index, first['family'], first.get('region'))
        except (SourceError, ValueError, OSError):
            comparison = {'items': [], 'editions_indexed': 0, 'newest_issue': None, 'previous_issue': None}
    differences = comparison['items']
    if historical:
        comparison['state'] = 'not_attempted_historical_question'
    elif differences:
        comparison['state'] = 'compared'
    elif comparison['editions_indexed'] > 1:
        comparison['state'] = 'no_compared_section_differs'
    elif comparison['editions_indexed'] == 1:
        comparison['state'] = 'single_edition_indexed'
    else:
        comparison['state'] = 'no_edition_indexed'

    classes, warning_hits, crop_hits, conflict_items = {}, [], [], []
    for sha in kept:
        for hit in documents[sha]['_hits']:
            kind = evidence_class(hit)
            classes[kind] = classes.get(kind, 0) + 1
            if kind == 'warning_reference':
                warning_hits.append(hit)
            if kind == 'crop_advisory':
                crop_hits.append(hit)
            conflict_items.append({'id': hit['id'], 'text': hit['text']})

    now = engine.workspace.clock()
    currency_unknown, expired, reading_order, heads = [], [], [], {}
    for sha in kept:
        view = views[sha]
        key = (view['family'], view.get('region'))
        if key not in heads:
            try:
                heads[key] = index.document_head(view['family'], view.get('region'))
            except (SourceError, ValueError, OSError):
                heads[key] = None
        if not view.get('issue_date'):
            currency_unknown.append(sha)
        valid = printed_validity(view)
        if valid and valid < now:
            expired.append((sha, valid))
        if 'reading_order_unverified' in str(view.get('extraction_status') or ''):
            reading_order.append(sha)

    conflicts = qualification_flags(conflict_items, [])
    citations, evidence, passages = [], [], []
    for sha in kept:
        view = views[sha]
        head = heads.get((view['family'], view.get('region'))) or {}
        citation_id = 'doc-' + sha
        spec = family_spec(view['family'])
        citations.append({'id': citation_id, 'source_id': view.get('source_id'),
                          'provider': (spec.get('issuer') or ['published source'])[0].title(),
                          'product': view.get('family_label'),
                          'response_sha256': sha, 'retrieved_at_utc': head.get('checked_at'),
                          'issue_date': view.get('issue_date'), 'family': view.get('family'),
                          'scope': view.get('scope'), 'region': view.get('region'),
                          'source_locator': 'document ' + sha[:12] + ', index ' + str(sha[:12]),
                          'physical_page': None, 'local_document_path': '/api/documents/' + sha,
                          'is_evidence': True})
        evidence.append({'family': view['family'], 'family_label': view.get('family_label'),
                         'scope': view.get('scope'), 'region': view.get('region'), 'state': view.get('state'),
                         'issue_date': view.get('issue_date'), 'currency': view.get('currency'),
                         'age_days': view.get('age_days'), 'sha256': sha, 'pages': view.get('pages'),
                         'source_id': view.get('source_id'), 'extraction_status': view.get('extraction_status'),
                         'printed_times': view.get('printed_times'), 'is_shared_edition': view.get('is_shared_edition'),
                         'selected_for_regions': view.get('selected_for_regions')})
        for hit in documents[sha]['_hits']:
            kind = evidence_class(hit)
            passages.append({**hit, 'citation_ids': [citation_id], 'evidence_kind': kind,
                             'applicability': ('reference_only; not a current applicable warning' if kind == 'warning_reference'
                                               else 'published_record; not a forecast, observation or personalized advice'),
                             'issue_date': view.get('issue_date'), 'currency': view.get('currency')})

    def document_headline(sha, head):
        view = views[sha]
        pieces = [view.get('family_label')]
        where = view.get('region') or ('national' if view.get('scope') == 'national' else view.get('scope'))
        if view.get('state') and view.get('family') == 'district_agromet':
            where = str(view['state']) + ' / ' + str(view.get('region'))
        pieces.append(str(where))
        pieces.append('document ' + sha[:12])
        pieces.append('printed issue ' + (view.get('issue_date') or 'not stated'))
        age = view.get('age_days')
        if age is None and view.get('issue_date'):
            try:
                age = (now.astimezone(IST).date() - datetime.fromisoformat(view['issue_date']).date()).days
            except ValueError:
                age = None
        if age is not None:
            pieces.append('on the printed issue date' if age == 0 else str(age) + ' day(s) after the printed issue')
        pieces.append('retrieved ' + (head.get('checked_at') or 'instant not recorded'))
        if view.get('is_shared_edition'):
            pieces.append('shared edition covering ' + ', '.join(view.get('selected_for_regions') or []))
        return ' · '.join(pieces)

    parts = ['Indexed published documents, not forecasts or current warnings:' if len(kept) > 1 else
             'Indexed published document:']
    if whole:
        parts.append(str(whole['passages_served']) + ' of ' + str(whole['passages_indexed']) +
                     ' indexed passages of this edition are quoted below, one per printed section in printed order (' +
                     str(whole['sections_indexed']) + ' section(s) indexed). That is a bounded reading of the edition, not its full text.')
    if differences:
        parts.append('Editions compared for ' + str(views[kept[0]].get('family_label')) + ' ' +
                     str(views[kept[0]].get('region') or 'national') + ':')
        for item in differences:
            if item['kind'] == 'section_absent_from_newer':
                parts.append('· ' + str(item['section']) + ' is printed in the ' + str(item['earlier']['issue_date']) +
                             ' edition (page ' + str(item['earlier']['page']) + ') and is not printed in the ' +
                             str(item['nearer']['issue_date']) + ' edition.')
            else:
                parts.append('· ' + str(item['section']) + ' differs materially between the ' +
                             str(item['earlier']['issue_date']) + ' edition (page ' + str(item['earlier']['page']) + ') and the ' +
                             str(item['nearer']['issue_date']) + ' edition (page ' + str(item['nearer']['page']) + ').')
        parts.append('Both editions are retained and none is ranked: the workspace does not decide which edition is current or '
                     'correct, and a section a later edition does not print is not a withdrawal.')
    for sha in kept:
        head = heads.get((views[sha]['family'], views[sha].get('region'))) or {}
        parts.append(document_headline(sha, head) + '.')
        for hit in documents[sha]['_hits']:
            if evidence_class(hit) == 'warning_reference':
                continue
            section = (' · ' + hit['section']) if hit.get('section') else ''
            parts.append('· page ' + str(hit.get('physical_page')) + section + ': “' + excerpt(hit['text']) + '”')
    if warning_hits:
        parts.append('Warning-related text published in these documents (reference only):')
        for hit in warning_hits:
            sha = hit['document_sha256']
            section = (' · ' + hit['section']) if hit.get('section') else ''
            parts.append('· ' + str(views[sha].get('region') or 'national') + ', page ' + str(hit.get('physical_page')) +
                         section + ': “' + excerpt(hit['text']) + '”')
        parts.append('That text records what a document published. It is not a current applicable official warning, not an '
                     'all-clear, and it grants no clearance. Current applicability is answered only by the official warning check, '
                     'which is a separate evidence source.')
    if crop_hits:
        parts.append('Crop guidance is district-level published advice. It has not been validated against an individual field, '
                     'current crop stage or the weather at that field, and it is not a personal go/no-go decision.')
    if conflicts:
        parts.append('Opposing wording was found for ' + ', '.join(flag['activity'] for flag in conflicts) +
                     '. Their conditions, dates and scopes may differ; the passages are retained and no conclusion has been made.')
    if CHANGE_QUERY.search(query) and comparison.get('state') == 'single_edition_indexed':
        family_name = str(views[kept[0]].get('family_label'))
        where = str(views[kept[0]].get('region') or 'national')
        parts.append('Only one edition of ' + family_name + ' for ' + where + ' is indexed here' +
                     (', printed ' + str(comparison['newest_issue']) if comparison.get('newest_issue') else '') +
                     ', so no earlier edition can be compared. That is not a statement that nothing changed: it is the '
                     'absence of a second indexed edition.')
    if currency_unknown:
        parts.append(str(len(currency_unknown)) + ' document(s) do not state a printed issue date, so their currency is unknown; '
                     'retrieval success is not an issue date.')
    for sha, valid in expired:
        parts.append('The printed validity of ' + str(views[sha].get('family_label')) + ' ended ' + valid.isoformat() +
                     '; it is shown as the published record, not as current guidance.')
    if retired:
        parts.append(str(len(retired)) + ' earlier-edition passage(s) matched but were retired from current retrieval because a newer '
                     'printed edition of the same product and region is indexed. Ask for the historical edition explicitly to see them.')
    if reading_order:
        parts.append('Extraction reading order is unverified for these documents; tables and headings can be split.')
    if match_basis == 'semantic_only_indic_script_disclosed':
        parts.append('The question is written in a script these English source documents do not share, so no exact word from '
                     'it appears in the retrieved passages. These are the top semantic matches, not a verified wording match.')
    if translation and str(match_basis).startswith('translated_query'):
        parts.append('The question was written in ' + str(translation['source_language']) + ' and was translated to English '
                     'for retrieval only (' + str(translation['service']) + ', ' + str(translation['model']) + '): the wording searched for was “' +
                     excerpt(translation['text'], 200) + '”. Every passage below is the source\'s own text, matched on that translation and not on '
                     'the original wording, so the reading is partial and the translation is not evidence.')
    if match_basis in {'lexical_overlap_without_the_topic_word', 'translated_query_without_the_topic_word'}:
        parts.append('No indexed passage of this product and region contains ' + ', '.join(topics) +
                     '. What is shown shares the other words of the request only, so it does not answer it and no passage was '
                     'substituted from another product or region.')
    parts.append('These are original source excerpts. They are not a forecast, an observation, an official warning or personalized advice.')
    result['answer'] = '\n\n'.join(parts)
    result['citations'] = citations
    result['whole_document'] = whole
    result['edition_differences'] = differences
    result['edition_comparison'] = comparison
    result['document_evidence'] = evidence
    result['passages'] = passages
    result['retrieval_coverage'] = {'mode': method.get('mode'), 'candidates': method.get('candidates', 0),
                                    'returned': len(passages), 'edition_differences': len(differences),
                                    'edition_comparison': comparison.get('state'),
                                    'editions_indexed_for_this_product': comparison.get('editions_indexed'),
                                    'whole_document': bool(whole),
                                    'lexically_supported': lexical_support, 'lexical_overlap_required': True,
                                    'match_basis': match_basis, 'topic_tokens': topics, 'topic_matched': topic_matched,
                                    'query_translation': ({**translation, 'used_for_retrieval': bool(translation and supported)}
                                                          if translation else None),
                                    'filters': {'family': family or None, 'scope': scope or None, 'region': region},
                                    'evidence_classes': classes,
                                    'superseded_retired': len(retired),
                                    'currency_unknown': len(currency_unknown),
                                    'expired_printed_validity': len(expired),
                                    'unverified_excluded': len(unverified),
                                    'scope': 'Whole-document passage index over indexed published documents; not a completeness '
                                             'claim for any publisher and not an archive.',
                                    'scores_are_confidence': False}
    result['trace']['tools'].append({'name': 'published_document_retrieval', 'method': method.get('mode'),
                                     'families': sorted({views[sha]['family'] for sha in kept}),
                                     'documents': kept, 'filters': {'family': family or None, 'scope': scope or None, 'region': region},
                                     'scores_are_confidence': False})
    # A served passage that is warning-classified does not make the reading incomplete: it is
    # served with its reference-only label and the answer says so. Partial means the request
    # itself was reduced: an unstated issue date, expired printed validity, a retired edition,
    # a filtered document, a disclosed weaker match, or opposing wording that was found.
    weaker_match = match_basis in {'semantic_only_indic_script_disclosed', 'lexical_overlap_without_the_topic_word',
                                   'translated_query_lexical_overlap', 'translated_query_without_the_topic_word'}
    partial = bool(currency_unknown or expired or retired or conflicts or filtered_out or weaker_match)
    result['status'] = 'partial' if partial else 'answered'
    return result
