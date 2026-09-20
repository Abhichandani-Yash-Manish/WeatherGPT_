#!/usr/bin/env python3
"""Run the scenario atlas against the running chat and publish the refusal ledger.

    python3 scripts/run_atlas.py --base http://127.0.0.1:8791
    python3 scripts/run_atlas.py --group ctx_context --json out.json

The atlas (data/registry/chat-atlas.json) is the extensive cousin of chat-scenarios.json: every one of
the eight problem-statement features, the named use cases, multi-turn context behaviour and adversarial
boundaries, each scenario declaring the outcomes that would be HONEST for it. A correct decline is a
pass; a corpus that expects an answer to an unanswerable question teaches the wrong lesson.

The number this exists to produce is the AVOIDABLE refusal rate, split from the publisher's gap and
from the honest edge of what any product could answer (docs/117's runner established the three buckets;
this runner keeps them and adds multi-turn scenarios and per-scenario assertions).

Multi-turn scenarios share one conversation: assertions can require that a continuation kept the place
the previous turn resolved, which is the context-understanding property the atlas measures.
"""
import argparse, json, re, sys, time, urllib.request, urllib.error, uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8791'

# The three refusal buckets, kept identical in spirit to scripts/run_scenarios.py: the publisher's gap
# is the product working; the product limit is the honest edge; anything else is ours to fix.
UPSTREAM = re.compile(
    r'every day it publishes has already passed|carries no current facts|'
    r'covers \d{4}[-–]\d{4}|cannot supply|not a supported quantity|does not supply|'
    r'refresh failed|could not be verified|no station row came back|'
    r'needs a completed window|is not in the past|no published .* row|'
    r'has not issued|not issued|no current bulletin|could not retrieve verified evidence', re.I)

PRODUCT_LIMIT = re.compile(
    r'limit of the product, not a failed request|no forecast for that date to retrieve|'
    r'is not a supported quantity in any connected source|does not reach \d{2} \w+ \d{4}|'
    r'not an observed water level|not a gauge reading|sea-area bulletins are not connected|'
    r'not connected in this workspace|does not carry|outside.{0,20}days ahead', re.I)

STATUS_TO_OUTCOME = {
    'answered': 'answered', 'partial': 'partial', 'stale': 'declined',
    'unavailable': 'declined', 'refused': 'declined', 'abstain': 'declined',
    'needs_selection': 'asked', 'needs_clarification': 'asked',
    'conversation': 'conversation', 'outside_validity': 'declined',
}


def token():
    with urllib.request.urlopen(BASE + '/', timeout=20) as response:
        page = response.read().decode('utf-8', 'replace')
    found = re.search(r'name="workspace-token"[^>]*content="([^"]*)"', page)
    if not found:
        raise SystemExit('No workspace token; is the workspace running at ' + BASE + '?')
    return found.group(1)


def ask(tok, question, conversation_id=None, selection_id=None, timeout=180):
    body = {'question': question, 'request_id': uuid.uuid4().hex}
    if conversation_id:
        body['conversation_id'] = conversation_id
    if selection_id:
        body['selection_id'] = selection_id
    request = urllib.request.Request(
        BASE + '/api/chat', data=json.dumps(body).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'X-WeatherGPT-Token': tok}, method='POST')
    began = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', 'replace')), round(time.time() - began, 2)
    except urllib.error.HTTPError as error:
        try:
            return json.loads(error.read().decode('utf-8', 'replace') or '{}'), round(time.time() - began, 2)
        except Exception:
            return {'error': 'HTTP %s' % error.code}, round(time.time() - began, 2)
    except Exception as error:
        return {'error': type(error).__name__ + ': ' + str(error)[:90]}, round(time.time() - began, 2)


def short_place(packet):
    points = packet.get('resolved_points') or {}
    for entry in points.values():
        if isinstance(entry, dict) and entry.get('label'):
            return str(entry['label']).split(',')[0].strip().lower()
    for fact in packet.get('facts') or []:
        if fact.get('place'):
            return str(fact['place']).split(',')[0].split('·')[0].strip().lower()
    return ''


def check_assertions(spec, packet, previous):
    """A list of failed assertion descriptions; empty means every assertion held."""
    failures = []
    assertions = spec.get('assert') or {}
    answer = str(packet.get('answer') or '')
    facts = packet.get('facts') or []
    citations = packet.get('citations') or []
    if 'min_facts' in assertions and len(facts) < assertions['min_facts']:
        failures.append('expected at least %s facts, got %s' % (assertions['min_facts'], len(facts)))
    for needle in assertions.get('answer_contains') or []:
        if needle.lower() not in answer.lower():
            failures.append('answer does not contain %r' % needle)
    for needle in assertions.get('answer_not_contains') or []:
        if needle.lower() in answer.lower():
            failures.append('answer contains forbidden %r' % needle)
    for source in assertions.get('sources') or []:
        if not any(c.get('source_id') == source for c in citations):
            failures.append('no citation from source %s' % source)
    if assertions.get('same_place_as_previous') and previous is not None:
        before, now = short_place(previous), short_place(packet)
        if before and now and before != now:
            failures.append('place moved from %r to %r across a continuation' % (before, now))
    if assertions.get('status') and packet.get('status') != assertions['status']:
        failures.append('status %s, expected %s' % (packet.get('status'), assertions['status']))
    return failures


