"""Plan Watch in the conversation: infer the plan, ask only for what is really missing.

A person describes a plan in their own words. Everything that can be read from those words,
or from the conversation so far, is set automatically: the activity, the hazards it makes
relevant, a label, the evening-before check-in. A question is asked only when the plan
cannot work without the answer - a place, a day, or the time of an activity - and only one
question per turn. The plan is saved as soon as the last needed slot is known; the reply is
the confirmation, and Undo removes it.

This runs before the model planner and needs no model call. When a turn is not about a plan,
it returns None and the normal engine answers.
"""
import re
from datetime import date, timedelta

from . import plans as P
from .plan_watcher import bulletin_text, place_phrase, plan_phrase, state_text
from .rule_planner import language_of, places_of
from .transport import SourceError, parsed, stamp, utcnow

LIST = re.compile(r"\b(?:what|which|show|list|see)\b[^?.!]{0,40}\b(?:plans?|reminders?|watch(?:es)?)\b"
                  r"|\bmy (?:plans|reminders|watches)\b", re.I)
CANCEL = re.compile(r"\b(?:cancel|delete|remove|stop|end|forget)\b[^?.!]{0,60}\b(?:plans?|reminders?|watch(?:es)?)\b", re.I)
PAUSE = re.compile(r"\b(?:pause|hold|mute)\b[^?.!]{0,60}\b(?:plans?|reminders?|watch(?:es)?)\b", re.I)
RESUME = re.compile(r"\b(?:resume|unpause|restart|unmute)\b[^?.!]{0,60}\b(?:plans?|reminders?|watch(?:es)?)\b", re.I)
CHANGE = re.compile(r"^\s*(?:(?:make|move|change|shift|switch|set)\s+(?:it|that|this|the plan|my plan)\b|.*\binstead\b)", re.I)
UNDO = re.compile(r"^\s*(?:undo(?: that)?|don'?t save(?: it| that)?|do not save(?: it| that)?)\s*[.!]?\s*$", re.I)
WATCH_THIS = re.compile(r"^\s*watch this plan\s*[.!]?\s*$", re.I)
DROP = re.compile(r"^\s*(?:cancel|never ?mind|forget it|no thanks|leave it)\s*[.!]?\s*$", re.I)
PLAN_ID = re.compile(r'\bplan ([0-9a-f]{8})\b', re.I)
COMMAND_WORDS = {'let', 'tell', 'notify', 'remind', 'keep', 'alert', 'warn', 'inform', 'please', 'i', "i'm", 'im',
                 'watch', 'make', 'move', 'change', 'cancel', 'pause', 'resume', 'undo'}
PLACE_LEAD = re.compile(r'^\s*(?:in|at|near|for|around)\s+', re.I)
TIME_REPLIES = [{'label': 'Morning', 'reply': 'Morning'}, {'label': 'Afternoon', 'reply': 'Afternoon'},
                {'label': 'Evening', 'reply': 'Evening'}, {'label': 'All day', 'reply': 'All day'}]
STATE_WORDS = {'watching': 'watching', 'waiting_for_coverage': 'waiting for IMD coverage', 'plan_day': 'plan day',
               'degraded': 'not being checked (read failing)', 'paused': 'paused', 'ended': 'ended',
               'not_connected': 'cannot be checked (not connected)'}


def plan_candidate(question):
    """A question that describes a dated activity without asking to be kept informed."""
    if P.notify_intent(question) or not P.activity_of(question):
        return False
    day = P.parse_day(question, utcnow())
    return bool(day and day['kind'] == 'once')


def might_be_plan_turn(state, question):
    """A cheap check that touches no store, so ordinary turns cost nothing extra."""
    text = (question or '').strip()
    if state.get('plan_draft') or state.get('plan_focus'):
        return True
    if WATCH_THIS.match(text) and state.get('plan_candidate'):
        return True
    return bool(P.notify_intent(text) or LIST.search(text) or CANCEL.search(text) or PAUSE.search(text) or RESUME.search(text))


