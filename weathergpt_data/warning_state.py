"""Canonical warning state (canon-v1) and change detection for watch delivery.

The warning engine (`warning_tools.execute_warning`, `district_warnings`,
`cap_lifecycle`) remains the sole authority on official state. This module adds
the thin, pure layer the dissemination pipeline was missing:

* `build_snapshot` — a normalized, versioned snapshot of the official state
  that matters to one watch. Only meaningful warning fields participate;
  volatile fields (fetch/retrieval timestamps, request/correlation ids, cache
  metadata, rendered text, feed order) are excluded by construction, so an
  identical official state always reproduces the same fingerprint.
* `fingerprint` — deterministic SHA-256 over the canonical snapshot. The
  canonical dict is byte-identical to what `watches.compute_fingerprint` has
  always hashed, so stored fingerprints stay valid (no migration, no
  re-notification storm on upgrade).
* `detect` — explicit change classification: baseline / created / updated /
  cancelled / expired / no_change / held. `no_change` and `held` never create
  user notifications; absence of a warning is never an all-clear.

Warning identity (which official version is this) comes from the existing
lifecycle system; delivery identity (has this watch seen this state) is the
(watch_id, fingerprint) pair stored on the watch row.
"""
import hashlib
import json

CANON_VERSION = 'canon-v1'

# Internal event kinds. Only created/updated/cancelled may enqueue a delivery;
# baseline establishes state silently, expired is silent, no_change/held are
# internal and must never notify.
KINDS = ('baseline', 'created', 'updated', 'cancelled', 'expired',
         'no_change', 'held')


def _normalise_facts(facts):
    """Official district-warning facts only, stable fields only, sorted."""
    items = []
    for fact in facts or []:
        if not isinstance(fact, dict) or fact.get('parameter') != 'official_district_warning':
            continue
        items.append({'id': fact.get('id'), 'label': fact.get('label'),
                      'value': fact.get('value'), 'start': fact.get('start'),
                      'end': fact.get('end'),
                      'hazard_codes': sorted(fact.get('hazard_codes') or []),
                      'quiet': bool(fact.get('quiet')),
                      'source_id': fact.get('source_id')})
    items.sort(key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    return items


def canonical_input(watch_id, hazard, place_name, facts, reason,
                    packet_status, cap_eligible=None, cap_messages=None):
    """The exact canonical dict whose SHA-256 is the delivery fingerprint.

    Field set and ordering are frozen: this must stay byte-identical to the
    historical `watches.compute_fingerprint` input so existing stored
    fingerprints keep matching. Any new canonical field belongs in the
    snapshot envelope (`build_snapshot`), never in this dict.
    """
    return {'watch_id': watch_id, 'hazard': hazard, 'place': place_name or '',
            'facts': _normalise_facts(facts), 'reason': reason,
            'packet_status': packet_status, 'cap_eligible': cap_eligible,
            'cap_messages': cap_messages}


def fingerprint(canonical):
    """Deterministic SHA-256 of canonical input (sorted keys, UTF-8)."""
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode('utf-8')
    ).hexdigest()


def build_snapshot(watch_id, hazard, place_name, facts, reason,
                   packet_status, cap_eligible=None, cap_messages=None,
                   matched=False):
    """Versioned snapshot of what one watch observed. Pure; JSON-safe."""
    canonical = canonical_input(watch_id, hazard, place_name, facts, reason,
                                packet_status, cap_eligible, cap_messages)
    return {'canon_version': CANON_VERSION, 'watch_id': watch_id,
            'hazard': hazard, 'place': place_name or '',
            'facts': canonical['facts'], 'reason': reason,
            'packet_status': packet_status, 'cap_eligible': cap_eligible,
            'cap_messages': cap_messages, 'matched': bool(matched),
            'fingerprint_sha256': fingerprint(canonical)}


def detect(old, new, unavailable=False, not_connected=False,
           window_expired=False, official_cancel=False):
    """Classify the transition from stored snapshot `old` to `new`.

    `old` is None on the first readable check. Returns
    {'kind', 'reason', 'detail', 'fingerprint_sha256'}. Kinds `no_change`
    and `held` must never enqueue; `baseline` establishes state silently.
    """
    if window_expired:
        return {'kind': 'expired', 'reason': 'window_ended',
                'detail': 'The watch window ended before this check.',
                'fingerprint_sha256': (new or {}).get('fingerprint_sha256')}
    if unavailable:
        return {'kind': 'held', 'reason': 'held_unavailable',
                'detail': 'The official source was unreachable; nothing is enqueued and the stored state does not move.',
                'fingerprint_sha256': (old or {}).get('fingerprint_sha256')}
    if not_connected:
        return {'kind': 'held', 'reason': 'not_connected_held',
                'detail': 'The connected official products do not carry this hazard; the state advances but nothing is enqueued.',
                'fingerprint_sha256': (new or {}).get('fingerprint_sha256')}
    if old is None:
        return {'kind': 'baseline', 'reason': 'first_readable_check',
                'detail': 'The first readable check establishes the baseline and enqueues nothing.',
                'fingerprint_sha256': (new or {}).get('fingerprint_sha256')}
    if official_cancel:
        return {'kind': 'cancelled', 'reason': 'official_cancel',
                'detail': 'The official source cancelled this warning. This is a cancellation notice, not an all-clear for other hazards.',
                'fingerprint_sha256': (new or {}).get('fingerprint_sha256')}
    if old.get('fingerprint_sha256') == new.get('fingerprint_sha256'):
        return {'kind': 'no_change', 'reason': 'identical_canonical_state',
                'detail': 'The canonical official state is unchanged; nothing is enqueued.',
                'fingerprint_sha256': new.get('fingerprint_sha256')}
    if not old.get('matched') and new.get('matched'):
        kind, reason = 'created', 'new_applicable_warning'
        detail = 'A new applicable official warning was observed for this watch.'
    elif old.get('matched') and not new.get('matched'):
        kind, reason = 'updated', 'warning_removed_or_downgraded'
        detail = ('The previously observed warning state changed (removal or downgrade). '
                  'This is a change notice, never an all-clear.')
    else:
        kind, reason = 'updated', 'warning_state_changed'
        detail = 'The applicable official warning state changed meaningfully.'
    return {'kind': kind, 'reason': reason, 'detail': detail,
            'fingerprint_sha256': new.get('fingerprint_sha256')}


def snapshot_from_stored(watch):
    """Rebuild the comparable old snapshot from a stored watch row, if any."""
    stored = watch.get('fingerprint_sha256')
    if not stored:
        return None
    return {'canon_version': CANON_VERSION, 'watch_id': watch.get('id'),
            'hazard': watch.get('hazard'),
            'place': (watch.get('place') or {}).get('name') or '',
            'fingerprint_sha256': stored,
            'matched': (watch.get('result') or {}).get('matched', False)
            if isinstance(watch.get('result'), dict) else False}
