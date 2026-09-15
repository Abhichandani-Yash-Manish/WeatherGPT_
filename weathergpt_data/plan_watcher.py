"""Plan Watch watcher: read the official district warning product, compare, and notify.

One cycle reads the national district warning attributes once, however many plans exist.
For each plan it keeps a snapshot of the plan's own days, keyed by the edition that was
read, and compares it with the previous snapshot. Only a change in the plan's watched
categories writes a notification; the first reading is a baseline, and an identical
edition says nothing.

What it never does:

* It never calls a quiet day an all-clear. "No warning for your watched hazards" is a
  statement about one product, and a removal says so.
* It never reads a missing colour code as a level.
* It never reports a plan it cannot read as quiet. A district absent from the edition, or a
  failed read, counts as not checked; three hours of that is reported once.
* It never delivers anything off this machine. Notifications are rows in a local store that
  the page reads while the workspace is running.
"""
import hashlib
import json
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .adapters import COLOURS, HAZARDS
from .plans import ACTIVITIES, ALL_CATEGORIES, PlanStore, day_phrase, hazard_phrase
from .rule_planner import IST
from .transport import SourceError, parsed, stamp

CYCLE_SECONDS = 1800
DEGRADED_AFTER = timedelta(hours=3)
CHECK_IN_HOUR = 19
QUIET_HOURS = (22, 6)
LOUD_COLOURS = {'red', 'orange'}
COVERAGE_DAYS = 5
LAYER = 'imd:district_warnings_india'
SKIPPED_STATES = {'paused', 'ended', 'not_connected'}
DAY_BASIS = ('Day n is the nth IST calendar day counted from the bulletin date; IMD does not publish a per-day '
             'validity field in this product.')


def rows_from_payload(data, meta, mode='live'):
    """District rows keyed the same way as the national warning table and the vendored map."""
    from .product_api import decode_days, norm
    rows = {}
    for feature in (data or {}).get('features') or []:
        properties = feature.get('properties') or {}
        key = norm(properties.get('District'))
        if not key or key in rows:
            continue
        issued, days = decode_days(properties)
        rows[key] = {'district': properties.get('District'), 'issued_at_utc': stamp(issued) if issued else None,
                     'updated_at': properties.get('updated_at'), 'days': days}
    sha = (meta or {}).get('sha256') or hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    return {'edition': {'sha256': sha, 'retrieved_at_utc': (meta or {}).get('retrieved_at_utc'),
                        'delivery': (meta or {}).get('delivery'), 'mode': mode, 'source_id': 'S63', 'layer': LAYER},
            'rows': rows}


class LiveEditions:
    """The current national edition, through the governed, cached product read."""

    def __init__(self, foundation):
        self.foundation = foundation

    def read(self):
        from .product_api import warning_attributes
        try:
            data, meta = warning_attributes(self.foundation)
        except (ValueError, OSError) as exc:
            raise SourceError('The IMD district warning layer could not be read: ' + str(exc)) from exc
        return rows_from_payload(data, meta)


class RecordedEdition:
    """One edition saved by scripts/capture_warning_edition.py, for a labelled replay."""

    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        try:
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            return rows_from_payload(saved['body'], saved.get('meta') or {}, mode='recorded')
        except (OSError, ValueError, KeyError) as exc:
            raise SourceError('The recorded edition ' + self.path.name + ' could not be read') from exc

    def retrieved_at(self):
        saved = json.loads(self.path.read_text(encoding='utf-8'))
        return parsed((saved.get('meta') or {}).get('retrieved_at_utc') or saved.get('captured_at_utc'))


def colour_of(day):
    code = day.get('colour_code')
    if code in (1, 2, 3):
        return COLOURS[code]
    if code == 4:
        return 'green'
    return None