def take_turn(engine, state, body, question, base):
    """Handle a plan turn and return its packet, or None when the turn is not about a plan."""
    if not might_be_plan_turn(state, question):
        return None
    now = engine.workspace.clock()
    store = engine.plan_store()
    text = (question or '').strip()
    if state.get('plan_draft'):
        handled = _continue_draft(engine, store, state, body, text, base, now)
        if handled is not None:
            return handled
    focus = state.get('plan_focus')
    if focus:
        if UNDO.match(text):
            return _manage(engine, store, state, text, base, now, 'delete', forced=focus)
        if CHANGE.search(text) or _only_when_words(text, now):
            changed = _change(engine, store, state, text, base, now, focus)
            if changed is not None:
                return changed
    for pattern, action in ((LIST, 'list'), (CANCEL, 'delete'), (PAUSE, 'pause'), (RESUME, 'resume')):
        if pattern.search(text):
            return _manage(engine, store, state, text, base, now, action)
    if WATCH_THIS.match(text) and state.get('plan_candidate'):
        return _create(engine, store, state, state.pop('plan_candidate'), base, now)
    if P.notify_intent(text):
        return _create(engine, store, state, text, base, now)
    return None


# ----- building a plan -------------------------------------------------------------------

def _read_slots(text, now):
    activity = P.activity_of(text)
    codes, unconnected = P.explicit_hazards(text)
    inferred = {}
    if activity:
        inferred['activity'] = 'from your words: ' + activity.replace('_', ' ')
    if codes:
        hazard_codes, inferred['hazards'] = codes, 'named in your message'
    elif activity:
        hazard_codes, inferred['hazards'] = list(P.ACTIVITIES[activity]['codes']), 'from the ' + P.ACTIVITIES[activity]['label'] + ' template'
    else:
        hazard_codes, inferred['hazards'] = list(P.ALL_CATEGORIES), 'no activity named, so every official category'
    not_connected, extra_note = None, None
    if activity == 'fishing':
        hazard_codes, not_connected = [], P.ACTIVITIES['fishing']['not_connected']
    elif unconnected and not codes:
        hazard_codes = []
        not_connected = ('No connected official product carries a ' + unconnected + ' warning, so this plan is recorded '
                         'but cannot be checked. It is not mapped onto a similar-sounding product.')
    elif unconnected:
        extra_note = ('No connected official product carries a ' + unconnected + ' warning; only ' +
                      P.hazard_phrase(hazard_codes) + ' are watched.')
    places = _places(text)
    return {'question': text, 'activity': activity, 'label': P.label_of(text), 'hazard_codes': sorted(hazard_codes),
            'not_connected': not_connected, 'extra_note': extra_note, 'day': P.parse_day(text, now),
            'time': P.parse_time(text), 'place_request': places[0] if places else None, 'place': None,
            'inferred': inferred, 'language': language_of(text), 'awaiting': None, 'choices': []}


def _create(engine, store, state, text, base, now):
    draft = _read_slots(text, now)
    resolution = None
    if draft['place_request']:
        resolution = engine.resolve_plan_place(draft['place_request'])
    elif state.get('resolved_points'):
        earlier = list(state['resolved_points'].values())[-1]
        if isinstance(earlier, dict) and earlier.get('coordinates'):
            resolution = engine.resolve_plan_place({'choice': earlier, 'name': earlier.get('name') or earlier.get('label')})
            draft['inferred']['place'] = 'the place already used in this conversation'
    return _advance(engine, store, state, base, now, draft, resolution)


def _apply_resolution(draft, resolution):
    """Returns a question packet fragment when the place still needs the person, else None."""
    status = (resolution or {}).get('status')
    name = ((draft.get('place_request') or {}).get('name')) or 'that place'
    if status == 'resolved':
        draft['place'] = resolution['place']
        draft['choices'] = []
        draft['inferred'].setdefault('place', 'from your message')
        return None
    if status == 'ambiguous':
        draft['choices'] = resolution['choices']
        return ('needs_selection', 'More than one place matches ' + name + '. Choose the one this plan is for, so an '
                'official warning is never attached to the wrong district.', [])
    if status == 'outside':
        return ('needs_clarification', 'The point for ' + name + ' is outside every IMD district in the warning product, '
                'so it cannot be checked there. Which nearby town should I use?', [])
    if status == 'not_found':
        return ('needs_clarification', 'I could not find a place called ' + name + '. Which town or district is this '
                'plan for? Add its state if the name is shared.', [])
    return None


