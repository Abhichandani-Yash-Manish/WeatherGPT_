"""Official warning evidence for a place, without inventing an all-clear.

Two official products are reported side by side and never merged into a verdict:

* IMD district-level warning guidance (source S15). Its Day_1..Day_5 fields are
  read as hazard codes, not as severity levels, and its windows are derived from
  the bulletin date.
* The IMD-labelled CAP relay (source S06), reported as a source assessment.

Neither establishes an all-clear. A CAP lifecycle result never authorises
dissemination, and a green district day is not a statement that nothing will
happen. A bulletin whose published days have all passed is reported as stale and
contributes no current facts.

A warning question is about a district, and the planner says so. Unlike a point
forecast, a district name is answerable here, because the official product is
itself district-level. A name that matches more than one place is asked about
rather than guessed: attaching an official warning to the wrong district is the
one failure this product must never make.
"""
import re
from datetime import timedelta

from . import district_warnings as dw
from .evidence_transport import evidence_store
from .foundation import Foundation
from .transport import SourceError, parsed, stamp

# The warning evidence store, relative to the ingestion root: the same convention corpus and
# forecast citations use, named here because these two products are fetched through it.
WARNING_EVIDENCE_STORE = 'warning-evidence'

# A nationwide sweep can match hundreds of districts. The answer lists and cites at most this
# many, and says so, rather than trimming in silence.
FACT_CAP = 40

CAP_LIMITS = ('Geographic applicability of the CAP relay to this place is not established here, its origin is not '
              'authenticated, and its completeness is unverified. A reachable feed and an empty eligible set are '
              'both not an all-clear.')


def stored_evidence(meta_row):
    """Where the bytes of a fetched warning response are kept, when the store recorded a blob.

    A response hash with no way back to the stored bytes is not a walkable chain: measured
    17 September 2026, the S15 and S06 citations carried response_sha256 while every forecast
    citation also carried the relative path of the blob it was read from.
    """
    blob = (meta_row or {}).get('blob')
    return {'raw_relative_path': blob, 'raw_store': WARNING_EVIDENCE_STORE} if blob else {}


def warning_citations(meta, snapshot_meta, has_districts):
    """The two product citations, each carrying the store path of the bytes it was read from."""
    citations = [{'id': 'cap-feed', 'source_id': 'S06',
                  'provider': 'IMD-labelled CAP relay; origin authentication unverified',
                  'product': 'Retrieved CAP feed state', 'url': meta['url'],
                  'response_sha256': meta['sha256'], 'retrieved_at_utc': meta['retrieved_at_utc'],
                  **stored_evidence(meta)}]
    if has_districts and snapshot_meta:
        citations.append({'id': 'district-warning', 'source_id': 'S15', 'provider': 'India Meteorological Department',
                          'product': 'District-wise warning product (GeoServer district_warnings_india)',
                          'url': snapshot_meta.get('url'), 'response_sha256': snapshot_meta.get('sha256'),
                          'retrieved_at_utc': snapshot_meta.get('retrieved_at_utc'),
                          **stored_evidence(snapshot_meta)})
    return citations


def normalise(value):
    """Letters only, upper case: the source writes AHMADABAD where GeoNames writes Ahmadabad."""
    return re.sub(r'[^A-Z]', '', str(value or '').upper())


def _point_for(place, resolved, coordinates):
    """The resolution already recorded for this place, else an explicit pin."""
    entry = (resolved or {}).get(place.get('name'))
    if isinstance(entry, dict) and isinstance(entry.get('coordinates'), dict):
        return entry['coordinates'], (entry.get('label') or place.get('name'))
    if isinstance(coordinates, dict) and coordinates.get('latitude') is not None:
        return coordinates, place.get('name')
    return None, place.get('name')


