import json
path = 'research/reviews/refinement-20260915/stage-samples.txt'
rows = []
for line in open(path):
    line = line.strip()
    if not line:
        continue
    value = json.loads(line)
    if isinstance(value, str):
        value = json.loads(value)
    rows.append(value)
print('samples:', len(rows))
stages, lines, seen = [], [], []
for row in rows:
    if row.get('stage') and row['stage'] not in stages:
        stages.append(row['stage'])
    if row.get('seen'): seen = row['seen']
    if row.get('line'): lines.append(row['line'])
print('distinct stages observed:', stages)
print('last stages_seen:', seen)
print('samples with a rendered stage line:', len(lines), 'of', len(rows))
print('first rendered line:', lines[0] if lines else None)
print('waiting queue samples:', sum(1 for row in rows if row.get('waiting')))
print('percent or ETA in any line:', any('%' in (row.get('line') or '') or 'ETA' in (row.get('line') or '') for row in rows))
print('last sample:', json.dumps(rows[-1], ensure_ascii=False)[:200])