def _advance(engine, store, state, base, now, draft, resolution=None):
    asked = _apply_resolution(draft, resolution)
    if asked:
        return _ask(state, base, draft, 'place', *asked)
    if not draft['place']:
        return _ask(state, base, draft, 'place', 'needs_clarification',
                    'Which place is this plan for? A town or district with its state is enough.', [])
    day = draft['day']
    if day is None and draft['activity'] is None:
        day = draft['day'] = {'kind': 'always'}
        draft['inferred']['when'] = 'no day named, so every day IMD publishes'
    if day is None or day['kind'] == 'past':
        lead = 'That date has already passed. ' if day else ''
        return _ask(state, base, draft, 'day', 'needs_clarification',
                    lead + 'Which day is ' + plan_phrase(draft) + ' in ' + place_phrase(draft) + '?', _day_replies(now))
    if day['kind'] == 'once' and not draft['time']:
        if draft['activity']:
            return _ask(state, base, draft, 'time', 'needs_clarification',
                        'What time on ' + P.day_phrase(day['date']) + '?', TIME_REPLIES)
        draft['time'] = P.parse_time('all day')
        draft['inferred']['time'] = 'no activity named, so the whole day'
    if day['kind'] == 'once':
        draft['day'] = day = P.settle_date(day, draft['time'], now)
        _, end = P.window_of(day['date'], draft['time'])
        if _instant(end) <= now:
            draft['day'] = None
            return _ask(state, base, draft, 'day', 'needs_clarification',
                        'That time has already passed. Which day is ' + plan_phrase(draft) + '?', _day_replies(now))
    return _save(engine, store, state, base, now, draft)


def _instant(iso):
    return parsed(iso)


def _day_replies(now):
    today = now.astimezone(P.IST).date()
    replies = [{'label': 'Tomorrow', 'reply': 'Tomorrow'}]
    for ahead in (2, 3):
        name = P.WEEKDAY_NAMES[(today + timedelta(days=ahead)).weekday()].capitalize()
        replies.append({'label': name, 'reply': name})
    replies.append({'label': 'Every day', 'reply': 'always'})
    return replies


def _ask(state, base, draft, slot, status, answer, replies):
    draft['awaiting'] = slot
    state['plan_draft'] = draft
    state.pop('plan_focus', None)
    return _packet(base, status, answer, quick_replies=replies,
                   choices=draft.get('choices') if slot == 'place' else [],
                   plan_watch={'action': 'asking', 'awaiting': slot})


def _fields(draft, now):
    day, slot = draft['day'], draft['time']
    once = day['kind'] == 'once'
    start, end = P.window_of(day['date'], slot) if once else (None, None)
    return {'question': draft['question'], 'label': draft['label'], 'activity': draft['activity'],
            'hazard_codes': draft['hazard_codes'], 'not_connected': draft['not_connected'], 'place': draft['place'],
            'kind': day['kind'], 'date_local': day['date'] if once else None, 'window_start': start, 'window_end': end,
            'part_label': slot['label'] if once else None, 'check_in': once and not draft['not_connected'],
            'state': 'not_connected' if draft['not_connected'] else 'watching', 'inferred': draft['inferred'],
            'language': draft['language'], 'created_at': stamp(now), 'saved_at': stamp(now)}


def _save(engine, store, state, base, now, draft):
    first = not store.list()
    plan = store.create(_fields(draft, now))
    snap = None if plan['state'] == 'not_connected' else engine.plan_baseline(plan)
    plan = store.get(plan['id'])
    state.pop('plan_draft', None)
    state['plan_focus'] = plan['id']
    answer = summary(plan, snap, lead='Saved.', first=first)
    if draft.get('extra_note'):
        answer += ' ' + draft['extra_note']
    return _packet(base, 'answered', answer, plan_watch={'action': 'saved', 'plan': public(plan)})


