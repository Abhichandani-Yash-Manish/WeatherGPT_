import json, pathlib, datetime

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
TICK = chr(96)

round3 = """

## Round 3 — WS4: two products in one answer, compared and never ranked

The product answered one task at a time. A person asking "will it rain tomorrow, and is there a
warning?" got two blocks stapled together and had to reconcile them; nothing said where the
official product and the model forecast agreed or disagreed, and the planner could not even
plan both questions from one sentence.

| Landed | Where | Evidence |
|---|---|---|
| Compound questions are planned clause by clause: a question with two requests becomes two tasks, and a clause that names no place of its own is read as being about the place the question named | weathergpt_data/rule_planner.py | tests/test_providers.py - compound planning and the inherited place; a two-place question is left to a model rather than silently shortened |
| A deterministic comparison of the products a turn actually retrieved: official district warning days against model forecast facts, and a published rain statement against the forecast | weathergpt_data/comparison.py | tests/test_comparison.py - nine checks: consistent, differ, a quiet day (never compared as no rain), a hazard the forecast does not measure, non-overlapping windows, a bulletin-versus-forecast pair, the four-item cap, and the absence of any score, confidence or all-clear language |
| The comparison is part of the answer: a sentence in the answer text, a "Products compared" block rendered in the open, and the structured items in the packet for the receipt | weathergpt_data/conversation.py, web/views.js | tests/test_views.js - the block names both source ids, the reading and the refusal to rank; live journey below |

### The live journey

Question: "Will it rain in Patna, Bihar tomorrow, and is there any warning?"

- Planned as two tasks by rules: forecast/lookup and warning/lookup, both on Patna.
- Task 1 answered: Patna, 16 Sep, 00:30-17 Sep 00:30 IST, forecast precipitation 0.0-0.5 mm, source S21.
- Task 2 answered: IMD district warning for PATNA, bulletin of 15 Sep 2026 05:30 IST, day 1
  yellow - Thunderstorm/lightning/squall, with the CAP relay assessment and its limits.
- **Products compared (1)**: Patna, 16 Sep 2026 - S15 IMD district warning product
  (yellow - Thunderstorm/lightning/squall) and S21 Model forecast (rainfall 0.5 mm across 2
  forecast values); reading **consistent** - both name rain in this window; and the standing
  note that both products are named, neither is ranked, a comparison is not a score or a skill
  measurement, and a quiet day is not a forecast of no rain.

Evidence: research/implementation/product-comparison-20260915/ - the rendered block, the full
answer, and the packet readings. A duplicate question in the same conversation produced a stored
turn, which is what the rail shows.

### What this does and does not establish

- It establishes that two different products can speak about the same window in one answer, that
  the agreement or disagreement is stated in words the reader can check, and that no score,
  ranking, confidence or all-clear is produced from a comparison.
- It does not establish which product is right, and it never will: the official product speaks
  about warnings, the model forecast about modelled values, and the comparison says so.
- The comparison only runs when a turn retrieved at least two of these products. A single-product
  answer carries no comparison, which is correct and tested.
- Nothing here closes the alert journey (WS5) or the PS coverage matrix: it is one workstream step.
"""
path = pathlib.Path('docs/49-engine-architecture-and-gap-analysis.md')
path.write_text(path.read_text(encoding='utf-8').rstrip(chr(10)) + chr(10) + round3, encoding='utf-8')
print('docs/49 round 3 recorded:', 'Round 3' in path.read_text())

h_path = pathlib.Path('data/registry/hardening-progress.json')
h = json.loads(h_path.read_text())
h['product_comparison_batch'] = {
    'report': 'docs/49-engine-architecture-and-gap-analysis.md',
    'evidence_directory': 'research/implementation/product-comparison-20260915',
    'operational_ready': False,
    'scope': ('Cross-product comparison in one answer (official district warning days against model forecast facts, and a published '
              'rain statement against the forecast), clause-by-clause planning of compound questions with place inheritance, and a '
              'rendered comparison block that names both products and refuses to rank them.'),
    'automated_tests': 705,
    'javascript_component_checks': 61,
    'measured': {
        'live_journey': {'question': 'Will it rain in Patna, Bihar tomorrow, and is there any warning?',
                         'tasks': ['forecast/lookup', 'warning/lookup'],
                         'comparison_items': 1,
                         'reading': 'consistent',
                         'products': ['S15 IMD district warning product', 'S21 Model forecast']},
        'comparison_readings_supported': ['consistent', 'differ', 'not_comparable'],
        'quiet_day_compared': False,
        'score_or_confidence_produced': False,
    },
    'limitations': [
        'The comparison states agreement or disagreement; it never decides which product is right.',
        'It runs only when one turn retrieves two comparable products; a single-product answer carries none.',
        'No live bulletin-versus-forecast comparison has been recorded yet; that path is pinned by component checks only.',
    ],
}
h['updated_at_utc'] = now
h_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')

p_path = pathlib.Path('data/registry/product-progress.json')
p = json.loads(p_path.read_text())
p['as_of_utc'] = now
p['latest_batch'] = 'docs/49-engine-architecture-and-gap-analysis.md'
p_path.write_text(json.dumps(p, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')

readme = pathlib.Path('README.md')
text = readme.read_text()
text = text.replace('# 694 Python tests', '# 705 Python tests')
text = text.replace("- **Desktop web only.**", "- **Two products, one answer.** When a turn retrieves an official district warning and a model forecast for the same window, the answer compares them in words - consistent, differing or not comparable - names both, and never ranks them.\n- **Desktop web only.**", 1)
readme.write_text(text, encoding='utf-8')

gap = pathlib.Path('docs/31-full-solution-gap-register.md')
lines = gap.read_text().splitlines()
entry = ("- **R19 is recorded in [docs/49](49-engine-architecture-and-gap-analysis.md).** A turn now plans compound questions clause by clause "
         "(with a place named once read as the place for both clauses) and compares the products it retrieved: official district warning days "
         "against model forecast facts, and a published rain statement against the forecast, in three bounded readings - consistent, differ, "
         "not comparable - with a quiet day never read as no rain and no score, ranking, confidence or all-clear produced. **R19 closes no "
         "gap-register item**; it is one WS4 step, the live bulletin-versus-forecast path is pinned by component checks only, and WS5-WS9 "
         "remain open. 705 tests and 61 component checks passed at that checkpoint.")
for index in range(len(lines) - 1, -1, -1):
    if lines[index].startswith('- **R18 is recorded'):
        lines.insert(index + 1, entry)
        break
gap.write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
print('batches:', len(h))