def snapshot(plan, edition, now):
    """The plan's own days in one edition: matched watched categories and their colour."""
    key = (plan.get('place') or {}).get('district_key')
    row = edition['rows'].get(key)
    base = {'edition': dict(edition['edition']), 'district_key': key, 'days': {}}
    if row is None or not row.get('issued_at_utc'):
        return dict(base, coverage='no_district_row')
    issued = parsed(row['issued_at_utc'])
    base['edition'].update(issued_at_utc=row['issued_at_utc'], updated_at=row.get('updated_at'))
    base['district'] = row.get('district')
    first = issued.astimezone(IST).date()
    today = now.astimezone(IST).date()
    watched = set(plan.get('hazard_codes') or [])
    for day in row['days']:
        on = first + timedelta(days=int(day['day']) - 1)
        if on < today:
            continue
        if plan.get('kind') == 'once' and on.isoformat() != plan.get('date_local'):
            continue
        matched = sorted(set(day.get('hazard_codes') or []) & watched)
        base['days'][on.isoformat()] = {
            'day': int(day['day']), 'date': on.isoformat(), 'matched_codes': matched,
            'hazards': [HAZARDS[code] for code in matched if code in HAZARDS],
            'colour': colour_of(day) if matched else None, 'colour_code': day.get('colour_code'),
            'quiet': bool(day.get('quiet')), 'source_text': day.get('source_text') if matched else None}
    if plan.get('kind') != 'once':
        return dict(base, coverage='covered' if base['days'] else 'passed')
    target = date.fromisoformat(plan['date_local'])
    if plan['date_local'] in base['days']:
        return dict(base, coverage='covered')
    if target > first + timedelta(days=COVERAGE_DAYS - 1):
        return dict(base, coverage='waiting', available_from=(target - timedelta(days=COVERAGE_DAYS - 1)).isoformat())
    return dict(base, coverage='passed')


def _state(entry):
    return (tuple(entry['matched_codes']), entry['colour'] if entry['matched_codes'] else None)


def compare(previous, current):
    """Changes in watched categories between two snapshots of different editions."""
    if not previous or previous.get('edition', {}).get('sha256') == current['edition']['sha256']:
        return []
    changes = []
    for day, entry in sorted(current['days'].items()):
        before = (previous.get('days') or {}).get(day)
        if before is None:
            if entry['matched_codes']:
                changes.append({'kind': 'issued', 'date': day, 'before': None, 'after': entry})
            continue
        if _state(before) == _state(entry):
            continue
        kind = 'issued' if not before['matched_codes'] else ('removed' if not entry['matched_codes'] else 'changed')
        changes.append({'kind': kind, 'date': day, 'before': before, 'after': entry})
    return changes


def plan_phrase(plan):
    label = plan.get('label')
    activity = ACTIVITIES.get(plan.get('activity') or '', {}).get('label')
    if label and activity in ('spraying', 'harvest', 'irrigation'):
        return 'your ' + label + ' ' + activity
    if label or activity:
        return 'your ' + (label or activity)
    codes = set(plan.get('hazard_codes') or [])
    if codes and not codes >= set(ALL_CATEGORIES):
        return 'your ' + hazard_phrase(codes) + ' watch'
    return 'your warning watch'


def place_phrase(plan):
    place = plan.get('place') or {}
    return place.get('label') or place.get('name') or 'the saved place'


def state_text(entry):
    if not entry or not entry['matched_codes']:
        return 'no warning for your watched hazards'
    return ', '.join(entry['hazards']) + ' (' + (entry['colour'] or 'colour not supplied') + ')'


def bulletin_text(snap):
    issued = (snap.get('edition') or {}).get('issued_at_utc')
    return parsed(issued).astimezone(IST).strftime('%d %b %Y %H:%M IST') if issued else 'time not supplied'


def receipt(plan, snap, entry, before=None):
    edition = snap.get('edition') or {}
    return {'plan_id': plan['id'], 'place': place_phrase(plan), 'district': snap.get('district'),
            'date': entry['date'] if entry else None, 'day': entry['day'] if entry else None,
            'hazard_codes': entry['matched_codes'] if entry else [], 'hazards': entry['hazards'] if entry else [],
            'colour': entry['colour'] if entry else None, 'colour_code': entry['colour_code'] if entry else None,
            'before': state_text(before) if before is not None else None,
            'source_id': edition.get('source_id'), 'layer': edition.get('layer'),
            'edition_sha256': edition.get('sha256'), 'bulletin_issued_at_utc': edition.get('issued_at_utc'),
            'retrieved_at_utc': edition.get('retrieved_at_utc'), 'mode': edition.get('mode'),
            'derived_window': DAY_BASIS, 'origin_authentication': 'unverified',
            'not_established': ['Not an all-clear.', 'Not a flood or cyclone warning.', 'Not a CAP alert.']}


def visible_at(now, loud):
    """Quiet hours hold a notification until 06:00 IST unless its level is orange or red."""
    local = now.astimezone(IST)
    start, end = QUIET_HOURS
    if loud or end <= local.hour < start:
        return stamp(now)
    release = local.replace(hour=end, minute=0, second=0, microsecond=0)
    if local.hour >= start:
        release += timedelta(days=1)
    return stamp(release)