def _continue_draft(engine, store, state, body, text, base, now):
    draft = state['plan_draft']
    if DROP.match(text):
        state.pop('plan_draft', None)
        return _packet(base, 'answered', "Okay, I didn't save that plan.", plan_watch={'action': 'dropped'})
    awaiting = draft.get('awaiting')
    if awaiting == 'place' and body.get('selection_id'):
        choice = next((item for item in draft.get('choices') or [] if item.get('selection_id') == body['selection_id']), None)
        if choice is None:
            raise SourceError('Choose a place from the candidates offered for this plan')
        resolution = engine.resolve_plan_place({'choice': choice, 'name': (draft.get('place_request') or {}).get('name')})
        return _advance(engine, store, state, base, now, draft, resolution)
    day, slot = P.parse_day(text, now), P.parse_time(text)
    resolution, filled = None, False
    if awaiting == 'place' and draft.get('choices'):
        from .dialogue import select_reply
        picked = select_reply(text, draft['choices'])
        if picked:
            resolution = engine.resolve_plan_place({'choice': picked, 'name': (draft.get('place_request') or {}).get('name')})
            return _advance(engine, store, state, base, now, draft, resolution)
    if awaiting == 'place':
        places = _places(text)
        request = places[0] if places else _bare_place(text)
        if request:
            draft['place_request'] = request
            resolution = engine.resolve_plan_place(request)
            filled = True
    elif awaiting == 'day' and day:
        draft['day'] = day
        filled = True
    elif awaiting == 'time' and slot:
        draft['time'] = slot
        filled = True
    if not filled:
        if '?' in text or len(text.split()) > 5:
            state.pop('plan_draft', None)
            return None
        return _ask(state, base, draft, awaiting, 'needs_clarification', "I didn't catch that. " +
                    {'place': 'Which place is this plan for?', 'day': 'Which day is it?',
                     'time': 'What time is it?'}.get(awaiting, ''),
                    TIME_REPLIES if awaiting == 'time' else (_day_replies(now) if awaiting == 'day' else []))
    if day and awaiting != 'day' and not draft.get('day'):
        draft['day'] = day
    if slot and awaiting != 'time' and not draft.get('time'):
        draft['time'] = slot
    return _advance(engine, store, state, base, now, draft, resolution)


def _places(text):
    """Named places, without the request words a plan statement starts with.

    The Hinglish locative pattern reads "Let me know" as a place called "Let" followed by
    "me"; a plan statement opens with exactly these words, so they are never place names.
    """
    return [place for place in places_of(text) if place['name'].split()[0].lower().strip("'’") not in COMMAND_WORDS]


def _bare_place(text):
    name = PLACE_LEAD.sub('', text).strip(' .!')
    if not name or '?' in name or len(name.split()) > 4 or re.search(r'\d', name):
        return None
    head, _, tail = name.partition(',')
    return {'name': head.strip(), 'state': tail.strip(), 'district': '', 'kind': 'unknown'}


# ----- acting on saved plans -------------------------------------------------------------

def _only_when_words(text, now):
    return ('?' not in text and len(text.split()) <= 4 and
            bool(P.parse_time(text) or (P.parse_day(text, now) or {}).get('kind') == 'once'))


def _nearest_weekday(day, plan, now):
    """'Make it Tuesday' means the Tuesday nearest the plan's current day, never a past one."""
    if day.get('basis') not in P.WEEKDAY_NAMES or not plan.get('date_local'):
        return day
    current = date.fromisoformat(plan['date_local'])
    target = P.WEEKDAY_NAMES.index(day['basis'])
    offset = (target - current.weekday()) % 7
    if offset > 3:
        offset -= 7
    chosen = current + timedelta(days=offset)
    today = now.astimezone(P.IST).date()
    while chosen < today:
        chosen += timedelta(days=7)
    return dict(day, date=chosen.isoformat())


