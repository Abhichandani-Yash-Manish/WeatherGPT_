import json, pathlib, datetime

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
TICK = chr(96)

round2 = """

## Round 2 — WS3: plan quality, and the declared benchmark at 18/18

The rules-first layer that landed in round 1 improved resilience but **regressed the declared
benchmark** from 12/18 to 11/18, with two declared tasks missing and two shape mismatches. The
cause was measured, not guessed: the rules claimed questions they could not answer (a
context-referencing follow-up, a district bulletin asked as a state one), and two resolution
rules were wrong. Six repairs followed, each pinned by tests.

| Repair | Before | After |
|---|---|---|
| Rules must not claim a context-referencing turn | "Compare the rain amount for that same morning period with GFS too" was planned fresh, with no place and no window, and asked for a place | A mid-conversation question that refers to context and carries no place of its own is left to a model; a self-contained question in a conversation is still planned by rules |
| Agriculture before generic document | "What does the Ahmedabad district agromet bulletin say about cotton?" was planned as a whole-document reading of the state family and asked for a state | Planned as agriculture/lookup with a document request carrying crop and topic, district scope, and the district read from the name |
| Administrative-unit and Hinglish place names | "Ahmedabad district" and "Kal Ahmedabad me" produced no place at all | Unit words (district, state, city) and Hinglish markers (me, mein, par, ke) are read, and a leading day word is stripped |
| Seat preference, with disclosure | A named district seat was asked about again because villages share the name | A unique administrative seat, or the one town whose own district carries its name, is accepted and **disclosed** with the alternatives; same-order peers still ask |
| Relative spans and whole days | "in the next three days" had no window; a day asked as 00:00-00:00 served 23 hours and reported partial | "next three days/next week" becomes a bounded upcoming window; a midnight-to-midnight IST day is read as the source's 00:30-to-00:30 day on both forecast paths, with the reading stated |
| Partial means reduced, not labelled | Serving a warning-classified passage made the whole reading partial | A served passage keeps its reference-only label without reducing the reading; partial stays for an unstated issue date, expired validity, a retired edition, a filtered document or a weaker disclosed match. Whole-document mode also now requires a topic-free question |

### Measured (one current-clock run each, 15 September 2026)

| Run | Cases | Turns | Declared tasks | Completed | Missing | Shape mismatches | Prohibited claims | Abstained turns | Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Development, model-only baseline (docs/45) | 17 | 19 | 18 | 12 | 0 | 0 | 0 | 3 | 66.7% |
| Development, after round 1 rules (regression) | 17 | 19 | 18 | 11 | 2 | 2 | 0 | 5 | 61.1% |
| Development, after the resolution repairs | 17 | 19 | 18 | 13 | 0 | 0 | 0 | 3 | 72.2% |
| Development, after the window and partial repairs | 17 | 19 | 18 | 16 | 0 | 0 | 0 | 0 | 88.9% |
| **Development, final** | **17** | **19** | **18** | **18** | **0** | **0** | **0** | **0** | **100%** |
| **Holdout** | **4** | **4** | **4** | **4** | **0** | **0** | **0** | **0** | **100%** |

Evidence: research/reviews/acceptance-benchmark-20260915i/development and .../holdout.
694 Python tests pass, and the two negative controls (D09 adversarial, D16 out-of-scope) still
return unavailable with no facts, which is the behaviour they exist to check.

### What this does and does not establish

- It establishes that the declared cases, at this clock, are all completed, with no missing
  task, no shape mismatch and no prohibited claim; and that the holdout agrees rather than
  contradicting, which is the check that matters after tuning against the development set.
- **The holdout is no longer sealed.** It was run in docs/45 (2/4) and again here (4/4), so it
  has been read twice. Future rounds must add fresh holdout cases before claiming generalisation
  again; until then, treat 4/4 as one measured pass, not as proof of unseen-case performance.
- Twenty-one cases are not 100% of the problem statement. Sections 1 and 4 of this document
  remain the coverage matrix; WS4-WS9 are untouched by this round.
"""
path = pathlib.Path('docs/49-engine-architecture-and-gap-analysis.md')
path.write_text(path.read_text(encoding='utf-8').rstrip(chr(10)) + chr(10) + round2, encoding='utf-8')
print('docs/49 round 2 recorded:', 'Round 2' in path.read_text())