def _gazetteer_ladder(engine, place):
    """Loosen the filters rather than the place: an unused hint must not hide a match.

    Returns (match, matches_seen, ambiguous_candidates).
    """
    name = place.get('name') or ''
    attempts = [(place.get('state') or '', place.get('district') or ''),
                (place.get('state') or '', ''),
                ('', '')]
    seen_filters = set()
    for state, district in attempts:
        if (state, district) in seen_filters:
            continue
        seen_filters.add((state, district))
        matches = engine.gazetteer.search(name, state, district)
        confident = [match for match in matches if match.get('coordinates')]
        if len(confident) == 1 and confident[0].get('match_type') != 'approximate_name_requires_confirmation':
            return confident[0], len(matches), None
        if len(confident) > 1:
            # A user who wrote "Patna, Bihar" narrowed the name already. When one
            # administrative seat outranks the villages sharing the name, attach the warning to
            # that seat and disclose the reading rather than asking again; a genuinely
            # same-order ambiguity still asks.
            from .gazetteer import preferred_match, rank_matches
            chosen, why = preferred_match(confident)
            if chosen is not None:
                others = [item['label'] for item in rank_matches(confident) if item['id'] != chosen['id']][:4]
                chosen['accepted_because'] = why
                chosen['alternatives'] = others
                return chosen, len(matches), None
            return None, len(matches), confident[:20]
    return None, 0, None


def _cap_assessment(foundation):
    packet = foundation.cap()
    records = packet['records']
    meta = packet['provenance']
    latest = max(records, key=lambda message: parsed(message['sent'])) if records else None
    return {'assessment': packet['lifecycle_assessment'], 'coverage': packet['coverage'],
            'delivery': meta['delivery'], 'latest_sent': latest['sent'] if latest else None,
            'records': records, 'meta': meta}


# The four IMD colours, read from the reader's own words. A colour is never guessed: an unnamed
# colour means "any hazard", which is every colour but green.
COLOUR_WORDS = {'red': 'red', 'orange': 'orange', 'amber': 'orange', 'yellow': 'yellow', 'green': 'green'}


def requested_colours(text):
    """The colours a sweep question names, or None for 'any hazard'."""
    words = re.findall(r'[a-z]+', str(text or '').lower())
    named = [COLOUR_WORDS[w] for w in words if w in COLOUR_WORDS]
    return sorted(set(named)) or None


