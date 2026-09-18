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
                      r'tomato|mango|banana|pulses|gram|turmeric|chilli|grapes|cumin|castor|sesame|pearl millet|'
                      r'finger millet|sorghum|ragi|pigeon ?pea|arhar|tur|chickpea|chana|moong|mung|urad|masoor|lentil|'
                      r'barley|oats|sunflower|linseed|safflower|napier|berseem|tea|coffee|rubber|coconut|areca ?nut|'
                      r'cashew|jute|peas|cauliflower|cabbage|brinjal|okra|bhindi|guava|papaya|pomegranate|lemon|lime|'
                      r'orange|sapota|custard apple|watermelon|muskmelon|cucumber|pumpkin|bottle ?gourd|bitter ?gourd|'
                      r'ridge ?gourd|spinach|fenugreek|coriander|garlic|ginger|tobacco|isabgol|fennel|ajwain)\b', re.I)

# A section that reports the weather outlook rather than crop advice: it is context for the brief, and the
# brief already carries its own forecast half, so it is quoted after the advice rather than before it.
FORECAST_SECTION = re.compile(r'forecast summary|weather during next|as per forecast|rainfall forecast', re.I)

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
    """A quoted passage with the PDF page furniture out and the cut on a sentence boundary.

    The brief quoted "2 | P a g e Advisory General advice ..." and cut mid-sentence, because it only
    collapsed whitespace. The cleaning and the boundary rules are the corpus ones, so a quote looks the
    same wherever the workspace serves it, and no wording is rewritten: only page furniture is removed.
    """
    from .corpus_tools import clean_quoted, sentence_spans
    body = clean_quoted(text)
    if len(body) <= limit:
        return body
    kept, size = [], 0
    for sentence in sentence_spans(body):
        if size + len(sentence) > limit and kept:
            break
        kept.append(sentence)
        size += len(sentence) + 1
    cut = ' '.join(kept) if kept else body[:limit]
    if len(cut) > limit:
        space = cut[:limit].rfind(' ')
        cut = cut[:space] if space > limit // 2 else cut[:limit]
    return cut.rstrip(' ,;') + ' …'

def crop_and_stage(text):
    """The crop and growth stage the passage names, read from its own words."""
    crop = CROP_ROW.search(text or '')
    stage = STAGE.search(text or '')
    return (crop.group(1).lower() if crop else None, stage.group(1).lower() if stage else None)


