import json, pathlib, datetime

now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

round1 = """

## Round 1 — what landed (WS1, and the rules half of WS2)

| Landed | Where | Evidence |
|---|---|---|
| A provider layer with one interface and three providers: rules, Ollama, OpenRouter | weathergpt_data/providers.py | 21 component checks in tests/test_providers.py over stub endpoints |
| Ollama stays loopback-only; OpenRouter routes a configured list of free models with retry, model-level failover, a refused-key circuit breaker, per-call token budget and a recorded trace (provider, model, attempts, latency, tokens, route) | weathergpt_data/providers.py | tests pin the request shape (json_schema, temperature 0, max_tokens, require_parameters), 429 failover, 401 disable, 404 model-level move-on, prose and non-JSON replies |
| The key lives in local backend configuration only: OPENROUTER_API_KEY or data/runtime/model-config.json (gitignored); no key is ever printed and nothing routes to a paid model | weathergpt_data/providers.py, scripts/models.py | scripts/models.py reports the key source as a name, never a value |
| A rules-first planner for the problem-statement shapes: forecast (rain, temperature, probability, feels-like, gusts, visibility, humidity, wind), warning, history lookup / compare / series / trend, marine, river, aviation, document (including whole-edition), agriculture (crop, topic, source-lookup vs decision-support), observation and out-of-scope research | weathergpt_data/rule_planner.py | tests/test_providers.py::RulePlannerTests pins nine shapes, the IST window and the questions rules must refuse |
| One validator for both paths: interpret_plan(complete, question, now, history, seed) | weathergpt_data/language.py | the engine's existing planner tests still pass unchanged |
| The engine defaults to the router: the model is no longer the floor | weathergpt_data/conversation.py | the rules-only run below |
| Provider reporting: scripts/models.py (providers, catalogue, --check) and the doctor's provider checks | scripts/models.py, scripts/doctor.py | scripts/models.py --check output and the doctor run below |

### Measured on this machine (15 September 2026)

- **680 Python tests pass**, 60 component checks, verify_all 21/21.
- **The engine answers with no model provider at all.** With the router built with an empty
  client list, three real journeys ran: the forecast question answered 0.0 mm from S21
  (Open-Meteo GFS) with the place resolved through S61; the 1990 annual rainfall question
  answered 983.6 mm from S27; the ambiguous warning question asked which Patna was meant and
  listed the candidates. Evidence:
  research/implementation/provider-layer-20260915/rules-only-engine.json.
- **Ollama takes 35.8 s** for one follow-up plan on this machine, which is the measured
  argument for routing to a hosted free model when a key exists.
- **Doctor**: 14 ok, 1 warning (no OpenRouter key configured), 0 failures, and the next action
  names the configuration file.
- **scripts/models.py --check** proves both paths: the rules path plans the core question with
  provider deterministic_rules, and the follow-up is planned by Ollama.

### What round 1 did not do

- No live OpenRouter call: no key is configured in this workspace yet, so the adapter is pinned
  by stub-endpoint checks and the key is reported missing rather than assumed. Adding it is one
  line of local configuration and one command.
- The rule planner covers the common English and Hinglish shapes; Indic scripts and follow-ups
  deliberately fall through to a model rather than guess.
- Plan quality with the new layer is not yet measured by the benchmark: that is WS3, the next
  round, and it is where the declared-task number is expected to move.
"""
path = pathlib.Path('docs/49-engine-architecture-and-gap-analysis.md')
path.write_text(path.read_text(encoding='utf-8').rstrip(chr(10)) + chr(10) + round1, encoding='utf-8')
print('docs/49 updated:', 'Round 1' in path.read_text())

