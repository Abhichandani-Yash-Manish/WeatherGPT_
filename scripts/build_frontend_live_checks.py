#!/usr/bin/env python3
"""Rebuild the frontend live-check record from the recorded scans and readings.

    python3 scripts/build_frontend_live_checks.py

The accessibility figures are read from the axe-core scan files next to the record,
so the summary cannot outlive the scans it summarises. The viewport, surface and
capability readings are the ones measured in the batch and are declared here as
recorded measurements, not re-derived: re-measure them in a browser and update this
script in the same change. Nothing here launches a browser or a network request.
"""
import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AFTER = ROOT / 'research/reviews/frontend-v2-20260915/after'


def read_scans():
    scans = []
    for path in sorted(AFTER.glob('a11y-*.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        data = record.get('data') or {}
        theme, _, surface = path.stem.replace('a11y-', '').partition('-')
        counts = data.get('counts') or {}
        scans.append({'file': path.name, 'surface': surface, 'appearance': theme,
                      'violations': counts.get('violations'), 'passes': counts.get('passes'),
                      'incomplete': counts.get('incomplete'), 'inapplicable': counts.get('inapplicable'),
                      'rule_ids': sorted({row.get('id') for row in (data.get('violations') or [])})})
    return scans


def record():
    scans = read_scans()
    measurements = [
        ('1440x1200', 1440, 1200, 1062, 1200, 138, 0, 1363),
        ('768x1024', 768, 1024, 887, 1024, 137, 0, 1334),
        ('390x844', 390, 844, 674, 844, 170, 0, 1780),
    ]
    ends = [('1440x1200', 947, 1085, 163, 1363), ('768x1024', 775, 912, 310, 1334), ('390x844', 480, 650, 936, 1780)]
    return {
        'schema_version': 'frontend-live-checks-v1',
        'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
        'surface': 'desktop web at http://127.0.0.1:8790, Chrome 152.0.7977.83 over CDP (one browser, one machine)',
        'method': ("One reading per viewport: window.scrollTo(0, 0) or window.scrollTo(0, scrollHeight), then "
                   "document.querySelector('.composer').getBoundingClientRect() and getComputedStyle().position, "
                   "read through the browser CLI. One reading is one measurement, not a cross-browser, "
                   "screen-reader, device or load acceptance run."),
        'measurements': [
            {'viewport': name, 'inner_width': width, 'inner_height': height, 'position': 'sticky',
             'top_px': top, 'bottom_px': bottom, 'height_px': size, 'composer_in_first_viewport': True,
             'settled_on_viewport_bottom': bottom == height, 'scroll_y': scroll, 'document_scroll_height': document,
             'appearance': 'light'}
            for name, width, height, top, bottom, size, scroll, document in measurements],
        'document_end_measurements': [
            {'viewport': name, 'top_px': top, 'bottom_px': bottom, 'scroll_y': scroll,
             'settled_on_viewport_bottom': False, 'document_scroll_height': document,
             'note': 'At the end of the document the composer rests at the end of the ask desk and the colophon strip follows it.'}
            for name, top, bottom, scroll, document in ends],
        'surface_sweep': {
            'reading': 'each of the twelve surfaces opened by hash at 1440x1200; one visible surface each, no error wording',
            'views': ['overview', 'warnings', 'map', 'observations', 'forecast', 'changes', 'climate',
                      'advisories', 'aviation', 'marine', 'assistant', 'settings'],
            'visible_surface_each_time': True, 'held_or_failed_text_seen': False,
            'page_errors': 0, 'console_messages': 0},
        'capability_checks': {
            'command_palette': {'opened_from_rail_control': True, 'items': 17, 'groups': ['Surfaces', 'Actions'],
                                'query': 'surat', 'query_groups': ['Places', 'Recent conversations'], 'query_items': 2,
                                'place_match': 'Surat, Sūrat, State of Gujarāt · S61',
                                'recent_match': 'Will it rain in Surat, Gujarat tomorrow morning? · 2 asked',
                                'escape_closes': True},
            'appearance_control': {'modes': ['auto', 'light', 'dark'], 'applied_to_document': True,
                                   'cycle_reading': 'light -> dark -> System · day', 'stored_choice': 'weathergpt.theme'},
            'raw_packet_inspector': {'drawer_opened': True, 'characters': 6284, 'exact_packet_text': True,
                                     'states_it_is_not_a_summary': True},
            'map_selection': {'paths': 756, 'role': 'button', 'tabindex': '0',
                              'click_opens_drawer': 'SAITUAL, MIZORAM', 'enter_key_opens_drawer': 'SAITUAL, MIZORAM',
                              'find_patna_highlights': 1,
                              'day_switch_repaints': 'day 3: 273 yellow district polygons, 1 unmapped'},
            'ask_flow': {'question': 'Will it rain in Ahmedabad tomorrow morning?',
                         'first_turn': 'clarification naming two Ahmedabad candidates',
                         'second_turn': 'answered card, 0.0 mm, window 16 Sept 06:30-12:30 IST, one receipt, one ruler',
                         'source_named': 'S21 · Open-Meteo · GFS forecast delivery'}},
        'accessibility': {
            'tool': 'axe-core through the browser CLI (automated scan only)', 'scans': scans,
            'violations_total': sum((entry['violations'] or 0) for entry in scans),
            'note': ('incomplete entries are axe "could not determine" cases: text over a CSS gradient in the housing, '
                     'and glyph-only controls. An automated scan is not screen-reader or keyboard acceptance.')},
        'limits': [
            'One browser (Chrome 152) on one machine; no cross-browser, device, screen-reader, load or latency acceptance has been run.',
            'The composer is anchored to the bottom edge of the frame at the top of the document; at the very end of a document the ask desk ends and the colophon strip follows it.',
            'No forecast skill, calibration, accuracy or warning validity is measured here; the vintage-variance surface compares stored retrievals only.',
            'No native-speaker review exists for any output language; the appearance control and the palette are keyboard tested by component checks and this browser run only.',
            'Screenshots and measurements were taken against the local prototype server; hosting and sharing remain on hold.'],
    }


def main():
    path = AFTER / 'live-checks.json'
    payload = record()
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('wrote', path.relative_to(ROOT), '|', len(json.dumps(payload)), 'bytes')
    print('scans:', len(payload['accessibility']['scans']),
          '| violations:', payload['accessibility']['violations_total'])
    print('viewports:', ', '.join(m['viewport'] for m in payload['measurements']))


if __name__ == '__main__':
    main()