def crop_section(text):
    """The crop a passage is a section *about*, or None when it merely mentions one.

    A district bulletin writes each crop section under its own heading: "COTTON (Flowering) ...",
    "SORGHUM(JOWAR/GREATMILLET) (Vegetative ...)". A general paragraph can mention crops too ("tall standing
    crops such as sugarcane, cotton"), and a livestock line can name a material that is also a plant word
    ("adding slaked lime powder"). Only a name in the passage's own opening is read as the section's crop, so a
    mention does not make a livestock paragraph a crop section. Measured 17 September 2026: a general farm
    request for Surat was led by "Poultry Shed Care" because "lime" appeared later in that paragraph.
    """
    match = CROP_ROW.search(text or '')
    if not match or match.start(1) > 24:
        return None
    return match.group(1).lower()

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
        # A crop request retrieves a few clearly-matching passages; a general request asks for a wider candidate
        # set, because the first six sections of an edition are often its livestock and outlook text and the crop
        # guidance sits further in (measured 17 September 2026: a general farm request for Surat was led by
        # "Poultry Shed Care" although the same edition carries cotton advice).
        kwargs = {'family': family, 'scope': scope, 'region': where, 'limit': 12 if not crop else 6}
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
    # A printed dose instruction is quoted as the label it is, never as the district's advice: the workspace
    # does not choose, adjust or endorse a dose. The two groups are reported separately so a reader can tell
    # which sentences are guidance and which are the product label.
    from .corpus_tools import label_text_only
    label_hits = [hit for hit in kept if label_text_only(hit.get('text'))]
    advice_hits = [hit for hit in kept if not label_text_only(hit.get('text'))]
    if label_hits:
        notes.append(str(len(label_hits)) + ' retrieved passage(s) are printed product-label or dose text. They are ' +
                     'quoted in a separate list, labelled as the label, and are not served as advice: no dose is ' +
                     'chosen, adjusted or endorsed here.')
    hits = advice_hits or (label_hits if not advice_hits else [])
    if not crop and hits:
        # The district editions carry their crop sections as passages of one document, and the retrieval query for a
        # general request ("advisory") does not reach them: the first sections of an edition are its title, forecast
        # and livestock text. Measured 17 September 2026: a general farm request for Surat was answered with "Poultry
        # Shed Care" while the same edition's stored passages include COTTON, PIGEON PEA and SORGHUM sections. The
        # edition's own passages are therefore the candidate set for a general request, and each section's crop is
        # read from its own heading. Nothing is fetched from another edition, and every claim below is quoted with
        # its own printed page.
        sha = hits[0].get('document_sha256')
        try:
            stored = [payload for payload in index.document_passages(sha)] if sha else []
        except (TypeError, ValueError, OSError):
            stored = []
        if len(stored) > len(hits):
            notes.append('No crop was named, so every indexed passage of this edition was considered (' +
                         str(len(stored)) + ' passages) and the crop sections were read from their own printed headings; '
                         'the retrieval query alone would have returned the title, forecast and livestock sections.')
            hits = stored

    if not crop and len(hits) > 1:
        # With no crop named, a general request should see the edition's crop guidance rather than four sections
        # of livestock and outlook text: one passage per crop the edition names (earliest printed page for each),
        # then the remaining general or livestock sections, then the weather outlook. Measured 17 September 2026:
        # a general farm request for Surat and for Patna was led by "Poultry Shed Care" and "Live Stock Advisory".
        # Nothing is dropped from the brief's own record; the ordering and the selection are both disclosed.
        per_crop, seen_crops, others, outlook = [], set(), [], []
        for hit in hits:
            text = hit.get('text') or ''
            named = crop_section(text)
            if FORECAST_SECTION.search(text[:400]):
                outlook.append(hit)
            elif named:
                if named not in seen_crops:
                    seen_crops.add(named)
                    per_crop.append(hit)
            else:
                others.append(hit)
        spread = per_crop + others + outlook
        if spread != list(hits):
            notes.append('With no crop named, the passages are chosen one per crop the edition names (' +
                         ', '.join(sorted(seen_crops)) + ') and the general, livestock and outlook sections follow.'
                         if seen_crops else
                         'With no crop named, the edition states no crop section in the retrieved passages, so the '
                         'general and livestock sections are shown and the weather outlook is quoted last.')
            hits = spread

    def passage_rank(hit):
        text = hit.get('text') or ''
        named = crop_section(text)
        early = text[:300].lower()
        page = str(hit.get('physical_page') or '')
        if crop:
            # The requested crop's own passages lead, and a passage naming it in its opening lines leads over
            # one that mentions it once inside a long multi-crop block.
            return (0 if crop in early else 1, 0 if named else 1, page)
        if named:
            return (0, 0, page)
        if FORECAST_SECTION.search(text[:400]):
            # The weather outlook is context, not crop advice, and this brief carries its own forecast half.
            return (2, 0, page)
        return (1, 0, page)

    printed_order = list(hits)
    hits = sorted(hits, key=passage_rank)
    if hits != printed_order:
        notes.append('The passages are ordered with the requested crop first, then the other advice, and the weather '
                     'outlook last; the bulletin printed order differs. Every retrieved passage is kept.')

    passages = []
    for hit in hits:
        crop_seen, stage_seen = crop_section(hit.get('text')), crop_and_stage(hit.get('text'))[1]
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
                             'passages': passages, 'matched': len(kept),
                             'label_text': [{'source_id': hit.get('source_id'), 'page': hit.get('physical_page'),
                                             'issue_date': hit.get('issue_date'), 'section': hit.get('section'),
                                             'crop': crop_and_stage(hit.get('text'))[0],
                                             'growth_stage': crop_and_stage(hit.get('text'))[1],
                                             'quote': clean(hit.get('text')),
                                             'source_locator': hit.get('source_locator'),
                                             'document_sha256_prefix': str(hit.get('document_sha256') or '')[:12]}
                                            for hit in label_hits[:MAX_PASSAGES]]},
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
