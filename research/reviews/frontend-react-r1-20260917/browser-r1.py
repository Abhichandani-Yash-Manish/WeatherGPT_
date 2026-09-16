"""R1 browser acceptance: the React shell in a real Chrome, over the real server.

Run from the repository root:  .venv/bin/python research/reviews/frontend-react-r1-20260917/browser-r1.py
It serves a throwaway copy of the ingestion store with --frontend react, loads the page in headless Chrome
(--dump-dom for the DOM, a second run for the screenshot), and records what the page actually rendered.
"""
import json, os, re, shutil, subprocess, sys, threading, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import Workspace, make_server  # noqa: E402

CHROME = os.environ.get('WG_CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
HERE = Path(__file__).resolve().parent
SERVE_DIR = ROOT / 'tmp/r1-browser'
SERVE_DIR.mkdir(parents=True, exist_ok=True)
for stale in SERVE_DIR.glob('*'):
    stale.unlink()
shutil.copyfile(ROOT / 'data/runtime/ingestion/ingestion.sqlite', SERVE_DIR / 'ingestion.sqlite')

workspace = Workspace(database=SERVE_DIR / 'ingestion.sqlite', frontend='react')
server = make_server(workspace, 0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:%d' % server.server_port
record = {'batch': 'docs/88-overhaul-decisions-and-design-language.md', 'stage': 'R1 shell',
          'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'surface': 'headless Chrome against the loopback server serving web/dist, throwaway store copy',
          'checks': [], 'limits': ['One browser, one build, one machine: this is a render check, not layout, keyboard or screen-reader acceptance.']}


def chrome(*args, timeout=90):
    return subprocess.run([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-crashpad',
                           '--disable-breakpad', '--no-first-run', '--no-default-browser-check', *args],
                          capture_output=True, text=True, timeout=timeout)


try:
    with urllib.request.urlopen(base + '/', timeout=20) as response:
        html = response.read().decode()
        csp = response.headers.get('Content-Security-Policy')
    profile = Path('/tmp/wg-r1-dom'); shutil.rmtree(profile, ignore_errors=True); profile.mkdir(parents=True)
    dom = chrome('--user-data-dir=' + str(profile), '--dump-dom', base + '/').stdout
    profile2 = Path('/tmp/wg-r1-shot'); shutil.rmtree(profile2, ignore_errors=True); profile2.mkdir(parents=True)
    chrome('--user-data-dir=' + str(profile2), '--window-size=1440,900',
           '--screenshot=' + str(HERE / 'r1-shell-1440.png'), base + '/', timeout=120)
    record['checks'].append({'check': 'the_built_page_is_served_with_the_token', 'bytes': len(html),
                            'module_script': bool(re.search(r'<script type="module"', html)),
                            'inline_script': bool(re.search(r'<script(?![^>]*\bsrc=)[^>]*>[^<]', html)),
                            'style_attribute': 'style=' in html,
                            'csp_is_the_strict_policy': "style-src-attr" not in (csp or '') and "script-src 'self'" in (csp or '')})
    rail_entries = re.findall(r'data-view="([a-z-]+)"', dom)
    record['checks'].append({'check': 'the_shell_rendered_in_the_browser', 'dom_bytes': len(dom),
                             'react_shell': 'data-shell="react"' in dom,
                             'sky_attribute': re.search(r'data-sky="([a-z]+)"', dom).group(1) if re.search(r'data-sky="([a-z]+)"', dom) else None,
                             'rail_entries': len(rail_entries), 'rail_first': rail_entries[:5],
                             'question_box': 'id="question"' in dom,
                             'service_state': (re.search(r'data-testid="service-state"[^>]*>([^<]*)<', dom) or [None, None])[1],
                             'r1_note_present': 'arrive in R2' in dom,
                             'decorative_band_aria_hidden': bool(re.search(r'class="sky-band"[^>]*aria-hidden="true"', dom))})
finally:
    server.shutdown(); server.server_close()

(HERE / 'browser-r1.json').write_text(json.dumps(record, indent=2) + chr(10))
for check in record['checks']:
    print(json.dumps(check)[:400])
print('written', HERE / 'browser-r1.json')
