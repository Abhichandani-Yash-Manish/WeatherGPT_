import json
for name in ('stage-sequence-a.json', 'stage-sequence-b.json'):
    path = 'research/reviews/refinement-20260915/' + name
    try:
        raw = open(path).read().strip()
    except OSError:
        print(name, 'missing'); continue
    if not raw:
        print(name, 'empty'); continue
    value = json.loads(raw)
    if isinstance(value, str):
        value = json.loads(value)
    stages, lines = [], 0
    for row in value:
        if row.get('stage') and row['stage'] not in stages:
            stages.append(row['stage'])
        if row.get('line'):
            lines += 1
    print(name, 'samples', len(value), '| stages', stages, '| rendered lines', lines)
    print('   last:', json.dumps(value[-1], ensure_ascii=False)[:180] if value else None)
body = open('research/reviews/refinement-20260915/second-turn-response.json').read()[:300]
print('second turn body:', body)
