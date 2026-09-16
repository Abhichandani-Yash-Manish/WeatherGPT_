#!/usr/bin/env python3
"""Audit the built React frontend the same way the served one is audited.

    python3 scripts/audit_react_build.py

The vanilla audit (`audit_workspace_frontend.py`) reads the served source files. This one reads the build
output, because that is what a browser receives: it checks the CSP-relevant properties of the built HTML, that
the session-token placeholder survives the build, that the manifest names files that exist, and that the entry
bundle stays inside a size budget. It reads files and changes nothing.

A missing build is reported as a skip, not a pass: the React surface is not the default until R6, and this
script must not make the gate depend on node.
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'web' / 'dist'
ENTRY_BUDGET_BYTES = 320_000  # gzip, R0 baseline measured at ~67 KB; the budget tightens per stage


def read(path):
    return path.read_text(encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='print the findings as JSON')
    args = parser.parse_args()

    index = DIST / 'index.html'
    findings = []
    if not index.exists():
        print('react build audit: SKIP - no build at ' + str(DIST.relative_to(ROOT)) +
              ' (build it with: cd frontend && npm run build)')
        return 0

    html = read(index)
    findings.append(('built_html_present', True, str(index.relative_to(ROOT))))

    inline_script = re.search(r'<script(?![^>]*\bsrc=)[^>]*>[^<]', html)
    findings.append(('no_inline_script', inline_script is None,
                     'inline script found' if inline_script else 'every script tag carries a src'))

    style_attribute = re.search(r'\sstyle\s*=', html)
    findings.append(('no_markup_style_attribute', style_attribute is None,
                     'markup style attribute found' if style_attribute else 'no style attribute in the built HTML'))

    external = re.findall(r'https?://[^"\'<> ]+', html)
    findings.append(('no_external_urls', not external, ', '.join(external) if external else 'nothing loaded off-origin'))

    token = '__WORKSPACE_TOKEN__' in html
    findings.append(('token_placeholder_survives', token,
                     'the server injects the session token into the built page' if token else
                     'the built page has no token placeholder: the token contract would break'))

    module_scripts = re.findall(r'<script[^>]*type="module"[^>]*src="([^"]+)"', html)
    findings.append(('module_entry_present', bool(module_scripts), ', '.join(module_scripts) or 'no module entry'))

    entry_files = []
    for src in module_scripts:
        target = (DIST / src.lstrip('/')).resolve()
        inside = DIST.resolve() in target.parents
        findings.append(('entry_exists:' + src, inside and target.exists(),
                         str(target.relative_to(ROOT)) if target.exists() else 'missing from disk'))
        if target.exists():
            entry_files.append(target)

    manifest_path = DIST / '.vite' / 'manifest.json'
    if manifest_path.exists():
        manifest = json.loads(read(manifest_path))
        named = [value.get('file') for value in manifest.values() if isinstance(value, dict) and value.get('file')]
        missing = [name for name in named if not (DIST / name).exists()]
        findings.append(('manifest_files_exist', not missing, ', '.join(missing) or str(len(named)) + ' manifest file(s) present'))
        entry = manifest.get('index.html', {})
        findings.append(('manifest_entry_matches_page', entry.get('file') in [s.lstrip('/') for s in module_scripts],
                         'manifest entry ' + str(entry.get('file')) + ' vs page ' + ', '.join(module_scripts)))
    else:
        findings.append(('manifest_present', False, 'no .vite/manifest.json: rebuild with the current vite config'))

    css = sorted(DIST.glob('assets/*.css'))
    external_css = []
    for sheet in css:
        external_css += re.findall(r'@import\s+url\(\s*["\']?https?://', read(sheet))
    findings.append(('no_external_css_imports', not external_css, ', '.join(external_css) or str(len(css)) + ' stylesheet(s) checked'))

    # The budget covers the initial graph, not just the entry file: a page that loads one small entry and
    # then pulls a large vendor chunk has not met a budget measured on the entry alone.
    budget_ok = True
    details = []
    initial = []
    if manifest_path.exists():
        queue = ['index.html']
        seen = set()
        while queue:
            key = queue.pop(0)
            if key in seen:
                continue
            seen.add(key)
            entry = manifest.get(key) or {}
            for name in ([entry.get('file')] if entry.get('file') else []) + list(entry.get('imports') or []):
                if name and name not in initial:
                    initial.append(name)
            queue.extend([name for name in (entry.get('imports') or []) if name.endswith('.js')])
    if not initial:
        initial = [entry_file.name for entry_file in entry_files]
    for name in initial:
        target = (DIST / name).resolve()
        if not target.exists() or target.suffix != '.js':
            continue
        raw = target.read_bytes()
        gzipped = len(gzip.compress(raw))
        details.append(target.name + ' ' + str(len(raw) // 1024) + ' KB raw, ' + str(gzipped // 1024) + ' KB gzip')
        if gzipped > ENTRY_BUDGET_BYTES:
            budget_ok = False
    total = sum(len(gzip.compress((DIST / name).read_bytes())) for name in initial if (DIST / name).exists())
    findings.append(('initial_bundle_within_budget', budget_ok,
                     '; '.join(details) + ' | total ' + str(total // 1024) + ' KB gzip (budget ' +
                     str(ENTRY_BUDGET_BYTES // 1024) + ' KB gzip for the whole initial graph)'))

    failed = [name for name, ok, _ in findings if not ok]
    if args.json:
        print(json.dumps([{'check': name, 'ok': ok, 'detail': detail} for name, ok, detail in findings], indent=2))
    else:
        for name, ok, detail in findings:
            print(('PASS ' if ok else 'FAIL ') + name.ljust(34) + ' ' + detail)
        print(str(len(findings)) + ' check(s), ' + str(len(failed)) + ' failed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