def _change(engine, store, state, text, base, now, plan_id):
    try:
        plan = store.get(plan_id)
    except SourceError:
        state.pop('plan_focus', None)
        return None
    day, slot = P.parse_day(text, now), P.parse_time(text)
    if not day and not slot:
        return None
    if day and day['kind'] == 'past':
        return _packet(base, 'needs_clarification', 'That date has already passed, so the plan was not changed.',
                       plan_watch={'action': 'unchanged', 'plan': public(plan)})
    kind = day['kind'] if day else plan['kind']
    if kind == 'always':
        updates = {'kind': 'always', 'date_local': None, 'window_start': None, 'window_end': None, 'part_label': None,
                   'check_in': False}
    else:
        if day and plan['kind'] == 'once':
            day = _nearest_weekday(day, plan, now)
        on = day['date'] if day else plan['date_local']
        if not on:
            return None
        if slot is None:
            slot = P.parse_time(plan.get('part_label') or '') or P.parse_time('all day')
        start, end = P.window_of(on, slot)
        if _instant(end) <= now:
            return _packet(base, 'needs_clarification', 'That time has already passed, so the plan was not changed.',
                           plan_watch={'action': 'unchanged', 'plan': public(plan)})
        updates = {'kind': 'once', 'date_local': on, 'window_start': start, 'window_end': end, 'part_label': slot['label'],
                   'check_in': not plan.get('not_connected')}
    plan = store.update(plan_id, last_snapshot=None, last_ok_at=None,
                        state='not_connected' if plan.get('not_connected') else 'watching', **updates)
    snap = None if plan['state'] == 'not_connected' else engine.plan_baseline(plan)
    plan = store.get(plan_id)
    state['plan_focus'] = plan_id
    return _packet(base, 'answered', summary(plan, snap, lead='Changed.'), plan_watch={'action': 'changed', 'plan': public(plan)})


def _manage(engine, store, state, text, base, now, action, forced=None):
    plans = [plan for plan in store.list() if plan.get('state') != 'ended']
    if action == 'list':
        if not plans:
            return _packet(base, 'answered', 'You have no saved plans. Tell me what you are planning and ask me to let you know if anything changes.',
                           plan_watch={'action': 'listed', 'plans': []})
        lines = ['%d. %s (%s)' % (index, title(plan), STATE_WORDS.get(plan.get('state'), plan.get('state')))
                 for index, plan in enumerate(plans, start=1)]
        return _packet(base, 'answered', 'You have %d saved plan%s: %s.' % (len(plans), '' if len(plans) == 1 else 's', '; '.join(lines)),
                       plan_watch={'action': 'listed', 'plans': [public(plan) for plan in plans]})
    if action == 'resume':
        plans = [plan for plan in plans if plan.get('state') == 'paused']
    elif action == 'pause':
        plans = [plan for plan in plans if plan.get('state') not in ('paused', 'not_connected')]
    matches = _target(plans, text, now, forced or state.get('plan_focus'))
    verb = {'delete': 'cancel', 'pause': 'pause', 'resume': 'resume'}[action]
    if not matches:
        return _packet(base, 'answered', 'I could not find a saved plan to ' + verb + '. Ask "what plans do I have?" to see them.',
                       plan_watch={'action': 'not_found'})
    if len(matches) > 1:
        return _packet(base, 'needs_clarification', 'Which plan should I ' + verb + '?',
                       quick_replies=[{'label': title(plan), 'reply': verb + ' plan ' + plan['id'][:8]} for plan in matches[:6]],
                       plan_watch={'action': 'choosing', 'plans': [public(plan) for plan in matches[:6]]})
    plan = matches[0]
    if action == 'delete':
        store.delete(plan['id'])
        state.pop('plan_focus', None)
        return _packet(base, 'answered', 'Cancelled ' + title(plan) + '. It will not be checked again.',
                       plan_watch={'action': 'deleted', 'plan': public(plan)})
    if action == 'pause':
        plan = store.update(plan['id'], state='paused')
        return _packet(base, 'answered', 'Paused ' + title(plan) + '. Nothing is checked or sent until you resume it.',
                       plan_watch={'action': 'paused', 'plan': public(plan)})
    plan = store.update(plan['id'], state='watching', last_snapshot=None, last_ok_at=None)
    snap = engine.plan_baseline(plan)
    plan = store.get(plan['id'])
    return _packet(base, 'answered', summary(plan, snap, lead='Resumed.'), plan_watch={'action': 'resumed', 'plan': public(plan)})


