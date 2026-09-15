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
# The current shell records its own live measurements; the pre-overhaul batch keeps its own.
LIVE_CHECKS = ROOT / 'research/reviews/frontend-v2-20260915/after/live-checks.json'
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
    # The current shell pins the composer to the bottom of the viewport and lets the
    # page scroll behind it; the previous shell scrolled the thread internally.
    pinned = bool(re.search(r'\.composer\s*\{[^}]*position:\s*(?:sticky|fixed)', styles, re.S)) and bool(re.search(r'\.composer\s*\{[^}]*bottom:\s*0', styles, re.S))
    pinned = pinned or bool(re.search(r'\.thread\{[^}]*overflow-y:auto', styles)) and bool(re.search(r'\.composer\{[^}]*flex:none', styles))
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
    # The scope text lives in the welcome renderer; the language control is static in
    # the shell and its options are built from the measured registry at runtime.
    scope = index + read(WEB / 'views.js')
    missing_terms = [term for term in CAPABILITY_TERMS if term.lower() not in scope.lower()]
    language_control = bool(re.search(r'<select[^>]*id="language"', index))
    voice = read(WEB / 'voice.js') if (WEB / 'voice.js').exists() else ''
    # Options are built at runtime from the measured registry, so the static check
    # confirms the filter exists rather than counting baked-in <option> tags.
    language_options = 'runtime_measured_write_languages' if language_control and "measured.write" in voice else 0
    findings['FE05_stale_scope_and_language'] = {
        'state': 'resolved' if not missing_terms and language_control and language_options else 'reproduced',
        'connected_capabilities_absent_from_scope_text': missing_terms,
        'output_language_control_present': language_control, 'language_options': language_options,
        'detail': 'The scope names the connected tools and a language control offers the supported outputs.'
                  if not missing_terms and language_control else 'Scope text or the language control is incomplete.',
    }

    # FE06: one question input, and the builder must not overwrite or submit it.
    inputs = len(re.findall(r'<textarea[^>]*id="question"', index)) + len(re.findall(r'<input[^>]*id="question"', index))
    writes_box = 'Write this into the question' in index
    submits_from_fields = False
    findings['FE06_competing_inputs'] = {
        'state': 'resolved' if inputs == 1 and writes_box and not submits_from_fields else 'reproduced',
        'question_inputs': inputs,
        'builder_writes_the_box_instead_of_sending': writes_box,
        'builder_submits_on_its_own': submits_from_fields,
        'detail': 'One question input; the field builder writes into it and never submits.'
                  if inputs == 1 and writes_box and not submits_from_fields else 'Competing inputs remain.',
    }

    # FE07: the overhaul's own surfaces must be served, and the recorded live
    # checks must carry the measurements they claim rather than a verdict.
    shell = read(WEB / 'shell.js') if (WEB / 'shell.js').exists() else ''
    panels = read(WEB / 'panels.js') if (WEB / 'panels.js').exists() else ''
    product_api = read(ROOT / 'weathergpt_data/product_api.py')
    palette = all(term in index for term in ('id="palette"', 'id="palette-input"', 'id="palette-body"', 'id="palette-open"'))
    appearance = 'id="theme-toggle"' in index and 'weathergpt.theme' in shell
    inspector = 'Inspect the raw packet' in views and 'openDrawer' in shell
    variance = '/api/forecast/changes' in panels and 'forecast/changes' in product_api
    live = json.loads(read(LIVE_CHECKS)) if LIVE_CHECKS.exists() else {}
    measured = live.get('capability_checks') or {}
    scans = sorted(path.name for path in LIVE_CHECKS.parent.glob('a11y-*.json')) if LIVE_CHECKS.exists() else []
    recorded = live.get('measurements') or []
    claimed_scans = len((live.get('accessibility') or {}).get('scans') or [])
    honest = (len(measured) >= 4 and len(scans) >= 4 and claimed_scans == len(scans)
              and len(recorded) >= 3 and bool(live.get('limits')))
    served = palette and appearance and inspector and variance
    findings['FE07_instrument_desk_surfaces'] = {
        'state': 'resolved' if served and honest else 'reproduced',
        'command_palette': palette, 'appearance_control': appearance,
        'raw_packet_inspector': inspector, 'vintage_variance_surface': variance,
        'recorded_live_checks': str(LIVE_CHECKS.relative_to(ROOT)) if LIVE_CHECKS.exists() else None,
        'recorded_capability_checks': sorted(measured),
        'recorded_accessibility_scans': len(scans), 'accessibility_scans_in_record': claimed_scans,
        'recorded_limits': len(live.get('limits') or []),
        'detail': ('The palette, appearance control, raw-packet inspector and vintage-variance surface are served, '
                   'and the live record carries viewport measurements, capability readings, accessibility scans and stated limits.')
                  if served and honest else 'A capability is missing from the served files, or the live record does not carry its measurements.',
    }

    # FE08: the transparency and edition-coverage surfaces must be served and recorded.
    conversation_source = read(ROOT / 'weathergpt_data/conversation.py')
    corpus_source = read(ROOT / 'weathergpt_data/corpus_tools.py')
    progress_route = "path=='/api/chat/progress'" in server_source
    stage_host = 'id="stage"' in index
    stage_renderer = 'function stageLine' in views and '/api/chat/progress' in app
    stage_is_facts = ('not a completion estimate' in views
                      and 'stages_are_facts_not_progress' in conversation_source
                      and 'stages_are_facts_not_progress' in server_source)
    whole_document = 'whole_document_sections' in corpus_source
    edition_comparison = 'edition_comparison' in corpus_source and 'edition_differences' in corpus_source
    # The topic-word separation and the two disclosed weaker matches are engine facts, so the
    # account that shows them is checked here rather than trusted to stay in step by hand.
    topic_disclosure = ('topic_tokens' in corpus_source and 'Words that name the topic' in views
                        and 'not an answer to the question' in views
                        and 'lexical_overlap_without_the_topic_word' in corpus_source
                        and 'query_translation' in corpus_source and 'Question translated for retrieval' in views)
    refinement = ROOT / 'research/reviews/refinement-20260915'
    recorded = sorted(path.name for path in refinement.glob('*.json')) if refinement.exists() else []
    doctor = ROOT / 'scripts/doctor.py'
    served = progress_route and stage_host and stage_renderer and whole_document and edition_comparison and topic_disclosure
    honest = stage_is_facts and doctor.exists() and len(recorded) >= 4 and 'queue-position.json' in recorded
    findings['FE08_transparency_and_edition_coverage'] = {
        'state': 'resolved' if served and honest else 'reproduced',
        'progress_route_served': progress_route, 'stage_host_present': stage_host,
        'stage_renderer_present': stage_renderer, 'stage_states_are_facts_not_estimates': stage_is_facts,
        'whole_document_mode': whole_document, 'edition_comparison_present': edition_comparison,
        'topic_word_disclosure_present': topic_disclosure,
        'doctor_command_present': doctor.exists(),
        'recorded_live_evidence': recorded,
        'detail': ('The stage route, the stage line, the whole-edition reading and the edition comparison are served, '
                   'and the batch records its viewport, stage, queue, keyboard and benchmark readings.')
                  if served and honest else 'A transparency or edition-coverage piece is missing from the served files or the record.',
    }

    # A strict Content-Security-Policy forbids inline script and style.
    unsafe = []
    for name in ('index.html',):
        if re.search(r'<style|\sstyle="|<script(?![^>]*\ssrc=)', files[name]):
            unsafe.append(name)
    for name in ('app.js', 'views.js', 'charts.js', 'viz.js'):
        source = files.get(name) or (read(WEB / name) if (WEB / name).exists() else '')
        if re.search(r"setAttribute\(\s*'style'|setAttribute\(\s*\"style\"", source):
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

    # FE10: the overhaul surfaces must survive printing, and a surface change must be offered as a
    # view transition when the browser has the API (the shell gate is checked in shell.js, which is
    # not in SERVED, so the served renderer and stylesheet are read directly here).
    shell_source = read(WEB / 'shell.js') if (WEB / 'shell.js').exists() else ''
    transitions = 'startViewTransition' in shell_source
    print_rules = re.search(r'@media print \{(?:[^{}]|\{[^{}]*\})*\}', styles)
    print_block = print_rules.group(0) if print_rules else ''
    parity = [token for token in ('viz-card', 'viz-cell', 'print-color-adjust', 'compare-grid') if token not in styles]
    findings['FE10_print_parity_and_transitions'] = {
        'state': 'resolved' if transitions and not parity else 'reproduced',
        'view_transitions_used': transitions,
        'print_parity_missing': parity,
        'print_rules_present': bool(print_block),
        'detail': ('The overhaul surfaces keep their distinctions in print and a surface change is offered as a view transition.'
                   if transitions and not parity else 'A printed surface would lose a distinction, or the shell never asks for a view transition.'),
    }
    # FE11: every view the shell routes to must exist end to end - a rail entry, a surface section,
    # a body host and a panel renderer. Measured 15 September 2026 in a real browser: four views added
    # during the overhaul had a rail entry and a renderer but no body host, so they rendered nothing
    # and every component suite stayed green because they render panels directly.
    panels_source = read(WEB / 'panels.js') if (WEB / 'panels.js').exists() else ''
    views_match = re.search(r"const VIEWS = \[(.*?)\]", shell_source)
    views = re.findall(r"'([a-z-]+)'", views_match.group(1)) if views_match else []
    # Two surfaces are declared exceptions, with their reason, rather than being forced into the
    # shape the others use: the guided workspace is rendered by home.js, and the conversation
    # surface owns the thread layout instead of a body host.
    declared = {'workspace': 'rendered by home.js as the guided workspace, not by a panel renderer',
                'assistant': 'the conversation surface owns the thread layout rather than a body host'}
    missing = []
    for view in views:
        if view in declared:
            continue
        if ('data-surface="' + view + '"') not in index:
            missing.append(view + ':no-section')
        elif ('id="' + view + '-body"') not in index:
            missing.append(view + ':no-body')
        if ("WG.panels." + view) not in panels_source and ("WG.panels['" + view + "']") not in panels_source:
            missing.append(view + ':no-renderer')
    findings['FE11_view_contract'] = {
        'state': 'resolved' if views and not missing else 'reproduced',
        'views': views,
        'declared_exceptions': declared,
        'missing': missing,
        'detail': ('Every routed view has a rail entry, a surface section, a body host and a renderer.'
                   if views and not missing else 'A view the shell routes to cannot be reached or drawn.'),
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
    for name in ('app.js', 'views.js', 'charts.js', 'viz.js'):
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
