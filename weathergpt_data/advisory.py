"""The advisory brief: published crop advice for a district, with the forecast as context.

A farmer question has two halves that must not be mixed up. The first is what the published
district agromet bulletin advises for a crop and a growth stage - source text, quoted with its
page, its printed issue date and its retrieval instant. The second is what the model forecast
says for the field window - model output, labelled as such.

This module composes both into one artefact and keeps them apart inside it. It does not
diagnose a crop, does not decide an operation, does not invent or adjust a dose, and does not
claim a field-level measurement. Where the published text states its own conditions ("if
irrigation facilities are available", "considering soil moisture"), those clauses are quoted as
the source's conditions - never as the state of the reader's field.
"""
import hashlib
import json
import re

from .gazetteer import norm

MAX_PASSAGES = 4
QUOTE_LIMIT = 420
NON_PRESCRIPTION = [
    'This is published district-level advice for the printed issue date shown, not a prescription for a field.',
    'The workspace does not diagnose crop symptoms, does not choose a pesticide or a dose, and does not decide whether an operation is safe.',
    'Soil moisture, the actual growth stage in the field and local conditions are not measured here; the source states its own conditions, which a local advisory must check.',
    'Any product, dose or quantity printed by the source belongs to the source label and the local advisory, not to this brief.',
    'The forecast is model output for a grid cell, not an observation of the field, and weather can change.',
]
CONDITION = re.compile(r'\b(?:if|when|where|considering|in case|provided)\b', re.I)
CROP_ROW = re.compile(r'\b(cotton|wheat|rice|paddy|maize|groundnut|sugarcane|soybean|bajra|jowar|mustard|onion|potato|'
                      r'tomato|mango|banana|pulses|gram|turmeric|chilli|grapes|cumin|castor|sesame)\b', re.I)
STAGE = re.compile(r'\b(sowing|sowing time|nursery|transplant|vegetative|squaring|flowering|boll formation|pod formation|'
                   r'tillering|booting|grain filling|maturity|harvest|harvesting|germination|seedling)\b', re.I)


def resolve_indexed_name(index, family, scope, wanted):
    """The publisher's own name for a requested region, from the indexed editions.

    The catalogue and the publisher do not always spell a district the same way (Ahmedabad and
    Ahmadabad are the same place). Resolution is disclosed in the brief, is bounded to the
    editions actually held, and returns (None, reason) rather than guessing when nothing matches
    closely enough.
    """
    import difflib
    with index.connection() as db:
        rows = [row[0] for row in db.execute(
            'SELECT DISTINCT region FROM passages WHERE family=? AND scope=? AND region IS NOT NULL',
            (family, scope)).fetchall() if row[0]]
    if not rows:
        return None, 'no edition of this family is indexed'
    target = norm(wanted)
    scored = sorted(((difflib.SequenceMatcher(None, norm(name), target).ratio(), name) for name in rows), reverse=True)
    best_score, best = scored[0]
    if best_score >= 0.90:
        return best, 'the indexed name is this close to the request'
    if best_score >= 0.80 and (len(scored) == 1 or scored[1][0] < best_score - 0.05):
        return best, 'one indexed name is closest to the request and clearly ahead of the next'
    return None, 'no indexed name is close enough to the request'


def clean(text, limit=QUOTE_LIMIT):
    body = ' '.join(str(text or '').split())
    return body if len(body) <= limit else body[:limit].rstrip() + ' …'


def crop_and_stage(text):
    """The crop and growth stage the passage names, read from its own words."""
    crop = CROP_ROW.search(text or '')
    stage = STAGE.search(text or '')
    return (crop.group(1).lower() if crop else None, stage.group(1).lower() if stage else None)


def conditions_of(text):
    """The source's own conditional clauses, quoted, bounded to three."""
    clauses = []
    for sentence in re.split(r'(?<=[.;])\s+', ' '.join(str(text or '').split())):
        if CONDITION.search(sentence) and 20 <= len(sentence) <= 220:
            clauses.append(sentence.strip())
        if len(clauses) == 3:
            break
    return clauses


def forecast_context(facts, window=None):
    """The forecast half of the brief: the retrieved series' own bounds, labelled as model output.

    No aggregation is applied here: the first and last values of the retrieved series and the
    number of samples are reported, because a total or a mean computed here would be the
    workspace inventing a summary the source did not publish for this brief.
    """
    rows = []
    for fact in facts or []:
        rows.append({'parameter': fact.get('parameter'), 'first_value': fact.get('value'), 'unit': fact.get('unit'),
                     'place': fact.get('place'), 'series_start': fact.get('start'), 'series_end': fact.get('end'),
                     'samples': fact.get('samples'), 'source_id': fact.get('source_id'), 'label': fact.get('label'),
                     'last_value': fact.get('last_value')})
    if not rows:
        return {'status': 'not_retrieved',
                'note': 'no forecast was retrieved for this brief, so no model values are shown'}
    return {'status': 'retrieved', 'window': window, 'values': rows,
            'note': ('model forecast for a grid cell, not an observation of the field, and not an instruction; the '
                     'first and last values of the retrieved series are shown with the number of samples, and no '
                     'summary is computed here; units are the source units as returned')}