def national_sweep(engine, result, plan, task, records, snapshot_meta, cap, colours,
                   state=None, directory=None):
    """Which districts carry a warning, across the whole country, with no place to narrow to.

    Added 20 September 2026. "Which districts are under a red warning today?" named no place, so the
    per-place path had nothing to resolve and the turn fell through to a CAP-relay refusal that spoke
    about "this place" - a place the reader never mentioned - and never once mentioned the district
    warning store it was holding. The store is the right source for this question: it is district-level
    and national by construction.

    Three outcomes, kept distinct because they mean different things:
      * districts match -> answered, with a fact per matching district;
      * the bulletin is current and nothing matches -> answered, a real "none today";
      * every stored day has passed -> stale, naming the edition and its date. Never an all-clear.
    """
    now = engine.workspace.clock()
    wanted = colours or ['red', 'orange', 'yellow']
    # Scoped to one state when the reader named one. The warning product publishes no state of its
    # own, so attribution is by name against the reviewed district directory and is PARTIAL - the
    # districts it cannot place are counted and reported, never quietly dropped.
    unattributed = 0
    total_records = len(records)
    if state and directory is not None:
        records, unattributed = directory.attribute(records, state)
    where = ' in ' + state if state else ''
    matched, lapsed_matched, current_districts, editions = [], [], 0, {}
    for record in records:
        try:
            rows, issued = dw.day_rows(record, now)
        except SourceError:
            continue
        editions[issued.date().isoformat()] = editions.get(issued.date().isoformat(), 0) + 1
        current = [row for row in rows if not row['is_past']]
        if current:
            current_districts += 1
            hits = [row for row in current if row['colour'] in wanted]
            if hits:
                matched.append({'record': record, 'rows': hits, 'issued': issued, 'published': rows})
        else:
            hits = [row for row in rows if row['colour'] in wanted]
            if hits:
                lapsed_matched.append({'record': record, 'rows': hits, 'issued': issued})

    colour_phrase = ' or '.join(wanted) if colours else 'any hazard colour (red, orange or yellow)'
    newest = max(editions) if editions else None
    result['facts'] = list(result.get('facts') or [])
    # One fact per matching district. The list is capped so a nationwide yellow day cannot bury the
    # answer, and the cap is stated rather than applied quietly.
    shown = matched[:FACT_CAP]
    for entry in shown:
        result['facts'] += dw.facts(entry['record'], entry['rows'], entry['issued'], 'district-warning',
                                    entry['record'].get('district_label'))

    def names(entries, limit=FACT_CAP):
        labels = [str(e['record'].get('district_label')) + ' (' + '; '.join(
            sorted({row['colour'] for row in e['rows'] if row['colour']})) + ')' for e in entries[:limit]]
        tail = len(entries) - len(labels)
        return ', '.join(labels) + (', and ' + str(tail) + ' more' if tail > 0 else '')

    chunks = []
    if matched:
        chunks.append(str(len(matched)) + ' district' + ('s' if len(matched) != 1 else '') + where +
                      ' carry ' + colour_phrase + ' in the current IMD district bulletin: ' + names(matched) + '.')
        if len(matched) > FACT_CAP:
            chunks.append('The list above and the facts below are capped at ' + str(FACT_CAP) +
                          ' districts; the full matched set is in this turn\'s warning evidence.')
        result['status'] = 'answered'
    elif current_districts:
        chunks.append('No district' + where + ' carries ' + colour_phrase + ' in the current IMD district '
                      'bulletin. ' + str(current_districts) + ' district' +
                      ('s have' if current_districts != 1 else ' has') + ' a day that has not yet passed, and '
                      'none of them is at ' + colour_phrase + '. A green or absent colour is not a statement '
                      'that nothing will happen.')
        result['status'] = 'answered'
    else:
        chunks.append('No district' + where + ' can be reported at ' + colour_phrase + ' today, because no '
                      'stored district bulletin still has a day in the future. The newest stored edition is '
                      'dated ' + (newest or 'an unreadable date') + ' and covers ' + str(len(records)) +
                      ' districts' + where + '; every day it publishes has already passed. This is a gap in the '
                      'published bulletin, not an all-clear.')
        if lapsed_matched:
            chunks.append('For the record, in that lapsed edition ' + str(len(lapsed_matched)) + ' district' +
                          ('s' if len(lapsed_matched) != 1 else '') + ' carried ' + colour_phrase + ' on a day that '
                          'has now passed: ' + names(lapsed_matched) + '. That is a past bulletin state, not a '
                          'warning in force now, and it carries no current facts.')
        result['status'] = 'stale'

    if state:
        from .states import coverage_note
        note = coverage_note(unattributed, total_records)
        if note:
            chunks.append(note)
    message_count = len(cap['records'])
    assessment = cap['assessment']
    chunks.append('CAP relay assessment: ' + str(message_count) + ' retrieved messages, ' +
                  str(assessment['eligible_by_lifecycle']) + ' pass the time/status/reference checks' +
                  ('; the newest was sent ' + cap['latest_sent'] + '.' if cap['latest_sent'] else '.') +
                  # No place was named, so the standing CAP caveat cannot say "this place".
                  ' ' + CAP_LIMITS.replace('to this place', 'to any particular district'))
    result['citations'] = warning_citations(cap['meta'], snapshot_meta, bool(matched))
    result['warning_evidence'] = {
        'assessment': assessment, 'coverage': cap['coverage'], 'delivery': cap['meta']['delivery'],
        'latest_sent': cap['latest_sent'], 'requested_places': [], 'records': cap['records'],
        'national_sweep': {'colours': wanted, 'colours_named_by_reader': bool(colours),
                           'state': state, 'districts_in_bulletin': total_records,
                           'districts_not_attributed_to_any_state': unattributed,
                           'districts_in_store': len(records), 'districts_with_a_current_day': current_districts,
                           'matched_districts': [{'district': e['record'].get('district_label'),
                                                  'issued_at_utc': e['issued'].isoformat(),
                                                  'days': e['rows']} for e in matched],
                           'lapsed_matched_districts': [{'district': e['record'].get('district_label'),
                                                         'issued_at_utc': e['issued'].isoformat(),
                                                         'days': e['rows']} for e in lapsed_matched],
                           'editions': editions},
        'district_warnings': [{'place': e['record'].get('district_label'),
                               'district': e['record'].get('district_label'),
                               'issued_at_utc': e['issued'].isoformat(), 'days': e['rows']} for e in shown],
        'stale_districts': [], 'points_outside_districts': [], 'places_without_a_point': [],
        'cap_applicability': []}
    result['trace']['tools'].append({'name': 'official_district_warning_national_sweep',
                                     'colours': wanted, 'districts_in_store': len(records),
                                     'districts_with_a_current_day': current_districts,
                                     'matched_districts': len(matched),
                                     'lapsed_matched_districts': len(lapsed_matched),
                                     'cap_messages': message_count,
                                     'cap_lifecycle_eligible': assessment['eligible_by_lifecycle'],
                                     'origin_authentication': 'unverified',
                                     'official_applicability_verified': bool(matched),
                                     'dissemination_eligible': False})
    result['answer'] = ' '.join(chunks)
    # The sweep's first sentence IS the answer, so it owns the lead. Left to the generic composer,
    # a thirteen-district sweep opened "Kerala: today the forecast value is yellow IMD district
    # warning colour" - one district's colour presented as the state's, and a warning colour called
    # a forecast. lead_sentence() keeps a lead that is already composed, and task_dispatch does not
    # prepend one that already appears in the answer.
    result['lead'] = chunks[0] if chunks else ''
    result['expires_at_utc'] = stamp(now + timedelta(minutes=15))
    result['notes'] += [('Every district the official product attributes to ' + state + ' was read.')
                        if state else
                        'No district or state was named, so every district in the official product was read.',
                        'IMD district warning guidance concerns land districts and is not a flood warning, a cyclone '
                        'warning, an all-clear or a CAP alert.',
                        'CAP lifecycle eligibility never authorises dissemination; warning material is reported as '
                        'official product state, not as an instruction.']
    return result


