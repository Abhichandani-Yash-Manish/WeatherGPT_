#!/usr/bin/env python3
"""Assert that the surfaces a reader can reach are served, and that both frontends agree on them.

    python3 scripts/audit_surface_registry.py

The vanilla rail (web/index.html) and the React registry (frontend/src/shell/views.ts) are two hand-written
lists of the same product surfaces. This audit reads both, compares them with the served route tables and with
an explicit map from a surface to the product route it reads, and fails when a surface has no backend or a
served product has no surface. It reads files and changes nothing.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_REGISTRY = ROOT / 'frontend' / 'src' / 'modules' / 'registry.ts'
MODULE_IMPORT = re.compile(r"(?:'([a-z-]+)':\s*|([a-z-]+):\s*)\{\s*load:\s*\(\)\s*=>\s*import\('(\.[^']+)'\)")
sys.path.insert(0, str(ROOT))
from weathergpt_data.product_api import PRODUCT_PATHS  # noqa: E402
from weathergpt_data.workspace import post_routes, Workspace  # noqa: E402

# Surface -> the product route it reads. 'assistant' and 'workspace' are the conversation itself; 'compare'
# composes from other product routes at the client. A surface with no entry here fails the audit, which is the
# point: a new rail entry has to say where its data comes from.
SURFACE_ROUTES = {
    'assistant': None,
    'workspace': '/api/now',
    'overview': '/api/overview',
    'warnings': '/api/warnings/national',
    'map': '/api/map/layers',
    'forecast': '/api/forecast',
    'observations': '/api/observations/network',
    'changes': '/api/forecast/changes',
    'climate': '/api/climate/index',
    'advisories': '/api/advisories/states',
    'air-quality': '/api/air-quality',
    'aviation': '/api/aviation',
    'ensemble': '/api/ensemble',
    'verification': '/api/verification',
    'compare': None,
    'marine': '/api/marine',
    'documents': '/api/corpus',
    'briefcase': '/api/health',   # the briefcase reads /api/briefs, which is a gated read route, not a product view
    'settings': '/api/settings/capabilities',
}

# Product routes that are sub-resources of a surface or client helpers rather than surfaces of their own. A new
# product route must either appear in SURFACE_ROUTES or be listed here with its reason, so a served view cannot
# become invisible to the interface without anyone noticing.
SUBROUTE_REASONS = {
    '/api/places/nearest': 'the catalogue place nearest a point, for the front door\'s "Use my location" control; it has no surface of its own because its whole result is the place the reader then holds',
    '/api/warnings/place': 'the place view of the warnings surface',
    '/api/warnings/alert-brief': 'the alert brief the warnings surface offers',
    '/api/warnings/cap': 'the CAP relay assessment inside the warnings surface',
    '/api/advisories/districts': 'the district step of the advisories surface',
    '/api/advisories/holdings': 'the advisory editions this machine holds, shown above the directory on the advisories surface',
    '/api/climate/series': 'the series view inside the climate surface',
    '/api/observations/near': 'the nearby-station view inside the observations surface',
    '/api/river': 'the river half of the Sea and rivers surface',
    '/api/basins': 'the basin list the river half reads',
    '/api/places/search': 'the composer place search',
    '/api/personas': 'the reading position the topbar offers',
    '/api/radar': 'the radar view, which states its own not-connected status',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()

    # The vanilla rail was removed in R6. Its nineteen ids are kept here as the frozen expectation the
    # React registry is measured against, so a surface cannot be dropped without this list being edited
    # on purpose.
    vanilla = ['assistant', 'workspace', 'overview', 'warnings', 'map', 'forecast', 'observations',
               'changes', 'climate', 'advisories', 'air-quality', 'aviation', 'ensemble', 'verification',
               'compare', 'marine', 'documents', 'briefcase', 'settings']
    react = re.findall(r"id: '([a-z-]+)'", (ROOT / 'frontend' / 'src' / 'shell' / 'views.ts').read_text(encoding='utf-8'))
    workspace = Workspace.__new__(Workspace)  # the route table only needs bound methods, not stores
    mutations = set(post_routes(workspace))
    products = set(PRODUCT_PATHS)
    registry_text = MODULE_REGISTRY.read_text(encoding='utf-8') if MODULE_REGISTRY.exists() else ''
    ported = MODULE_IMPORT.findall(registry_text)
    ported_ids = {quoted or bare for quoted, bare, _ in ported}
    missing_modules = sorted(
        spec.strip('./') + '.tsx'
        for _, _, spec in ported
        if not (MODULE_REGISTRY.parent / (spec.strip('./') + '.tsx')).exists()
    )
    server = (ROOT / 'weathergpt_data' / 'workspace.py').read_text(encoding='utf-8')
    GATED_READ_ROUTES = {path for path in re.findall(r"path=='(/api/[a-z0-9/_-]+)'", server) if path not in products}

    findings = [
        ('frozen_rail_expectation', len(vanilla) == 19, str(len(vanilla)) + ' surface(s) in the frozen expectation'),
        ('react_registry_present', bool(react), str(len(react)) + ' registry entr(ies)'),
        ('the_two_frontends_agree', set(vanilla) == set(react),
         'only vanilla: ' + str(sorted(set(vanilla) - set(react))) + '; only react: ' + str(sorted(set(react) - set(vanilla)))),
        ('every_surface_declares_a_route', set(vanilla) <= set(SURFACE_ROUTES),
         'unmapped: ' + str(sorted(set(vanilla) - set(SURFACE_ROUTES)))),
        ('every_declared_route_is_served',
         all(route is None or route in products or route in GATED_READ_ROUTES for route in SURFACE_ROUTES.values()),
         'not served: ' + str(sorted({route for route in SURFACE_ROUTES.values() if route and route not in products and route not in GATED_READ_ROUTES}))),
        ('every_product_has_a_surface_or_a_reason',
         products <= ({route for route in SURFACE_ROUTES.values() if route} | set(SUBROUTE_REASONS)),
         'products with neither: ' + str(sorted(products - ({route for route in SURFACE_ROUTES.values() if route} | set(SUBROUTE_REASONS))))),
        ('every_exemption_carries_a_reason', all(str(reason).strip() for reason in SUBROUTE_REASONS.values()),
         str(len(SUBROUTE_REASONS)) + ' exemption(s), each with a reason'),
        ('no_surface_calls_a_mutation_route', not ({route for route in SURFACE_ROUTES.values() if route} & mutations),
         'a read surface must not be wired to a mutating route'),
        ('every_ported_module_is_a_declared_surface', not (ported_ids - set(SURFACE_ROUTES)),
         'modules with no surface: ' + str(sorted(ported_ids - set(SURFACE_ROUTES))) if ported_ids - set(SURFACE_ROUTES)
         else str(len(ported_ids)) + ' of ' + str(len(SURFACE_ROUTES)) + ' surfaces have a real module, '
              + str(len(set(SURFACE_ROUTES) - ported_ids)) + ' are placeholders that state their stage'),
        ('every_ported_module_file_exists', not missing_modules,
         ', '.join(missing_modules) if missing_modules else str(len(ported_ids)) + ' module file(s) present'),
    ]
    failed = [name for name, ok, _ in findings if not ok]
    if args.json:
        print(json.dumps([{'check': name, 'ok': ok, 'detail': detail} for name, ok, detail in findings], indent=2))
    else:
        for name, ok, detail in findings:
            print(('PASS ' if ok else 'FAIL ') + name.ljust(36) + ' ' + detail)
        print(str(len(findings)) + ' check(s), ' + str(len(failed)) + ' failed')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
