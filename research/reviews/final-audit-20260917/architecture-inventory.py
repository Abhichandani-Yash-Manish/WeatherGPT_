"""Architecture inventory for the final integration audit: what exists, and what is wired to what.

Run from the repository root:  .venv/bin/python research/reviews/final-audit-20260917/architecture-inventory.py
It reads the code and the registries and prints what it found. It changes nothing and claims nothing: the
findings are the numbers, and the audit document interprets them.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.product_api import PRODUCT_PATHS  # noqa: E402
from weathergpt_data.capabilities import CAPABILITIES  # noqa: E402

inventory = {}


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


# Endpoints: the GET product routes, the GET known list and the POST route table.
server = read('weathergpt_data/workspace.py')
post_routes = re.findall(r"'(/api/[a-z0-9/_-]+)':workspace\.", server)
get_known = sorted(set(re.findall(r"path=='(/api/[a-z0-9/_-]+)'", server)))
get_products = sorted(PRODUCT_PATHS.keys()) if isinstance(PRODUCT_PATHS, dict) else sorted(PRODUCT_PATHS)
inventory['endpoints'] = {'product_get': get_products, 'other_get': get_known,
                          'post': sorted(set(post_routes))}

# Which endpoints appear anywhere in the Python tests.
tests_text = '\n'.join(p.read_text(encoding='utf-8') for p in (ROOT / 'tests').glob('test_*.py'))
# A route counts as referenced when a test names its path or the handler method behind it: the
# suite exercises handlers directly in many places, so a path-only measure overstates the gap.
handlers = dict(re.findall(r"'(/api/[a-z0-9/_-]+)':workspace\\.([a-z_]+)", server))
def referenced(path):
    if path in tests_text:
        return True
    handler = handlers.get(path)
    return bool(handler and re.search(r'\b' + re.escape(handler) + r'\b', tests_text))
inventory['endpoint_test_references'] = {path: referenced(path) for path in sorted(set(
    list(handlers) + inventory['endpoints']['other_get'] + inventory['endpoints']['product_get']))}

# Modules and their importers inside the package.
modules = sorted(p.stem for p in (ROOT / 'weathergpt_data').glob('*.py') if p.stem not in {'__init__', '__main__'})
package_text = '\n'.join(p.read_text(encoding='utf-8') for p in (ROOT / 'weathergpt_data').glob('*.py'))
script_text = '\n'.join(p.read_text(encoding='utf-8') for p in (ROOT / 'scripts').glob('*.py'))
test_text = tests_text
inventory['modules'] = {
    'count': len(modules),
    'imported_inside_package': sorted(m for m in modules if re.search(r'\b' + re.escape(m) + r'\b', package_text.replace('def ' + m, ''))),
    'imported_by_scripts': sorted(m for m in modules if re.search(r'\b' + re.escape(m) + r'\b', script_text)),
    'never_referenced_outside_itself': sorted(m for m in modules
                                              if not re.search(r'\b' + re.escape(m) + r'\b', package_text.replace('def ' + m, ''))
                                              and not re.search(r'\b' + re.escape(m) + r'\b', script_text)
                                              and not re.search(r'\b' + re.escape(m) + r'\b', test_text)),
}

# Frontend surfaces: the vanilla rail, the React registry, and the capabilities the engine publishes.
index = read('web/index.html')
vanilla = re.findall(r'data-view="([a-z-]+)"', index)
react = re.findall(r"id: '([a-z-]+)'", read('frontend/src/shell/views.ts'))
inventory['surfaces'] = {'vanilla_rail': vanilla, 'react_registry': react,
                         'only_in_vanilla': sorted(set(vanilla) - set(react)),
                         'only_in_react': sorted(set(react) - set(vanilla))}

# Capabilities the engine can answer, and the surfaces that claim them.
inventory['capabilities'] = {'tools': [c['tool'] for c in CAPABILITIES],
                             'kinds': sorted({c['kind'] for c in CAPABILITIES})}

# Source ledger.
ledger = json.loads(read('data/registry/source-review.json'))
rows = ledger.get('sources') or []
connector = lambda row: row.get('connector') or {}
inventory['sources'] = {'registered': len(rows),
                        'status_counts': ledger.get('counts') or {},
                        'connected': len([r for r in rows if connector(r).get('connected')]),
                        'wired_to_chat': len([r for r in rows if connector(r).get('wired_to_chat')]),
                        'blocked_access': len([r for r in rows if r.get('status') == 'blocked_access']),
                        'connector_kinds': ledger.get('connector_kinds') or {},
                        'flags_are_nested': True}

# Documents, registries, evidence.
inventory['docs'] = {'count': len(list((ROOT / 'docs').glob('*.md'))),
                     'latest': sorted(p.name for p in (ROOT / 'docs').glob('*.md'))[-4:]}
inventory['registry_files'] = sorted(p.name for p in (ROOT / 'data/registry').glob('*.json'))
inventory['evidence_dirs'] = sorted(p.name for p in (ROOT / 'research/reviews').iterdir() if p.is_dir())[-6:]
inventory['images'] = sorted(p.name for p in (ROOT / 'docs/images').glob('*.png'))

# Test inventory.
collected = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '--collect-only', '-q'], cwd=str(ROOT),
                           capture_output=True, text=True).stdout
match = re.search(r'(\d+) tests? collected', collected)
inventory['tests'] = {'python_collected': int(match.group(1)) if match else None,
                      'node_suites': len(list((ROOT / 'tests').glob('*.js'))) - 1,
                      'frontend_specs': len(list((ROOT / 'frontend/src').rglob('*.test.ts*')))}

print(json.dumps(inventory, indent=1)[:6000])
target = Path(__file__).resolve().parent / 'architecture-inventory.json'
target.write_text(json.dumps(inventory, indent=1) + chr(10))
print('written', target)
