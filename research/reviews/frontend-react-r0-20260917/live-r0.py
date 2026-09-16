"""R0 live check: the React build served by the workspace server, with the vanilla path still working.

Run from the repository root:  .venv/bin/python research/reviews/frontend-react-r0-20260917/live-r0.py
It starts two servers on ephemeral loopback ports - one serving the built bundle, one serving the legacy
frontend - and records what each actually answered: the page, its assets, the CSP header, the session token,
and what happens when the build is missing.
"""
import hashlib, json, re, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import REACT_CSP, STRICT_CSP, Workspace, make_server  # noqa: E402

DIST = ROOT / 'web' / 'dist'
record = {'batch': 'docs/86-react-frontend-overhaul-plan.md',
          'captured_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
          'stage': 'R0 groundwork', 'checks': [],
          'limits': ['One machine, one loopback server per mode, one build; this is not layout or accessibility acceptance.',
                     'The missing-build case is measured by moving the build aside for one request and restoring it.']}


def serve(frontend, port=0):
    server = make_server(Workspace(frontend=frontend), port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def fetch(base, path, token=None):
    headers = {'X-WeatherGPT-Token': token} if token else {}
    request = urllib.request.Request(base + path, headers=headers)
    began = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers), response.read(), round(time.monotonic() - began, 3)
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read(), round(time.monotonic() - began, 3)


react, react_thread = serve('react')
legacy, legacy_thread = serve('legacy')
try:
    base = 'http://127.0.0.1:' + str(react.server_port)
    status, headers, body, seconds = fetch(base, '/')
    html = body.decode()
    token = re.search(r'name="workspace-token" content="([^"]+)"', html)
    record['checks'].append({'check': 'the_react_build_is_served_at_root', 'http': status, 'seconds': seconds,
                             'content_type': headers.get('Content-Type'), 'bytes': len(body),
                             'token_injected': bool(token), 'token_is_not_the_placeholder': bool(token and token[1] != '__WORKSPACE_TOKEN__'),
                             'module_script': bool(re.search(r'<script type="module" crossorigin src="/assets/', html)),
                             'inline_script': bool(re.search(r'<script[^>]*>[^<]', html)),
                             'inline_style_attribute': 'style=' in html,
                             'external_urls': re.findall(r'https?://[^"\' ]+', html)})
    record['checks'].append({'check': 'the_page_policy_for_the_react_surface',
                             'csp': headers.get('Content-Security-Policy'),
                             'script_src_self': "script-src 'self'" in (headers.get('Content-Security-Policy') or ''),
                             'style_src_attr_relaxed': "style-src-attr 'unsafe-inline'" in (headers.get('Content-Security-Policy') or ''),
                             'style_src_still_self_only': "style-src 'self'" in (headers.get('Content-Security-Policy') or ''),
                             'cache_control': headers.get('Cache-Control')})
    assets = re.findall(r'/assets/[A-Za-z0-9._-]+', html)
    asset_rows = []
    for path in sorted(set(assets)):
        status, headers, body, seconds = fetch(base, path)
        local = DIST / path.removeprefix('/')
        asset_rows.append({'path': path, 'http': status, 'bytes': len(body), 'seconds': seconds,
                           'content_type': headers.get('Content-Type'), 'cache_control': headers.get('Cache-Control'),
                           'sha256_matches_disk': hashlib.sha256(body).hexdigest() == hashlib.sha256(local.read_bytes()).hexdigest() if local.exists() else None})
    record['checks'].append({'check': 'every_referenced_asset_is_served_and_matches_the_build', 'assets': asset_rows})
    manifest = json.loads((DIST / '.vite' / 'manifest.json').read_text())
    record['checks'].append({'check': 'the_build_manifest_names_the_entry', 'entry': list(manifest.keys()),
                             'files': {key: value.get('file') for key, value in manifest.items()}})

    missing = DIST / 'index.html'
    moved = DIST / 'index.html.r0-check'
    missing.rename(moved)
    try:
        status, headers, body, seconds = fetch(base, '/')
        record['checks'].append({'check': 'a_missing_build_is_refused_in_words', 'http': status,
                                 'content_type': headers.get('Content-Type'),
                                 'body': body.decode()[:200], 'blank_page': len(body.strip()) == 0})
    finally:
        moved.rename(missing)

    legacy_base = 'http://127.0.0.1:' + str(legacy.server_port)
    status, headers, body, seconds = fetch(legacy_base, '/')
    legacy_html = body.decode()
    record['checks'].append({'check': 'the_vanilla_frontend_still_serves_by_default', 'http': status,
                             'shell_script_referenced': '/shell.js' in legacy_html,
                             'csp': headers.get('Content-Security-Policy'),
                             'strict_policy_kept': headers.get('Content-Security-Policy') == STRICT_CSP,
                             'react_policy_not_leaked': "style-src-attr" not in (headers.get('Content-Security-Policy') or ''),
                             'token_injected': '__WORKSPACE_TOKEN__' not in legacy_html})
    status, headers, body, seconds = fetch(legacy_base, '/app.js')
    record['checks'].append({'check': 'the_vanilla_assets_still_serve', 'http': status, 'bytes': len(body),
                             'content_type': headers.get('Content-Type')})
finally:
    for server, thread in ((react, react_thread), (legacy, legacy_thread)):
        server.shutdown(); server.server_close(); thread.join(5)

target = Path(__file__).resolve().parent / 'live-r0.json'
target.write_text(json.dumps(record, indent=2) + chr(10))
for check in record['checks']:
    print(json.dumps(check)[:260])
print('written', target)