def compose(index, request, forecast=None, encoder=None):
    """Compose the brief from the indexed published advice and the forecast facts.

    request: region (district), state, crop, stage, topic, mode, window, point.
    encoder: passed to the index for offline checks; production leaves it to the index.
    """
    crop = (request.get('crop') or '').strip().lower()
    stage = (request.get('stage') or '').strip().lower()
    topic = (request.get('topic') or 'general').strip().lower()
    region = (request.get('region') or '').strip()
    state = (request.get('state') or '').strip()
    query = ' '.join(part for part in (crop, stage, '' if topic == 'general' else topic, 'advisory') if part)
    notes = []
    attempts = []
    hits, scope_used, family_used, where_used = [], None, None, None
    if region:
        publisher_region, why = resolve_indexed_name(index, 'district_agromet', 'district', region)
        if publisher_region:
            if norm(publisher_region) != norm(region):
                notes.append('The district was read as "' + publisher_region + '" - the name this published edition uses - '
                             'from the requested "' + region + '" (' + why + ').')
            attempts.append(('district_agromet', 'district', publisher_region))
        else:
            notes.append('No indexed district edition matches "' + region + '"; nothing from another district was substituted.')
    if state:
        publisher_state, why = resolve_indexed_name(index, 'state_agromet', 'state', state)
        if publisher_state:
            if norm(publisher_state) != norm(state):
                notes.append('The state was read as "' + publisher_state + '" from the requested "' + state + '".')
            attempts.append(('state_agromet', 'state', publisher_state))
    for family, scope, where in attempts:
        kwargs = {'family': family, 'scope': scope, 'region': where, 'limit': 6}
        if encoder is not None:
            kwargs['encoder'] = encoder
        try:
            found, method = index.search_passages(query, **kwargs)
        except (TypeError, ValueError):
            found, method = [], {}
        if found:
            hits, scope_used, family_used, where_used = found, scope, family, where
            break
    if not hits:
        return {'status': 'not_available',
                'why': ('no indexed published advisory matches this crop and district'
                        + (' or its state' if state else '')),
                'query': query, 'attempts': ['%s/%s' % (family, where) for family, _, where in attempts],
                'not_established': NON_PRESCRIPTION,
                'forecast': forecast_context(forecast)}
    kept, named_other, crops_seen = [], [], set()
    terms = [value for value in (crop, stage, '' if topic == 'general' else topic) if value]
    for hit in hits:
        text = hit.get('text') or ''
        seen_crop, _seen_stage = crop_and_stage(text)
        if seen_crop:
            crops_seen.add(seen_crop)
        if crop and seen_crop and seen_crop != crop:
            named_other.append(seen_crop)
            continue
        # A passage that names no crop must at least carry one of the request's own terms;
        # front matter and weather tables matched lexically and belong in no crop brief.
        lowered = text.lower()
        if not seen_crop and terms and not any(term in lowered for term in terms):
            continue
        kept.append(hit)
    if crop and not kept:
        return {'status': 'not_available',
                'why': ('the indexed edition for ' + str(where_used or region or state or 'this area') +
                        ' does not name ' + crop + ' in the passages retrieved for this request'),
                'crops_named_by_the_edition': sorted(crops_seen),
                'query': query, 'attempts': ['%s/%s' % (family, where) for family, _, where in attempts],
                'not_established': NON_PRESCRIPTION,
                'forecast': forecast_context(forecast)}
    if named_other:
        notes.append('Passages that name another crop (' + ', '.join(sorted(set(named_other))) +
                     ') were left out of this brief rather than served for ' + crop + '.')
    if crop and not any(passage_crop == crop for passage_crop in [crop_and_stage(hit.get('text'))[0] for hit in kept]):
        notes.append('The edition does not name ' + crop + ' in the passages retrieved for this request; what follows is '
                     'the district edition\'s own general advice, quoted as printed.')
    hits = kept
    passages = []
    for hit in hits:
        crop_seen, stage_seen = crop_and_stage(hit.get('text'))
        passages.append({'source_id': hit.get('source_id'), 'family': hit.get('family'), 'region': hit.get('region'),
                         'page': hit.get('physical_page'), 'issue_date': hit.get('issue_date'), 'section': hit.get('section'),
                         'crop': crop_seen, 'growth_stage': stage_seen, 'quote': clean(hit.get('text')),
                         'conditions': conditions_of(hit.get('text')), 'source_locator': hit.get('source_locator'),
                         'document_sha256_prefix': str(hit.get('document_sha256') or '')[:12]})
        if len(passages) == MAX_PASSAGES:
            break
    if scope_used == 'state':
        notes.append('No district edition matched for ' + (region or 'this district') +
                     '; the advice below is the state edition for ' + str(where_used) +
                     ', which is the published product for this area. Nothing from another district was substituted.')
    if topic != 'general':
        notes.append('The passages were selected for the topic "' + topic + '"; the source text is quoted as printed.')
    brief = {
        'status': 'ok',
        'request': {'crop': crop or None, 'growth_stage': stage or None, 'topic': topic,
                    'mode': (request.get('mode') or 'source_lookup'), 'region': region or None, 'state': state or None,
                    'point': request.get('point'), 'window': request.get('window')},
        'published_advice': {'family': family_used, 'scope': scope_used, 'region': where_used,
                             'passages': passages, 'matched': len(hits)},
        'forecast': forecast_context(forecast, request.get('window')),
        'conditions_named_by_the_source': [clause for passage in passages for clause in passage['conditions']][:6],
        'not_established': list(NON_PRESCRIPTION) + notes,
        'sources': sorted({passage['source_id'] for passage in passages if passage['source_id']}),
    }
    if (request.get('mode') or '') == 'decision_support':
        brief['decision_support'] = {
            'what_the_source_conditions_are': brief['conditions_named_by_the_source'] or
                ['the quoted passages state no explicit condition, so the brief lists none'],
            'what_is_missing_for_a_decision': ['soil moisture at the field', 'the growth stage actually in the field',
                                               'the local advisory for the block', 'any product label or dose decision'],
            'statement': ('The workspace will not turn published advice into a go/no-go decision: the conditions above are '
                          'the conditions the source states, the missing items are not measured here, and a local advisory decides.'),
        }
    canonical = json.dumps(brief, sort_keys=True, ensure_ascii=False).encode()
    brief['brief_id'] = hashlib.sha256(canonical).hexdigest()
    return brief