def run_scenario(tok, item, quiet):
    """One scenario is one or more turns over one conversation; the result rows are per turn."""
    conversation_id = None  # the first turn creates the conversation; the id comes from its response
    rows = []
    previous = None
    turns = item.get('turns') or [{'q': item['q'], 'want': item['want'], 'assert': item.get('assert')}]
    for index, turn in enumerate(turns):
        selection_id = None
        if turn.get('select') is not None and previous is not None:
            # A disambiguation turn: re-ask the previous question with one of the offered choices.
            choices = previous.get('choices') or []
            picked = None
            for choice in choices:
                if str(turn['select']).lower() in str(choice.get('label', '')).lower():
                    picked = choice
                    break
            if picked is None and choices:
                picked = choices[0]
            if picked is not None:
                selection_id = picked.get('selection_id')
                turn = {**turn, 'q': previous.get('question') or turn.get('q', '')}
        packet, seconds = ask(tok, turn['q'], conversation_id=conversation_id, selection_id=selection_id)
        conversation_id = packet.get('conversation_id') or conversation_id
        status = packet.get('status')
        outcome = STATUS_TO_OUTCOME.get(status, 'error' if packet.get('error') else 'declined')
        prose = str(packet.get('answer') or packet.get('error') or '')
        upstream = bool(UPSTREAM.search(prose))
        product_limit = bool(PRODUCT_LIMIT.search(prose))
        ok = outcome in str(turn.get('want', '')).split('|')
        assertion_failures = check_assertions(turn, packet, previous)
        if assertion_failures:
            ok = False
        rows.append({'id': item['id'], 'turn': index + 1, 'group': item['group'],
                     'feature': item.get('feature'), 'q': turn['q'], 'want': turn.get('want'),
                     'outcome': outcome, 'status': status, 'upstream_gap': upstream,
                     'product_limit': product_limit, 'ok': ok, 'seconds': seconds,
                     'facts': len(packet.get('facts') or []),
                     'assertion_failures': assertion_failures,
                     'answer_head': prose[:160]})
        if not quiet:
            mark = 'ok ' if ok else 'OFF'
            suffix = ' :: ' + '; '.join(assertion_failures)[:80] if assertion_failures else ''
            print('%s %-11s %-12s %6ss  %s%s' % (mark, item['group'][:11], outcome, seconds,
                                                 turn['q'][:56], suffix))
        previous = packet
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', default=BASE, help='workspace base URL (default %(default)s)')
    parser.add_argument('--group')
    parser.add_argument('--id', dest='only', action='append', help='run only this scenario id (repeatable)')
    parser.add_argument('--json')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    globals()['BASE'] = args.base.rstrip('/')

    atlas = json.loads((ROOT / 'data/registry/chat-atlas.json').read_text())['scenarios']
    if args.group:
        atlas = [s for s in atlas if s['group'] == args.group]
    if args.only:
        atlas = [s for s in atlas if s['id'] in set(args.only)]
    if not atlas:
        raise SystemExit('no scenarios matched')
    tok = token()

    rows = []
    for item in atlas:
        rows.extend(run_scenario(tok, item, args.quiet))

    counts = {}
    for row in rows:
        counts[row['outcome']] = counts.get(row['outcome'], 0) + 1
    declined = [r for r in rows if r['outcome'] == 'declined']
    avoidable = [r for r in declined if not r['upstream_gap'] and not r['product_limit']]
    honest = [r for r in declined if r['upstream_gap']]
    limits = [r for r in declined if r['product_limit']]
    mismatched = [r for r in rows if not r['ok']]

    total = len(rows)
    print('\n' + '=' * 72)
    print('turns: %d   outcomes: %s' % (total, '  '.join('%s=%s' % kv for kv in sorted(counts.items()))))
    print('refusal rate: %d/%d = %d%%   upstream (publisher): %d   product limit: %d   avoidable: %d'
          % (len(declined), total, len(declined) * 100 // max(total, 1), len(honest), len(limits), len(avoidable)))
    print('expectation mismatches: %d' % len(mismatched))

    if limits:
        print('\nHONEST LIMITS - nothing could answer these, and each says which limit it hit:')
        for row in limits:
            print('  - [%s] %s\n      %s' % (row['id'], row['q'][:62], row['answer_head'][:110]))
    if avoidable:
        print('\nAVOIDABLE REFUSALS - these are ours to fix:')
        for row in avoidable:
            print('  - [%s] %s\n      %s' % (row['id'], row['q'][:62], row['answer_head'][:110]))
    if mismatched:
        print('\nnot what the scenario expected:')
        for row in mismatched:
            why = '; '.join(row['assertion_failures'])[:90] if row['assertion_failures'] else row['answer_head'][:90]
            print('  [%s t%s] %s\n      got %s, wanted %s :: %s'
                  % (row['id'], row['turn'], row['q'][:56], row['outcome'], row['want'], why))

    if args.json:
        Path(args.json).write_text(json.dumps(
            {'base': BASE, 'ran_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
             'total_turns': total, 'counts': counts, 'avoidable': len(avoidable),
             'upstream': len(honest), 'product_limit': len(limits),
             'mismatched': len(mismatched), 'rows': rows}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
