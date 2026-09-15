import json, pathlib, datetime
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
root = pathlib.Path('.')
r = root / 'README.md'
t = r.read_text()
old_tests = '# 766 Python tests'
assert t.count(old_tests) == 1
t = t.replace(old_tests, '# 774 Python tests', 1)
anchor = '- **Desktop web only.**'
assert t.count(anchor) == 1
t = t.replace(anchor, "- **One command, and a preflight that tells the truth.** `python3 scripts/start_weather.py` reports the Python version, the registries, the indexed corpus, the gazetteer, the port, the runtime store and the model providers before it serves - and it starts without a model at all, because the rules floor answers. A blocked check (a registry that does not parse, an unusable store, a taken port) refuses to start and names what to fix. No key material is printed. Measured latency over eight representative turns: p50 4.844 s, p90 6.327 s, with the rules floor planning seven of eight. See [docs/53](docs/53-operations.md)." + chr(10) + anchor, 1)
doc_anchor = '- [Language and voice, re-measured](docs/52-language-and-voice-measurement.md)'
assert t.count(doc_anchor) == 1
t = t.replace(doc_anchor, "- [Operations: one command, a preflight and measured latency](docs/53-operations.md) - a preflight that reports each state rather than refusing to start, a clean-runtime start recorded against an empty store, eight measured turns with p50 4.844 s and p90 6.327 s, the three defects that measurement found, and a release checklist with what it does not establish." + chr(10) + doc_anchor, 1)
r.write_text(t)
h = root / 'data/registry/hardening-progress.json'
d = json.loads(h.read_text())
d['operations_batch'] = {
    'report': 'docs/53-operations.md',
    'evidence_directory': 'research/implementation/operations-20260915',
    'operational_ready': False,
    'scope': "WS9 (operations): one-command start with a preflight that reports each state on its own and never prints key material, a recorded clean-runtime start against an empty store, measured latency percentiles and provider use over eight representative turns, three repairs the measurement found (a bare-null provider response crashing planning, an advisory path asking for a district it had already been given, and a publisher-spelling mismatch refusing a district that exists), and a release checklist.",
    'automated_tests': 774,
    'javascript_component_checks': 70,
    'measured': {'preflight': {'checks': 7, 'blocked': 0, 'model_providers': 'limited (no local Ollama reachable, no OpenRouter key configured)'},
                 'clean_runtime_start': {'store': 'empty ingestion store', 'health_available': False, 'question_status': 'answered', 'facts': 1},
                 'latency_seconds': {'turns': 8, 'min': 0.015, 'p50': 4.844, 'p90': 6.327, 'max': 36.127, 'mean': 7.118},
                 'providers': {'deterministic_rules/rule-planner-v1': 7, 'ollama/qwen3.6:latest': 1},
                 'failures': 0},
    'limitations': ['No load, concurrency, sustained-rate or multi-user measurement: one process, eight turns, one afternoon.',
                    'No operational clearance, uptime or service level, and hosting remains on hold.',
                    'No percentile beyond these eight observations, and no monitoring or alerting exists.',
                    'No clean-machine acceptance from a fresh clone: the corpus was not rebuilt from nothing.']}
d['updated_at_utc'] = now
h.write_text(json.dumps(d, indent=2, ensure_ascii=False) + chr(10))
p = root / 'data/registry/product-progress.json'
pd = json.loads(p.read_text())
pd['as_of_utc'] = now
pd['latest_batch'] = 'docs/53-operations.md'
p.write_text(json.dumps(pd, indent=2, ensure_ascii=False) + chr(10))
g = root / 'docs/31-full-solution-gap-register.md'
glines = g.read_text().splitlines()
inserted = False
for index in range(len(glines) - 1, -1, -1):
    if glines[index].startswith('- **R24 is recorded'):
        glines.insert(index + 1, "- **R25 is recorded in [docs/53](53-operations.md).** WS9 landed: `scripts/start_weather.py` runs a preflight instead of refusing to start without a model, and no key material is printed. A clean-runtime start was measured against an empty store (health reports the missing store honestly, and a question still answers through the governed forecast adapter). Latency was measured over eight representative turns: p50 4.844 s, p90 6.327 s, max 36.127 s (a cold district-warning read), with the rules floor planning seven of eight turns and no failures. The measurement found three defects that are repaired and pinned: a bare-null provider response crashed the planning turn, the published-advisory path asked for a district and state it had already been given, and a publisher-spelling mismatch refused a district that exists. **R25 closes no gap-register item and makes no operational claim**: no load, concurrency, uptime or clean-machine acceptance was measured, and hosting remains on hold.")
        inserted = True
        break
g.write_text(chr(10).join(glines) + chr(10))
print('README', 'docs/53' in r.read_text(), '| batch', 'operations_batch' in h.read_text(), '| R25', inserted)