def markdown(brief):
    """The shareable artefact: published advice, then forecast context, then the limits."""
    if brief.get('status') != 'ok':
        lines = ['# Advisory brief: not available', '', '- ' + str(brief.get('why') or 'no brief was composed'), '']
        if brief.get('query'):
            lines.append('- Searched for: ' + str(brief['query']))
        if brief.get('attempts'):
            lines.append('- Editions searched: ' + ', '.join(brief['attempts']))
        lines += ['', '## What is not established here', ''] + ['- ' + item for item in brief.get('not_established') or []]
        return chr(10).join(lines) + chr(10)
    request = brief['request']
    advice = brief['published_advice']
    lines = ['# Advisory brief - ' + str(request.get('crop') or 'crop not named') +
             ((' · ' + str(request.get('growth_stage'))) if request.get('growth_stage') else '') +
             ' · ' + str(advice.get('region') or 'region not stated'), '',
             '- Brief identity: sha256 ' + str(brief.get('brief_id'))[:16] + ' (the content hash of this brief)',
             '- Edition searched: ' + str(advice.get('family')) + ' (' + str(advice.get('scope')) + ') for ' + str(advice.get('region')),
             '- Requested mode: ' + str(request.get('mode')), '',
             '## Published advice, quoted', '']
    for passage in advice.get('passages') or []:
        lines.append('- ' + str(passage.get('source_id')) + ' · page ' + str(passage.get('page')) + ' · printed issue ' +
                     str(passage.get('issue_date')) + ((' · ' + str(passage.get('crop'))) if passage.get('crop') else '') +
                     ((' · ' + str(passage.get('growth_stage'))) if passage.get('growth_stage') else '') + ':')
        lines.append('  > ' + str(passage.get('quote')))
        for clause in passage.get('conditions') or []:
            lines.append('  - source condition: ' + clause)
    forecast = brief.get('forecast') or {}
    lines += ['', '## Forecast context', '']
    if forecast.get('status') == 'retrieved':
        for value in forecast.get('values') or []:
            first = value.get('first_value', value.get('value'))
            last = value.get('last_value')
            samples = value.get('samples')
            lines.append('- ' + str(value.get('label') or value.get('parameter')) + ': first ' + str(first) + ' ' +
                         str(value.get('unit') or '') +
                         ('' if last in (None, first) else ', last ' + str(last) + ' ' + str(value.get('unit') or '')) +
                         ('' if samples in (None, '') else ' across ' + str(samples) + ' sample(s)') +
                         ' · ' + str(value.get('series_start', value.get('start'))) + ' to ' +
                         str(value.get('series_end', value.get('end'))) + ' · ' + str(value.get('source_id')))
    else:
        lines.append('- ' + str(forecast.get('note') or 'no forecast context was retrieved'))
    if brief.get('decision_support'):
        lines += ['', '## Decision support: what a decision still needs', '',
                  '- ' + str(brief['decision_support'].get('statement'))]
        for item in brief['decision_support'].get('what_is_missing_for_a_decision') or []:
            lines.append('- missing here: ' + item)
    lines += ['', '## What is not established here', ''] + ['- ' + item for item in brief.get('not_established') or []]
    lines += ['', '_Composed by a local prototype from the sources named above. Published advice is quoted, not rewritten; '
              'the forecast is model output; neither is a prescription._', '']
    return chr(10).join(lines)