def _target(plans, text, now, focus):
    named = PLAN_ID.search(text)
    if named:
        return [plan for plan in plans if plan['id'].startswith(named.group(1).lower())]
    activity, label = P.activity_of(text), P.label_of(text)
    day = P.parse_day(text, now)
    lowered = text.lower()
    place_named = any((plan.get('place') or {}).get('name', '').lower() in lowered for plan in plans
                      if (plan.get('place') or {}).get('name'))
    filtered = [plan for plan in plans
                if (not activity or plan.get('activity') == activity)
                and (not label or plan.get('label') == label)
                and (not day or day.get('kind') != 'once' or plan.get('date_local') == day['date'])
                and (not place_named or (plan.get('place') or {}).get('name', '').lower() in lowered)]
    if activity or label or place_named or (day and day.get('kind') == 'once'):
        return filtered
    if focus:
        return [plan for plan in plans if plan['id'] == focus]
    return plans


def related_plans(store, result):
    """Sentences naming a saved plan whose place and day an ordinary answer covers."""
    points = [point for point in (result.get('resolved_points') or {}).values() if isinstance(point, dict)]
    names = {str(point.get('name') or '').casefold() for point in points}
    names |= {str(point.get('label') or '').split(',')[0].strip().casefold() for point in points}
    names.discard('')
    if not names:
        return []
    days = set()
    for fact in result.get('facts') or []:
        for key in ('start', 'end'):
            try:
                days.add(parsed(fact[key]).astimezone(P.IST).date().isoformat())
            except (KeyError, TypeError, ValueError):
                continue
    sentences = []
    for plan in store.list():
        if plan.get('state') in ('ended', 'paused', 'not_connected'):
            continue
        if str((plan.get('place') or {}).get('name') or '').casefold() not in names:
            continue
        if plan.get('kind') == 'once':
            if plan.get('date_local') not in days:
                continue
            part = plan.get('part_label') if plan.get('part_label') not in (None, 'all day') else ''
            sentences.append(P.day_phrase(plan['date_local']) + (' ' + part if part else '') + ' is ' + plan_phrase(plan) +
                             ' plan; I am watching IMD district warnings for it.')
        else:
            sentences.append('You have a standing plan for ' + place_phrase(plan) + '; I am watching IMD district warnings for it.')
    return sentences[:2]


# ----- wording -----------------------------------------------------------------------------

def title(plan):
    what = plan_phrase(plan)[len('your '):] if plan_phrase(plan).startswith('your ') else plan_phrase(plan)
    parts = [what[:1].upper() + what[1:], place_phrase(plan)]
    if plan.get('kind') == 'once' and plan.get('date_local'):
        parts.append(P.day_phrase(plan['date_local']) + (' ' + plan['part_label'] if plan.get('part_label') else ''))
    else:
        parts.append('every day')
    return ' · '.join(parts)


def _window_words(plan):
    label = plan.get('part_label') or ''
    if label == 'all day':
        return 'all day'
    start, end = plan['window_start'][11:16], plan['window_end'][11:16]
    return (label + ' ' if label and not label.startswith('from') else '') + '(' + start + '–' + end + ' IST)'


