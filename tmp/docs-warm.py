import json, pathlib, datetime
doc = pathlib.Path('docs/63-product-walkthrough.md')
t = doc.read_text()
anchor = '## What is still not product-grade'
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, "\n## The warm start: first answers are no longer the first read\n\nThe review's worst number was latency: the first right-now ask took 146 seconds and the first warning ask 67,\nbecause those layers were being read for the first time on the user's question. Two changes, both honest about\nwhat they are:\n\n1. **The server warms the slow layers once at startup** (`Workspace.start_warming()`, in a daemon thread;\n   `--no-warm` turns it off). It reads exactly what an ask would read, through the same governed adapters, and\n   records each layer with its own seconds, state and failure detail. Nothing is inferred from a warm-up.\n2. **The page warms the place it is working with** on load (`POST /api/warm`), so the first question about that\n   place reads warm cache rather than an empty one.\n\nMeasured on 15 September 2026 (`research/implementation/product-review-20260915/warm-start.json`,\n`page-warm-start.json`):\n\n| | Cold (before) | Warm (after) |\n|---|---|---|\n| First *what is it like right now in Ahmedabad?* | 146.2 s | **2.0-32.2 s** |\n| First *is any warning in force for Patna, Bihar today?* | 67.0 s | 46.7 s |\n\nThe honest reading of that table: warming removes most of the first-ask wait for the working place, and does not\nremove it everywhere - the warning ask for a *different* district still reads under a short cache lifetime, and a\ncold station read in the warm cycle itself took 26 s. Warming is a head start, not a promise, and the health view\nnow reports exactly what was warmed, when, and how long each layer took.\n" + anchor, 1)
lines = t.splitlines(keepends=True)
for index, line in enumerate(lines):
    if line.startswith('- **Cold-start latency.**'):
        lines[index] = ('- **Cold-start latency, improved but not gone.** Warming the working place takes the first right-now ask from 146 s to 2-32 s; a warning ask for a different district still reads under a short cache lifetime.\n')
        break
t = ''.join(lines)
doc.write_text(t)
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
h = pathlib.Path('data/registry/hardening-progress.json')
d = json.loads(h.read_text())
batch = d['product_review_batch']
batch['measured']['warm_start'] = {'first_right_now_ask_cold_seconds': 146.2, 'first_right_now_ask_warm_seconds': 2.0,
                                   'first_warning_ask_cold_seconds': 67.0, 'first_warning_ask_warm_seconds': 46.7,
                                   'station_layers_warm_seconds': 26.2, 'route': 'POST /api/warm', 'flag': '--no-warm disables the startup read'}
batch['limitations'] = ['Warming is a head start, not a promise: a different district or an expired cache still reads cold.',
                        'Corpus coverage is uneven by family: 571 district agromet, five state editions, one edition per national product.',
                        'Radar and satellite imagery, sea-area and coastal bulletins, flood extent and delivery remain unconnected.',
                        'No native-speaker review; no mobile or screen-reader acceptance; no valid OpenRouter key call yet.']
batch['automated_tests'] = 864
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
readme = pathlib.Path('README.md')
rt = readme.read_text()
assert rt.count('# 860 Python tests') == 1
readme.write_text(rt.replace('# 860 Python tests', '# 864 Python tests', 1))
print('warm start documented, latency line updated, count set')