def _notify_change(store, plan, snap, change, now):
    after, before = change['after'], change['before']
    day = day_phrase(change['date'])
    lead = day + ' for ' + plan_phrase(plan) + ' in ' + place_phrase(plan) + ' changed: '
    if change['kind'] == 'removed':
        text = (lead + state_text(before) + ' → no warning for your watched hazards in this product. IMD district '
                'warning bulletin ' + bulletin_text(snap) + '. This is not an all-clear.')
    else:
        text = (lead + state_text(before) + ' → ' + state_text(after) + '. IMD district warning bulletin ' +
                bulletin_text(snap) + '. This is official product state, not an instruction.')
    title = day + ' · ' + place_phrase(plan) + ' · official warning ' + {'issued': 'issued', 'removed': 'removed',
                                                                         'changed': 'changed'}[change['kind']]
    key = ':'.join([plan['id'], 'change', change['date'], ','.join(map(str, after['matched_codes'])),
                    str(after['colour']), str(snap['edition']['sha256'])])
    loud = after['colour'] in LOUD_COLOURS
    return store.add_notification(plan['id'], 'change', key, title, text, receipt(plan, snap, after, before),
                                  stamp(now), visible_at(now, loud))


def _check_in(store, plan, snap, now):
    if plan.get('kind') != 'once' or not plan.get('check_in') or snap.get('coverage') != 'covered':
        return None
    target = date.fromisoformat(plan['date_local'])
    local = now.astimezone(IST)
    if local.date() != target - timedelta(days=1) or local.hour < CHECK_IN_HOUR:
        return None
    entry = snap['days'][plan['date_local']]
    part = plan.get('part_label') or ''
    lead = "Tomorrow's plan in " + place_phrase(plan) + ' (' + plan_phrase(plan) + ', ' + day_phrase(plan['date_local']) + \
           (' ' + part if part else '') + '): '
    body = ('IMD shows ' + state_text(entry) if entry['matched_codes'] else 'no warning in this product for your watched hazards')
    text = lead + body + ', as of the IMD district warning bulletin ' + bulletin_text(snap) + '. This is not an all-clear.'
    return store.add_notification(plan['id'], 'check_in', plan['id'] + ':check_in:' + plan['date_local'],
                                  day_phrase(plan['date_local']) + ' · ' + place_phrase(plan) + ' · evening check-in', text,
                                  receipt(plan, snap, entry), stamp(now), stamp(now))


def lifecycle(plan, snap, now):
    if plan.get('kind') != 'once':
        return 'watching'
    if now.astimezone(IST).date().isoformat() == plan.get('date_local'):
        return 'plan_day'
    return 'waiting_for_coverage' if snap.get('coverage') == 'waiting' else 'watching'


def _unreadable(store, plan, now, error):
    last_ok = plan.get('last_ok_at') or plan.get('saved_at') or plan.get('created_at')
    written = 0
    if plan.get('state') != 'degraded' and last_ok and now - parsed(last_ok) >= DEGRADED_AFTER:
        text = ('The IMD district warning product could not be read for ' + place_phrase(plan) + ' since ' +
                parsed(last_ok).astimezone(IST).strftime('%d %b %H:%M IST') + '. ' + plan_phrase(plan).capitalize() +
                ' is not being checked until a read succeeds.')
        if store.add_notification(plan['id'], 'degraded', plan['id'] + ':degraded:' + last_ok,
                                  place_phrase(plan) + ' · watch degraded', text,
                                  {'plan_id': plan['id'], 'error': error, 'last_ok_at_utc': last_ok},
                                  stamp(now), stamp(now)):
            written = 1
        store.update(plan['id'], state='degraded', last_checked_at=stamp(now), last_error=error)
    else:
        store.update(plan['id'], last_checked_at=stamp(now), last_error=error)
    return written


def check_plan(store, plan, edition, now, error=None):
    """Evaluate one plan against one edition (or a failed read). Returns notifications written."""
    if plan.get('kind') == 'once' and plan.get('window_end') and now >= parsed(plan['window_end']):
        store.update(plan['id'], state='ended', last_checked_at=stamp(now))
        return 0
    if edition is None:
        return _unreadable(store, plan, now, error or 'The official product could not be read.')
    snap = snapshot(plan, edition, now)
    if snap['coverage'] == 'no_district_row':
        return _unreadable(store, plan, now, 'The plan district is absent from the edition that was read.')
    written = 0
    for change in compare(plan.get('last_snapshot'), snap):
        if _notify_change(store, plan, snap, change, now):
            written += 1
    if _check_in(store, plan, snap, now):
        written += 1
    store.update(plan['id'], last_snapshot=snap, last_ok_at=stamp(now), last_checked_at=stamp(now),
                 state=lifecycle(plan, snap, now), last_error=None)
    return written