h_path = pathlib.Path('data/registry/hardening-progress.json')
h = json.loads(h_path.read_text())
h['plan_quality_batch'] = {
    'report': 'docs/49-engine-architecture-and-gap-analysis.md',
    'evidence_directory': 'research/reviews/acceptance-benchmark-20260915i',
    'operational_ready': False,
    'scope': ('Rules-path plan quality and resolution: context-referencing turns left to a model, agriculture before generic documents, '
              'administrative-unit and Hinglish place reading, disclosed seat preference, relative spans and source-aligned days, and '
              'partial meaning a reduced reading rather than a labelled one.'),
    'automated_tests': 694,
    'javascript_component_checks': 60,
    'measured': {
        'development': {'cases': 17, 'declared_tasks': 18, 'completed': 18, 'missing': 0, 'shape_mismatches': 0,
                        'prohibited_claims': 0, 'abstained_turns': 0, 'completion_rate': 1.0},
        'holdout': {'cases': 4, 'declared_tasks': 4, 'completed': 4, 'completion_rate': 1.0},
        'baseline_for_comparison': {'docs_45_development_rate': 0.667, 'round_1_regression_rate': 0.611},
        'repaired_cases': ['D07 agriculture', 'D10 multi-turn crosscheck', 'D05 warning', 'D13 river', 'D15 Hinglish forecast',
                           'D06 document topic', 'D08 Gujarati whole day'],
    },
    'limitations': [
        'The holdout has now been read twice (docs/45 and here), so it is no longer sealed; fresh holdout cases are required before claiming generalisation.',
        'One current-clock run each; no replay, load or cross-machine measurement.',
        'Twenty-one declared cases are not the whole problem statement: WS4-WS9 remain open.',
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
text = text.replace('# 680 Python tests', '# 694 Python tests')
old_line = ('**P12** (a declared benchmark now runs: 17 development cases at 66.7% declared-task completion, '
            '4 sealed holdout cases at 2/4; the proposed 90% gate is not met and the set is below the docs/14 scale)')
new_line = ('**P12** (a declared benchmark now runs: 17 development cases at 100% declared-task completion and 4 holdout '
            'cases at 4/4 in one current-clock pass after the plan-quality repairs; the holdout has been read twice, so it '
            'is no longer sealed and the set is still far below the docs/14 scale)')
if old_line in text:
    text = text.replace(old_line, new_line, 1)
    print('README P12 line updated')
else:
    print('README P12 line not found - check manually')
text = text.replace('- [Engine and architecture: gap analysis and round 1](docs/49-engine-architecture-and-gap-analysis.md) — the provider layer',
                    '- [Engine and architecture: gap analysis, rounds 1-2](docs/49-engine-architecture-and-gap-analysis.md) — the declared benchmark moved from 66.7% to 100% on the development set and 4/4 holdout after the plan-quality repairs, with the holdout no longer sealed; the provider layer', 1)
readme.write_text(text, encoding='utf-8')

gap = pathlib.Path('docs/31-full-solution-gap-register.md')
lines = gap.read_text().splitlines()
entry = ("- **R18 is recorded in [docs/49](49-engine-architecture-and-gap-analysis.md).** Six measured repairs to the rules path and the "
         "resolution layer - context-referencing turns left to a model, agriculture before generic documents, administrative-unit and "
         "Hinglish place reading, a disclosed seat preference that still asks on same-order peers, relative spans and source-aligned days, "
         "and partial meaning a reduced reading rather than a labelled passage - moved the declared development benchmark from 66.7% "
         "(docs/45) and 61.1% (round 1 regression) to **18/18 (100%)**, with the holdout at 4/4 in the same pass, no missing tasks, no "
         "shape mismatches and no prohibited claims. **R18 closes no gap-register item and promotes no finding beyond this scope**; the "
         "holdout has now been read twice and is no longer sealed, and WS4-WS9 remain open. 694 tests passed at that checkpoint.")
inserted = False
for index in range(len(lines) - 1, -1, -1):
    if lines[index].startswith('- **R17 is recorded'):
        lines.insert(index + 1, entry)
        inserted = True
        break
gap.write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
print('registry batches:', len(h), '| R18 inserted:', inserted)
