import json, sys, collections
def walk(entry):
    if isinstance(entry, dict) and 'data' in entry and isinstance(entry['data'], dict):
        return entry['data']
    return entry if isinstance(entry, dict) else {}
for path in sys.argv[1:]:
    record = json.load(open(path))
    data = walk(record)
    print('==', path.rsplit('/', 1)[-1], '| success', record.get('success'), '| url', data.get('url'))
    print('   counts:', json.dumps(data.get('counts'), sort_keys=True))
    for kind in ('violations', 'incomplete'):
        rows = data.get(kind) or []
        for v in rows:
            nodes = v.get('nodes') or []
            print('   ', kind, '|', v.get('id'), '|', v.get('impact'), '|', len(nodes), 'node(s) |', (v.get('help') or '')[:70])
            for n in nodes[:3]:
                print('        target:', (n.get('target') or ['?'])[0], '|', (n.get('failureSummary') or '').replace('\n', ' ')[:150])