def execute_warning(engine, result, plan, task, resolved=None, coordinates=None):
    chosen, ambiguous, unresolved, outside, stale, sea_areas = [], None, [], [], [], []
    records, snapshot_meta = [], None
    sweep = not plan['places']
    # A state is not a settlement. Before any gazetteer search, ask whether the named place IS one of
    # the thirty-six states: "warnings in Kerala" was being answered with four hamlets spelled like it.
    state_scope = None
    try:
        from .states import StateDirectory
        directory = StateDirectory(engine.workspace.service.geography_database)
        for place in plan['places']:
            resolved_state = directory.resolve(place.get('state') or place.get('name'))
            if resolved_state:
                state_scope = resolved_state
                break
    except (ValueError, OSError, AttributeError):
        directory, state_scope = None, None
    if state_scope:
        sweep = True
    try:
        with evidence_store(engine.workspace, 'imd_cap',
                            engine.workspace.service.raw_root.parent / 'warning-evidence') as store:
            foundation = Foundation.__new__(Foundation)
            foundation.store = store
            cap = _cap_assessment(foundation)
            # With no place to narrow to, the question is about the country, and the district product
            # is national by construction. Read it rather than falling through to a CAP-only refusal.
            if plan['places'] or sweep:
                snapshot = foundation.warning_snapshot()
                snapshot_meta = snapshot.get('provenance') or {}
                records = snapshot['records']
            for place in plan['places']:
                point, label = _point_for(place, resolved, coordinates)
                if point:
                    chosen.append({'place': label, 'point': point})
                    continue
                if place.get('kind') == 'sea_area':
                    # A coast is not a settlement: it has no district guidance and no single
                    # point. Measured on 15 September 2026, 'the Kerala coast' searched for a village
                    # and offered places called Kerla in Rajasthan.
                    sea_areas.append(place.get('name') or 'that coast')
                    continue
                match, seen, candidates = _gazetteer_ladder(engine, place)
                result['trace']['tools'].append({'name': 'gazetteer_search', 'query': place, 'matches': seen})
                if candidates:
                    ambiguous = candidates
                    break
                if match is not None:
                    if match.get('accepted_because'):
                        result['notes'].append('Place read as ' + (match.get('label') or label) + ' — ' +
                                               match['accepted_because'] + '.' +
                                               (' Other places share this name: ' + '; '.join(match.get('alternatives') or []) +
                                                '. Say which one you meant to switch.' if match.get('alternatives') else ''))
                    chosen.append({'place': match.get('label') or label, 'point': match['coordinates']})
                    continue
                # No settlement answer: the official district label may still carry the name.
                target = normalise(place.get('name'))
                exact = [record for record in records if normalise(record.get('district_label')) == target]
                if len(exact) == 1:
                    chosen.append({'place': exact[0].get('district_label'), 'record': exact[0]})
                    continue
                # Reviewed-alias fallback: a publisher spelling the crosswalk
                # knows, disclosed — never a guess, and ambiguity stays unresolved.
                from .district_aliases import CROSSWALK_VERSION, resolve as resolve_alias
                canonical, why = resolve_alias(place.get('name'), place.get('state'))
                if canonical is not None:
                    aliased = [record for record in records
                               if normalise(record.get('district_label')) == normalise(canonical)]
                    if len(aliased) == 1:
                        result['notes'].append(
                            'Place read as ' + str(aliased[0].get('district_label')) + ' via the reviewed '
                            'district-alias table (' + str(why.get('basis')) + ', confidence '
                            + str(why.get('confidence')) + ', ' + CROSSWALK_VERSION + ').')
                        chosen.append({'place': aliased[0].get('district_label'), 'record': aliased[0]})
                        continue
                unresolved.append(place.get('name') or 'your location')
    except (ValueError, OSError) as exc:
        result.update(status='unavailable',
                      answer='Current official warning evidence could not be verified: ' + str(exc) +
                             '. This is an evidence gap, not an all-clear.')
        return result

    if sweep:
        return national_sweep(engine, result, plan, task, records, snapshot_meta, cap,
                              requested_colours(str(task.get('request_quote') or '') + ' ' +
                                                str(plan.get('requested_outcome') or '')),
                              state=state_scope, directory=directory if state_scope else None)

    if sea_areas and not chosen:
        result.update(status='needs_clarification',
                      answer=('A coast or a sea area is not a district, so the official district warning '
                              'product has nothing to match for '+', '.join(sea_areas)+'. Name a district or a port '
                              'on that coast (for example Kochi) and I will read the published guidance for it. '
                              'The sea-area and coastal bulletins are registered but not connected to this '
                              'conversation.'),
                      follow_up='A district or a port on that coast')
        return result
    if sea_areas:
        result['notes'].append('A sea area was named ('+', '.join(sea_areas)+') and is not a district: no '
                               'district guidance was read for it.')
    if ambiguous:
        result.update(status='needs_selection', choices=ambiguous,
                      answer='More than one place matches this warning question. Confirm the intended place first, so '
                             'an official warning is never attached to the wrong district.',
                      follow_up='Choose a place, or add its district and state.')
        return result

    districts = []
    for item in chosen:
        record = item.get('record')
        if record is None:
            hits = dw.select(records, item['point']['latitude'], item['point']['longitude'])
            if not hits:
                outside.append(item['place'])
                continue
            record = hits[0]
        try:
            rows, issued = dw.day_rows(record, engine.workspace.clock())
        except SourceError:
            continue
        current = [row for row in rows if not row['is_past']]
        if not current:
            stale.append((item['place'], record, issued))
        else:
            districts.append({'place': item['place'], 'record': record, 'rows': current, 'issued': issued,
                              'published': rows, 'now': engine.workspace.clock()})

    meta = cap['meta']
    assessment = cap['assessment']
    citations = warning_citations(meta, snapshot_meta, bool(districts))
    facts = []
    for entry in districts:
        facts += dw.facts(entry['record'], entry['rows'], entry['issued'], 'district-warning', entry['place'])
    result['facts'] = list(result.get('facts') or []) + facts
    # CAP geometric applicability per resolved point: additive assessment only.
    # It never changes facts, lifecycle, or fingerprints — held stays held, and
    # dissemination_eligible stays False. A failure here holds, never breaks.
    cap_applicability = []
    try:
        from .cap_geo import assess_records
        for item in chosen:
            point = item.get('point')
            if not isinstance(point, dict):
                continue
            assessed = assess_records(cap['records'], point.get('latitude'), point.get('longitude'))
            cap_applicability.append({
                'place': item.get('place'),
                'assessed_records': len(assessed),
                'applicable_records': sum(1 for row in assessed if row['verdict'] == 'applicable'),
                'held_records': sum(1 for row in assessed if row['verdict'] == 'held'),
                'records': assessed})
    except Exception:
        cap_applicability = [{'place': item.get('place') if isinstance(item, dict) else None,
                              'assessed_records': 0, 'applicable_records': 0, 'held_records': 0,
                              'records': [], 'verdict': 'held',
                              'reason': 'CAP applicability could not be assessed.'}
                             for item in chosen]

    message_count = len(cap['records'])
    result['warning_evidence'] = {
        'assessment': assessment, 'coverage': cap['coverage'], 'delivery': meta['delivery'],
        'latest_sent': cap['latest_sent'], 'requested_places': plan['places'], 'records': cap['records'],
        'district_warnings': [{'place': entry['place'], 'district': entry['record'].get('district_label'),
                               'issued_at_utc': entry['issued'].isoformat(), 'days': entry['rows']}
                              for entry in districts],
        'stale_districts': [{'place': label, 'district': record.get('district_label'),
                             'issued_at_utc': issued.isoformat()} for label, record, issued in stale],
        'points_outside_districts': outside, 'places_without_a_point': unresolved,
        'cap_applicability': cap_applicability}
    result['citations'] = citations
    result['trace']['tools'].append({'name': 'official_district_warning', 'districts': len(districts),
                                     'stale_districts': len(stale), 'outside_districts': len(outside),
                                     'places_without_a_point': len(unresolved),
                                     'cap_messages': message_count,
                                     'cap_lifecycle_eligible': assessment['eligible_by_lifecycle'],
                                     'origin_authentication': 'unverified',
                                     'official_applicability_verified': bool(districts),
                                     'dissemination_eligible': False})

    cap_line = ('CAP relay assessment: ' + str(message_count) + ' retrieved messages, ' +
                str(assessment['eligible_by_lifecycle']) + ' pass the time/status/reference checks' +
                ('; the newest was sent ' + cap['latest_sent'] + '.' if cap['latest_sent'] else '.') + ' ' + CAP_LIMITS)
    # The statement is made over every day the bulletin publishes, not only the days a
    # question returned, and the read instant is carried so the edition's age is stated.
    chunks = [dw.summary(entry['record'], entry['rows'], entry['issued'], published=entry.get('published'),
                         now=entry.get('now')) for entry in districts]
    for label, record, issued in stale:
        chunks.append('The stored IMD district warning for ' + label + ' is dated ' + issued.strftime('%d %b %Y') +
                      ' and every day it publishes has already passed, so it carries no current facts. Ask again for a '
                      'current bulletin; a lapsed bulletin is neither a current warning nor an all-clear.')
    for label in outside:
        chunks.append('The resolved point for ' + label + ' does not fall inside any district polygon of the IMD '
                      'district warning product, so no district warning applies there. That product covers land '
                      'districts only; ask for a nearby town for district guidance.')
    if districts:
        # Measured 17 September 2026: the plan window was IST ("2026-09-17T00:00:00+05:30") while the
        # day row was UTC ("2026-09-16T18:30:00+00:00"). The two are the same instant, and nothing said
        # so, which makes two correct readings look like a contradiction.
        chunks.append('The plan window is written as IST calendar days and each day row as UTC instants; '
                      'each pair names the same interval, and neither is a second validity.')
    if chunks:
        chunks.append(cap_line)
    else:
        chunks.append('I cannot confirm a current official warning for ' +
                      (', '.join(unresolved) if unresolved else 'this place') + '. The retrieved CAP relay contains ' +
                      str(message_count) + ' messages; ' + str(assessment['eligible_by_lifecycle']) +
                      ' pass the time/status/reference checks' +
                      ('; its newest message was sent ' + cap['latest_sent'] + '.' if cap['latest_sent'] else '.') +
                      ' ' + CAP_LIMITS)
    if meta['delivery'] == 'stale_cache':
        chunks.append('The CAP source refresh also failed, so that part of this answer is a cached feed assessment.')

    if districts:
        result['status'] = 'answered' if not (unresolved or outside or stale) else 'partial'
    elif stale:
        result['status'] = 'stale'
    else:
        result['status'] = 'unavailable'
    result['answer'] = ' '.join(chunks)
    result['expires_at_utc'] = stamp(engine.workspace.clock() + timedelta(minutes=15))
    result['notes'] += ['IMD district warning guidance concerns land districts and is not a flood warning, a cyclone '
                        'warning, an all-clear or a CAP alert.',
                        'CAP lifecycle eligibility never authorises dissemination; warning material is reported as '
                        'official product state, not as an instruction.',
                        'Day windows are derived from the bulletin date and the IMD day selector, not from a validity '
                        'field published per day.']
    if snapshot_meta is not None and records:
        result['notes'] += ['The district warning layer was read as a complete collection with no truncation; its '
                            'geometry is not an LGD village crosswalk.']
    return result
