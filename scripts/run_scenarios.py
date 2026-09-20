#!/usr/bin/env python3
"""Run the scenario corpus against the running chat and report the refusal rate.

    python3 scripts/run_scenarios.py
    python3 scripts/run_scenarios.py --group farmer
    python3 scripts/run_scenarios.py --json out.json

The number this exists to produce is the AVOIDABLE refusal rate. A refusal because a publisher has issued
nothing is the product working; a refusal because this product failed to fetch, failed to route, or
mishandled a window is a defect wearing the same clothes. Both look identical to a reader, which is why
they have to be told apart deliberately rather than counted together.

A scenario declares the outcomes that would be honest for it. 'answered' means facts came back;
'declined' means the engine said what it could not do; 'asked' means it needed one more thing before it
could; 'conversation' means it answered without reading a source, which is right for a greeting and wrong
for a forecast.
"""
import argparse, json, re, sys, time, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The harness talks to a RUNNING workspace, so a server started before an edit will happily
# report the behaviour that edit replaced. --base points it at a freshly started one.
BASE = 'http://127.0.0.1:8765'

# A decline whose sentence matches one of these is the publisher's gap, not ours.
UPSTREAM = re.compile(
    r'every day it publishes has already passed|carries no current facts|'
    r'covers \d{4}[-–]\d{4}|cannot supply|not a supported quantity|does not supply|'
    r'refresh failed|could not be verified|no station row came back|'
    r'needs a completed window|is not in the past|no published .* row', re.I)

# A refusal because nothing could exist - a date past the forecast horizon, a quantity no connected
# source carries - is honest in a third way: not the publisher's gap and not our defect, but the edge
# of what any product could answer. It is kept separate from the upstream bucket so that "we cannot"
# is never quietly filed as "they did not publish".
#
# These patterns read this product's own wording, which means they can be gamed by writing the phrase
# somewhere it does not belong. They are deliberately narrow for that reason, and a refusal that
# matches one should still state the limit concretely - naming the horizon, the date, the quantity.
PRODUCT_LIMIT = re.compile(
    r'limit of the product, not a failed request|no forecast for that date to retrieve|'
    r'is not a supported quantity in any connected source', re.I)

STATUS_TO_OUTCOME = {
    'answered': 'answered', 'partial': 'partial', 'stale': 'declined',
    'unavailable': 'declined', 'refused': 'declined', 'abstain': 'declined',
    'needs_selection': 'asked', 'needs_clarification': 'asked',
    'conversation': 'conversation',
}


def token():
    with urllib.request.urlopen(BASE + '/', timeout=20) as response:
        page = response.read().decode('utf-8', 'replace')
    found = re.search(r'name="workspace-token"[^>]*content="([^"]*)"', page)
    if not found:
        raise SystemExit('No workspace token; is the workspace running on 8765?')
    return found.group(1)


def ask(tok, question, timeout=180):
    request = urllib.request.Request(
        BASE + '/api/chat', data=json.dumps({'question': question}).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'X-WeatherGPT-Token': tok}, method='POST')
    began = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8', 'replace')), round(time.time() - began, 2)
    except urllib.error.HTTPError as error:
        return json.loads(error.read().decode('utf-8', 'replace') or '{}'), round(time.time() - began, 2)
    except Exception as error:
        return {'error': type(error).__name__ + ': ' + str(error)[:90]}, round(time.time() - began, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--base', default='http://127.0.0.1:8765', help='workspace base URL (default %(default)s)')
    parser.add_argument('--group')
    parser.add_argument('--json')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    globals()['BASE'] = args.base.rstrip('/')

    corpus = json.loads((ROOT / 'data/registry/chat-scenarios.json').read_text())['scenarios']
    if args.group:
        corpus = [s for s in corpus if s['group'] == args.group]
    tok = token()

    rows, counts = [], {'answered': 0, 'partial': 0, 'asked': 0, 'declined': 0, 'conversation': 0, 'error': 0}
    avoidable, honest, limits, mismatched = [], [], [], []

    for item in corpus:
        packet, seconds = ask(tok, item['q'])
        status = packet.get('status')
        outcome = STATUS_TO_OUTCOME.get(status, 'error' if packet.get('error') else 'declined')
        prose = str(packet.get('answer') or packet.get('error') or '')
        upstream = bool(UPSTREAM.search(prose))
        product_limit = bool(PRODUCT_LIMIT.search(prose))
        counts[outcome] = counts.get(outcome, 0) + 1
        ok = outcome in item['want'].split('|')
        if outcome == 'declined':
            bucket = limits if product_limit else honest if upstream else avoidable
            bucket.append((item['q'], prose[:110]))
        if not ok:
            mismatched.append((item['group'], item['q'], outcome, item['want'], prose[:90]))
        rows.append({'group': item['group'], 'q': item['q'], 'want': item['want'], 'outcome': outcome,
                     'status': status, 'upstream_gap': upstream, 'product_limit': product_limit,
                     'ok': ok, 'seconds': seconds,
                     'facts': len(packet.get('facts') or [])})
        if not args.quiet:
            print(f'{"ok " if ok else "OFF"} {item["group"][:11]:11} {outcome:12} {seconds:>6}s  {item["q"][:58]}')

    total = len(rows)
    declines = len(avoidable) + len(honest) + len(limits)
    print(f'\n{"="*72}\nscenarios: {total}   outcomes: ' +
          '  '.join(f'{k}={v}' for k, v in counts.items() if v))
    print(f'refusal rate: {declines}/{total} = {declines*100//max(total,1)}%'
          f'   of which upstream (publisher): {len(honest)}   product limit: {len(limits)}'
          f'   avoidable: {len(avoidable)}')
    print(f'expectation mismatches: {len(mismatched)}')

    if limits:
        print('\nHONEST LIMITS - nothing could answer these, and each says which limit it hit:')
        for q, why in limits:
            print(f'  - {q[:62]}\n      {why}')
    if avoidable:
        print('\nAVOIDABLE REFUSALS - these are ours to fix:')
        for q, why in avoidable:
            print(f'  - {q[:62]}\n      {why}')
    if mismatched:
        print('\nnot what the scenario expected:')
        for group, q, got, want, why in mismatched:
            print(f'  [{group}] {q[:56]}\n      got {got}, wanted {want} :: {why}')

    if args.json:
        Path(args.json).write_text(json.dumps(
            {'total': total, 'counts': counts, 'avoidable': len(avoidable), 'upstream': len(honest),
             'product_limit': len(limits), 'mismatched': len(mismatched), 'rows': rows}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