def _read(source):
    try:
        edition = source.read()
    except SourceError as exc:
        return None, str(exc)
    if edition['edition'].get('delivery') == 'stale_cache':
        return None, 'The live read failed and only a cached copy of the product was available.'
    return edition, None


def run_cycle(store, source, now):
    """One watcher cycle: one read of the national product, every active plan evaluated."""
    plans = [plan for plan in store.list() if plan.get('state') not in SKIPPED_STATES]
    store.meta_set('last_cycle_at', stamp(now))
    edition, error = _read(source) if plans else (None, None)
    if edition is not None:
        store.meta_set('last_ok_at', stamp(now))
    store.meta_set('last_error', error or '')
    notified = sum(check_plan(store, plan, edition, now, error) for plan in plans)
    return {'checked': len(plans), 'notified': notified, 'read': edition is not None if plans else None,
            'error': error, 'cycle_at_utc': stamp(now),
            'edition_sha256': edition['edition']['sha256'] if edition else None}


def baseline(store, plan, source, now):
    """The first reading of a new plan: stored as its snapshot, never notified."""
    if plan.get('state') in SKIPPED_STATES:
        return None
    edition, error = _read(source)
    if edition is None:
        store.update(plan['id'], last_checked_at=stamp(now), last_error=error)
        return None
    snap = snapshot(plan, edition, now)
    if snap['coverage'] == 'no_district_row':
        store.update(plan['id'], last_checked_at=stamp(now), last_error='The plan district is absent from the edition that was read.')
        return snap
    store.update(plan['id'], last_snapshot=snap, last_ok_at=stamp(now), last_checked_at=stamp(now),
                 state=lifecycle(plan, snap, now), last_error=None)
    return snap


def replay(live_store, replay_store, paths, now=None):
    """Replay recorded editions over copies of the live plans, into the replay store only."""
    editions = [RecordedEdition(path) for path in paths]
    if len(editions) < 2:
        raise SourceError('A replay needs at least two recorded editions; record them with scripts/capture_warning_edition.py.')
    for plan in replay_store.list():
        replay_store.delete(plan['id'])
    copies = []
    for plan in live_store.list():
        if plan.get('state') in {'ended'}:
            continue
        fields = {key: value for key, value in plan.items()
                  if key not in {'id', 'last_snapshot', 'last_ok_at', 'last_checked_at', 'last_error'}}
        if fields.get('state') == 'degraded':
            fields['state'] = 'watching'
        copies.append(replay_store.create(fields))
    first = editions[0]
    started = first.retrieved_at()
    for plan in copies:
        baseline(replay_store, replay_store.get(plan['id']), first, started)
    notified, cycles = 0, []
    for recorded in editions[1:]:
        result = run_cycle(replay_store, recorded, recorded.retrieved_at())
        notified += result['notified']
        cycles.append(result)
    return {'mode': 'replay_of_recorded_editions', 'plans': len(copies), 'editions': [str(Path(p).name) for p in paths],
            'notified': notified, 'cycles': cycles,
            'note': 'Replay of recorded IMD editions: nothing here is current, and nothing was written to the live inbox.'}


class PlanWatcher:
    """A background cycle inside the workspace process. It runs only while the workspace runs."""

    def __init__(self, workspace, interval=CYCLE_SECONDS):
        self.workspace = workspace
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None
        self.last_result = None

    def run_once(self):
        store = self.workspace.plan_store()
        self.last_result = run_cycle(store, LiveEditions(self.workspace.foundation()), self.workspace.clock())
        return self.last_result

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.run_once()
            except Exception as exc:  # the loop must survive one bad cycle; the failure is recorded
                self.last_result = {'error': 'The watcher cycle failed: ' + type(exc).__name__,
                                    'cycle_at_utc': stamp(datetime.now(timezone.utc))}
            self._stop.wait(self.interval)

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name='plan-watcher', daemon=True)
            self._thread.start()
        return self

    def stop(self):
        self._stop.set()

    def status(self):
        return {'running': bool(self._thread and self._thread.is_alive()), 'interval_seconds': self.interval,
                'last_result': self.last_result}


__all__ = ['PlanStore', 'LiveEditions', 'RecordedEdition', 'rows_from_payload', 'snapshot', 'compare', 'run_cycle',
           'baseline', 'replay', 'PlanWatcher', 'check_plan', 'visible_at']