h_path = pathlib.Path('data/registry/hardening-progress.json')
h = json.loads(h_path.read_text())
h['provider_layer_batch'] = {
    'report': 'docs/49-engine-architecture-and-gap-analysis.md',
    'evidence_directory': 'research/implementation/provider-layer-20260915',
    'operational_ready': False,
    'scope': ('Model access and the rules-first floor: one provider interface over rules, Ollama and '
              'OpenRouter, free-model routing with retry/failover/budget and a recorded trace, and a rule '
              'planner for the problem-statement shapes so the product plans and answers with no model.'),
    'automated_tests': 680,
    'javascript_component_checks': 60,
    'measured': {
        'providers': ['rules', 'ollama', 'openrouter (not configured on this machine)'],
        'rule_shapes_covered': ['forecast', 'warning', 'history lookup/compare/series/trend', 'marine', 'river',
                                'aviation', 'document', 'agriculture', 'observation', 'research'],
        'rules_only_engine': {'turns': 3, 'answered': 2, 'needs_selection': 1, 'model_calls': 0},
        'ollama_follow_up_latency_ms': 35821,
        'free_models_configured': 6,
        'doctor': {'ok': 14, 'warn': 1, 'fail': 0},
    },
    'limitations': [
        'No live OpenRouter call yet: the key is not configured in this workspace.',
        'The rule planner covers English and Hinglish common shapes; Indic scripts and follow-ups use a model.',
        'Plan quality under the new layer is not yet measured by the declared benchmark.',
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
text = text.replace('# 659 Python tests', '# 680 Python tests')
text = text.replace('python3 scripts/doctor.py                            # environment, model and corpus presence',
                    'python3 scripts/doctor.py                            # environment, providers and corpus presence' + chr(10) +
                    'python3 scripts/models.py --check                    # the rules-first floor and the configured providers')
text = text.replace('No paid gateway is required, and the server answers only on loopback with a per-process session token.',
                    'The engine plans the core question shapes with rules and no model at all, and the rest through '
                    'whatever providers exist. Optional: add an OpenRouter key to data/runtime/model-config.json to route '
                    'free models after Ollama; the key stays in local configuration. No paid gateway is required, and the '
                    'server answers only on loopback with a per-process session token.', 1)
text = text.replace('- [The intake holds what it cannot verify](docs/48-intake-publication-identity.md) — publication identity is content and address',
                    '- [Engine and architecture: gap analysis and round 1](docs/49-engine-architecture-and-gap-analysis.md) — the provider layer with OpenRouter-free routing and a rules-first floor that answers with no model at all, plus the WS1-WS9 plan to full problem-statement coverage.' + chr(10) +
                    '- [The intake holds what it cannot verify](docs/48-intake-publication-identity.md) — publication identity is content and address', 1)
readme.write_text(text, encoding='utf-8')

gap = pathlib.Path('docs/31-full-solution-gap-register.md')
lines = gap.read_text().splitlines()
entry = ("- **R17 is recorded in [docs/49](49-engine-architecture-and-gap-analysis.md).** The engine gained a provider "
         "layer (rules, Ollama, OpenRouter over a configured free-model pool with retry, failover, budget and a recorded "
         "trace) and a rules-first planner for the problem-statement shapes, so the product plans and answers with no "
         "model at all: a rules-only engine run answered a forecast question from S21 and a 1990 rainfall lookup from "
         "S27, and asked which Patna was meant on the ambiguous one. **R17 closes no gap-register item by itself**; it "
         "removes the model as the single point of failure and sets up WS1-WS9 toward the PS coverage matrix. No live "
         "OpenRouter call has been made yet because no key is configured here. 680 tests passed at that checkpoint.")
for index in range(len(lines) - 1, -1, -1):
    if lines[index].startswith('- **R16 is recorded'):
        lines.insert(index + 1, entry)
        break
gap.write_text(chr(10).join(lines) + chr(10), encoding='utf-8')
print('registry batches:', len(h), '| latest_batch:', p['latest_batch'])
print('README updated:', '680 Python tests' in readme.read_text(), '| R17:', 'R17 is recorded' in gap.read_text())
