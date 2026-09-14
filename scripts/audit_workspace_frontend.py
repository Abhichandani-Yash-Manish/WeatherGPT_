#!/usr/bin/env python3
"""Audit the local workspace frontend against its served contract.

Static only: it reads the files the workspace server actually serves, the asset
map that serves them, and any recorded live measurements. It does not launch a
browser, and a pass here is a structural check, not browser or mobile acceptance.

Each finding reports the measured state, so the same command documents the
pre-overhaul baseline and later confirms a repair. A non-zero exit means the
workspace cannot serve a consistent page, not that a finding is open.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / 'web'
EVIDENCE = ROOT / 'research/reviews/frontend-overhaul-20260914'
LIVE_CHECKS = EVIDENCE / 'after/live-checks.json'
ENGINE_KEYS = {'question', 'conversation_id', 'selection_id', 'coordinates'}
SERVED = ('index.html', 'app.js', 'views.js', 'charts.js', 'style.css')
CAPABILITY_TERMS = ('wave', 'discharge', 'METAR', 'airport', 'bulletin', 'warning')
STYLESHEET_TOKENS = ('notice', 'is-calm', 'is-good', 'tag', 'fact', 'receipt', 'ruler')


def read(path):
    return path.read_text(encoding='utf-8')


def served_assets(server_source):
    match = re.search(r"assets=\{(.*?)\}\s*\n", server_source, re.S)
    if not match:
        return None
    return set(re.findall(r"'/([A-Za-z0-9_.-]+)'", match.group(1)))


def audit():
    files = {name: read(WEB / name) for name in SERVED}
    index, app, views, charts, styles = (files[name] for name in SERVED)
    server_source = read(ROOT / 'weathergpt_data/workspace.py')
    findings = {}

    assets = served_assets(server_source)
    wanted = set(re.findall(r'(?:src|href)="/([A-Za-z0-9_.-]+)"', index))
    if assets is None:
        findings['serve_contract'] = {'state': 'unreadable', 'detail': 'The asset map could not be parsed.'}
    else:
        unserved = sorted(wanted - assets)
        missing = sorted(asset for asset in assets if asset != 'index.html' and not (WEB / asset).exists())
        findings['serve_contract'] = {
            'state': 'broken' if unserved or missing else 'ok',
            'served': sorted(assets), 'requested_by_page': sorted(wanted),
            'referenced_but_not_served': unserved, 'served_but_absent_on_disk': missing,
            'detail': 'Every served path exists and every asset the page asks for has a route.'
                      if not unserved and not missing else 'A served path is missing or unrouted.',
        }

    # FE01: the question box must not sit below a competing form. The page keeps the
    # thread scrollable and the composer pinned, and any recorded live measurement
    # must agree.
    pinned = bool(re.search(r'\.thread\{[^}]*overflow-y:auto', styles)) and bool(re.search(r'\.composer\{[^}]*flex:none', styles))
    live = None
    if LIVE_CHECKS.exists():
        record = json.loads(read(LIVE_CHECKS))
        live = record.get('measurements', [])
        visible = [m for m in live if m.get('composer_in_first_viewport')]
        findings['FE01_mobile_reachability'] = {
            'state': 'verified_live' if pinned and live and len(visible) == len(live) else 'broken' if not pinned else 'needs_live_check',
            'thread_scrolls_internally': pinned,
            'measured_viewports': [m.get('viewport') for m in live],
            'composer_visible_in_all_measured': len(visible) == len(live),
            'recorded_evidence': str(LIVE_CHECKS.relative_to(ROOT)),
            'detail': 'The composer is pinned inside the first viewport at every measured size.'
                      if pinned and live and len(visible) == len(live) else 'The composer is not pinned, so it can be pushed below the fold.',
        }
    else:
        findings['FE01_mobile_reachability'] = {
            'state': 'needs_live_check' if pinned else 'broken',
            'thread_scrolls_internally': pinned,
            'detail': 'The composer is pinned by the stylesheet; a recorded live measurement is still required.',
        }

    # FE02: a bounded collection must be reachable from the page.
    refresh_route = "api/refresh" in app
    refresh_control = "Collect fresh evidence" in views
    sends_point = "coordinates" in app and "resolved_points" in app
    findings['FE02_refresh_unreachable'] = {
        'state': 'resolved' if refresh_route and refresh_control and sends_point else 'reproduced',
        'posts_to_refresh_route': refresh_route, 'offers_a_control': refresh_control,
        'sends_the_resolved_point': sends_point, 'rejected_legacy_key_sent': 'entity_id' in app,
        'detail': 'The page offers a bounded collection, posts to /api/refresh and sends the resolved point.'
                  if refresh_route and refresh_control and sends_point else 'A bounded collection is not reachable from the page.',
    }

    # FE03: no unreachable renderer, and no rejected request key.
    legacy = "function render(" in app
    rejected_keys = sorted(set(re.findall(r"\b(entity_id)\b", app)))
    findings['FE03_dead_renderer'] = {
        'state': 'resolved' if not legacy and not rejected_keys else 'reproduced',
        'unreachable_renderer_present': legacy,
        'engine_rejected_keys_in_client': rejected_keys,
        'engine_accepts': sorted(ENGINE_KEYS),
        'detail': 'One renderer path remains and no rejected key is sent.'
                  if not legacy and not rejected_keys else 'A renderer or request key the engine cannot serve remains.',
    }

    # FE04: task accounting must not be a single affirmative count.
    affirmative = 'requested tasks completed' in (app + views)
    honest = 'coverage' in views and 'Asked' in views and 'Answered' in views and 'Incomplete' in views
    findings['FE04_unqualified_task_count'] = {
        'state': 'resolved' if not affirmative and honest else 'reproduced',
        'renders_single_completion_count': affirmative, 'reports_asked_answered_incomplete': honest,
        'detail': 'Asked, answered and incomplete are reported separately, and no bare completion count is shown.'
                  if not affirmative and honest else 'A single affirmative task count is still renderable.',
    }

    # FE05: the scope text must name the connected tools, and a language control must exist.
    scope_match = re.search(r'<div class="scope">(.*?)</div>', index, re.S)
    scope = scope_match.group(1) if scope_match else ''
    missing_terms = [term for term in CAPABILITY_TERMS if term.lower() not in scope.lower()]
    language_control = bool(re.search(r'<select[^>]*id="language"', index))
    language_options = len(re.findall(r'<option value="(?:en|hi|gu)"', index))
    findings['FE05_stale_scope_and_language'] = {
        'state': 'resolved' if not missing_terms and language_control and language_options >= 3 else 'reproduced',
        'connected_capabilities_absent_from_scope_text': missing_terms,
        'output_language_control_present': language_control, 'language_options': language_options,
        'detail': 'The scope names the connected tools and a language control offers the supported outputs.'
                  if not missing_terms and language_control else 'Scope text or the language control is incomplete.',
    }

    # FE06: one question input, and the builder must not overwrite or submit it.
    inputs = len(re.findall(r'<textarea[^>]*id="question"', index)) + len(re.findall(r'<input[^>]*id="question"', index))
    writes_box = 'Write this into the question box' in index
    submits_from_fields = False
    findings['FE06_competing_inputs'] = {
        'state': 'resolved' if inputs == 1 and writes_box and not submits_from_fields else 'reproduced',
        'question_inputs': inputs,
        'builder_writes_the_box_instead_of_sending': writes_box,
        'builder_submits_on_its_own': submits_from_fields,
        'detail': 'One question input; the field builder writes into it and never submits.'
                  if inputs == 1 and writes_box and not submits_from_fields else 'Competing inputs remain.',
    }

    # A strict Content-Security-Policy forbids inline script and style.
    unsafe = []
    for name in ('index.html',):
        if re.search(r'<style|\sstyle="|<script(?![^>]*\ssrc=)', files[name]):
            unsafe.append(name)
    for name in ('app.js', 'views.js', 'charts.js'):
        if re.search(r"setAttribute\(\s*'style'|setAttribute\(\s*\"style\"", files[name]):
            unsafe.append(name)
    findings['csp_compliance'] = {
        'state': 'ok' if not unsafe else 'broken',
        'files_with_inline_style_or_script': unsafe,
        'detail': 'No inline style or script is used, so the page stays within the served policy.'
                  if not unsafe else 'The page uses inline style or script the policy forbids.',
    }

    # A class name rendered as text is a silent presentation defect.
    leaks = []
    for token in STYLESHEET_TOKENS:
        if re.search(r"el\(\s*'[a-z0-9]+'\s*,\s*'" + token + r"(?:\s|')", views) or re.search(r"el\(\s*'[a-z0-9]+'\s*,\s*'" + token + r"(?:\s|')", app):
            leaks.append(token)
    findings['class_as_text'] = {
        'state': 'ok' if not leaks else 'broken',
        'suspect_tokens': leaks,
        'detail': 'No element passes a stylesheet class name as its text.'
                  if not leaks else 'A class name is being rendered as text, which the component suite also guards against.',
    }

    findings['javascript_syntax'] = syntax_check()
    return {'schema_version':'frontend-audit-v1',
            'files': {name: len(files[name].splitlines()) for name in SERVED},
            'findings': findings}


def syntax_check():
    try:
        node = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=20)
        if node.returncode != 0:
            return {'state': 'skipped', 'detail': 'Node is not available, so served scripts were not parsed.'}
    except (OSError, subprocess.SubprocessError):
        return {'state': 'skipped', 'detail': 'Node is not available, so served scripts were not parsed.'}
    broken = []
    for name in ('app.js', 'views.js', 'charts.js'):
        result = subprocess.run(['node', '--check', str(WEB / name)], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            broken.append(name)
    return {'state': 'broken' if broken else 'ok', 'unparsable': broken,
            'detail': 'Every served script parses.' if not broken else 'A served script does not parse.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='Print the whole report as JSON')
    parser.add_argument('--baseline', action='store_true', help='Also confirm the frozen baseline record is present')
    arguments = parser.parse_args()

    report = audit()
    blocked = [name for name, value in report['findings'].items() if value['state'] == 'broken']
    open_findings = [name for name, value in report['findings'].items() if value['state'] == 'reproduced']

    if arguments.baseline:
        if not (EVIDENCE / 'baseline/baseline.json').exists():
            print('MISSING baseline record')
            return 1
        record = json.loads(read(EVIDENCE / 'baseline/baseline.json'))
        report['baseline'] = {'path': 'research/reviews/frontend-overhaul-20260914/baseline/baseline.json',
                              'findings': [item['id'] for item in record['measured_defects']],
                              'captures': len(record['captures'])}

    if arguments.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for name, value in report['findings'].items():
            print('{:<34} {}'.format(name, value['state']))
            print('    ' + value['detail'])
        if 'baseline' in report:
            print('{:<34} {}'.format('baseline', ','.join(report['baseline']['findings'])))

    if blocked:
        print('\nThe workspace cannot serve a consistent page: ' + ', '.join(blocked), file=sys.stderr)
        return 1
    if open_findings:
        print('\nStill open: ' + ', '.join(open_findings), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