def summary(plan, snap, lead='Saved.', first=False):
    where, what = place_phrase(plan), plan_phrase(plan)
    district = (plan.get('place') or {}).get('district')
    sentences = []
    if plan.get('state') == 'not_connected':
        sentences.append(lead + ' ' + (plan.get('not_connected') or 'This plan cannot be checked.'))
        sentences.append('Recorded for ' + where + (' on ' + P.day_phrase(plan['date_local']) if plan.get('date_local') else '') + '.')
        return ' '.join(sentences)
    hazards = P.hazard_phrase(plan.get('hazard_codes'))
    if plan.get('kind') == 'once':
        sentences.append(lead + " I'm watching " + P.day_phrase(plan['date_local']) + ', ' + _window_words(plan) + ' in ' +
                         where + ' for ' + what + ': IMD district warnings for ' + hazards + '.')
    else:
        sentences.append(lead + " I'm watching " + where + ' for ' + what + ', every day IMD publishes: district warnings for ' +
                         hazards + '.')
    if district:
        sentences.append('IMD district: ' + district + '.')
    sentences.append(_coverage_words(plan, snap))
    if plan.get('check_in'):
        sentences.append("I'll message you the evening before.")
    if first:
        sentences.append('Notifications appear in the Watch panel, and as browser notifications if you allow them, while '
                         'WeatherGPT is running on this machine.')
    return ' '.join(sentence for sentence in sentences if sentence)


def _coverage_words(plan, snap):
    if not snap:
        return "I couldn't read the IMD district warning product just now, so the first check is still to come."
    coverage = snap.get('coverage')
    if coverage == 'waiting' and plan.get('date_local') and snap.get('available_from'):
        available = date.fromisoformat(snap['available_from'])
        return ('Official warnings for ' + P.WEEKDAY_NAMES[date.fromisoformat(plan['date_local']).weekday()].capitalize() +
                ' become available on ' + str(available.day) + ' ' + available.strftime('%b') + '.')
    if coverage == 'no_district_row':
        return 'The district was missing from the edition just read, so the first check is still to come.'
    if coverage == 'passed':
        return 'The latest IMD bulletin no longer covers this day.'
    days = snap.get('days') or {}
    if plan.get('kind') == 'once':
        entry = days.get(plan['date_local'])
        if entry and entry['matched_codes']:
            return 'The IMD bulletin of ' + bulletin_text(snap) + ' currently shows ' + state_text(entry) + ' for that day.'
        return ('The IMD bulletin of ' + bulletin_text(snap) + ' currently shows no warning for your watched hazards on that '
                'day. That is not an all-clear.')
    warned = [P.day_phrase(day) + ' ' + state_text(entry) for day, entry in sorted(days.items()) if entry['matched_codes']]
    if warned:
        return 'The IMD bulletin of ' + bulletin_text(snap) + ' currently shows: ' + '; '.join(warned) + '.'
    return ('The IMD bulletin of ' + bulletin_text(snap) + ' currently shows no warning for your watched hazards in its '
            'published days. That is not an all-clear.')


def public(plan):
    keys = ('id', 'label', 'activity', 'hazard_codes', 'kind', 'date_local', 'window_start', 'window_end', 'part_label',
            'check_in', 'state', 'not_connected', 'last_checked_at', 'last_error', 'inferred')
    out = {key: plan.get(key) for key in keys}
    place = plan.get('place') or {}
    out.update(place=place_phrase(plan), district=place.get('district'), hazards=P.hazard_phrase(plan.get('hazard_codes')),
               day=P.day_phrase(plan['date_local']) if plan.get('date_local') else None, title=title(plan),
               state_words=STATE_WORDS.get(plan.get('state'), plan.get('state')))
    snap = plan.get('last_snapshot') or {}
    if snap:
        out['coverage'] = snap.get('coverage')
        out['bulletin'] = bulletin_text(snap) if (snap.get('edition') or {}).get('issued_at_utc') else None
    return out


def _packet(base, status, answer, **extra):
    packet = {key: base.get(key) for key in ('schema_version', 'conversation_id', 'question', 'answered_at_utc')}
    packet.update({'schema_version': packet.get('schema_version') or 'weather-conversation-v1', 'status': status,
                   'answer': answer, 'facts': [], 'citations': [], 'notes': [], 'choices': [], 'quick_replies': [],
                   'follow_up': None, 'operational_eligible': False, 'expires_at_utc': None,
                   'trace': {'planning': {'provider': 'deterministic_plan_intake', 'model_calls': 0}, 'generation': None,
                             'tools': [], 'provider': 'deterministic_plan_intake'}})
    packet.update(extra)
    return packet
