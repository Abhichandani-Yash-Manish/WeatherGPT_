"""R0 CSP probe: does the served policy block the style attributes these libraries need?

Run from the repository root:  .venv/bin/python research/reviews/frontend-react-r0-20260917/csp-probe.py
It serves the built probe page twice - once under the strict page policy the workspace already uses and once
under the policy that was *proposed* for the React surface - loads each in headless Chrome with --dump-dom,
and reads the page's own measurement: the computed style each library ended up with, and every CSP violation
the document reported. Chrome is invoked directly rather than through a CDP client, because a driver that
reports a timeout would be indistinguishable from a page that never rendered.
"""
import json, os, re, shutil, subprocess, sys, threading, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import STRICT_CSP  # noqa: E402

CHROME = os.environ.get('WG_CHROME', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
HERE = Path(__file__).resolve().parent
PORT = 8798
PROPOSED_CSP = STRICT_CSP.replace("style-src 'self';", "style-src 'self'; style-src-attr 'unsafe-inline';")

server = subprocess.Popen([sys.executable, str(HERE / 'serve-probe.py')], stdout=subprocess.PIPE, text=True)
for _ in range(40):
    try:
        urllib.request.urlopen('http://127.0.0.1:%d/probe.html' % PORT, timeout=1).read(64)
        break
    except Exception:
        time.sleep(0.25)

record = {'batch': 'docs/87-frontend-research-and-inspiration.md', 'stage': 'R0 groundwork',
          'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'probe_page': 'web/dist/probe.html (development entry, not a product surface)',
          'libraries': ['@radix-ui/react-popover', '@tanstack/react-virtual', 'motion'],
          'method': ('Chrome --dump-dom per policy, in a fresh profile; the page measures itself and reports the '
                     'computed style, because a blocked inline style is ignored by the engine while its attribute '
                     'stays in the DOM. Violations are collected from module scope, before React mounts.'),
          'variants': {},
          'limits': ['One Chrome, one build, one machine; directives are reported as this Chrome reported them.',
                     'The probe measures whether a style attribute is honoured, not how a library degrades when it is not.']}


def dump(policy):
    profile = Path('/tmp/wg-csp-' + policy)
    shutil.rmtree(profile, ignore_errors=True)
    profile.mkdir(parents=True, exist_ok=True)
    out = subprocess.run([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-crashpad',
                          '--disable-breakpad', '--no-first-run', '--no-default-browser-check',
                          '--user-data-dir=' + str(profile), '--dump-dom',
                          'http://127.0.0.1:%d/probe.html?csp=%s' % (PORT, policy)],
                         capture_output=True, text=True, timeout=120).stdout
    return out


try:
    for policy, label in (('strict', 'current_strict_policy'), ('react', 'proposed_attribute_policy')):
        dom = dump(policy)
        block = re.search(r'data-probe="findings">(.*?)</pre>', dom, re.S)
        findings = None
        if block:
            try:
                findings = json.loads(block.group(1).replace('&quot;', chr(34)))
            except ValueError:
                findings = {'unparsed': block.group(1)[:200]}
        report_file = HERE / ('csp-report-' + policy + '.json')
        posted = None
        for _ in range(20):
            if report_file.exists():
                try:
                    posted = json.loads(report_file.read_text()); break
                except ValueError:
                    time.sleep(0.25)
            time.sleep(0.25)
        applied = {row.get('component'): {'style_attribute_present': row.get('styleAttributePresent'),
                                          'computed': row.get('computed'), 'applied': row.get('applied')}
                   for row in (findings or {}).get('findings', [])} if isinstance(findings, dict) else None
        profile = Path('/tmp/wg-csp-shot-' + policy); shutil.rmtree(profile, ignore_errors=True); profile.mkdir(parents=True)
        subprocess.run([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--disable-crashpad',
                        '--disable-breakpad', '--no-first-run', '--no-default-browser-check',
                        '--user-data-dir=' + str(profile), '--window-size=1440,900',
                        '--screenshot=' + str(HERE / ('csp-probe-' + policy + '.png')),
                        'http://127.0.0.1:%d/probe.html?csp=%s' % (PORT, policy)], capture_output=True, timeout=120)
        record['variants'][label] = {'url': 'http://127.0.0.1:%d/probe.html?csp=%s' % (PORT, policy),
                                     'csp_header': STRICT_CSP if policy == 'strict' else PROPOSED_CSP,
                                     'applied': applied,
                                     'violations_reported_by_the_page': (findings or {}).get('violations') if isinstance(findings, dict) else None,
                                     'posted_report': bool(posted), 'dom_bytes': len(dom)}
finally:
    server.terminate()
    try: server.wait(timeout=10)
    except subprocess.TimeoutExpired: server.kill()

(HERE / 'csp-probe.json').write_text(json.dumps(record, indent=2) + chr(10))
for label, variant in record['variants'].items():
    print(label, '->', json.dumps(variant['applied'])[:280])
    print('   violations:', json.dumps(variant['violations_reported_by_the_page'])[:160], '| posted:', variant['posted_report'])
print('written', HERE / 'csp-probe.json')
