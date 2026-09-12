# WeatherGPT — SIH26068

**Current implementation:** [Context and retrieval coverage](docs/19-context-and-retrieval-coverage.md) repairs pending crop/place replies, multi-crop questions and explicit all-passages retrieval. Earlier source cross-checks, Hinglish forecasts and airport tools remain connected. Follow the [standing product plan](data/registry/product-progress.json) and [critical review](docs/14-product-review-and-progress-plan.md). Desktop work continues; hosting/sharing stays on hold.

A local conversational weather prototype using **Ollama, source-backed forecasts and historical climate tables**. Ask ordinary questions, confirm ambiguous places and follow up in the same conversation. Nationwide and specialist operational acceptance remains incomplete.

```sh
python3 scripts/start_weather.py
```

Open [WeatherGPT](http://127.0.0.1:8765) and reload any older tab. The launcher uses the installed `qwen3.6:latest` model; no paid model gateway is required. Forecast questions check stored evidence and can trigger a bounded refresh automatically.

Try “kal ahmedabad me barish padne ki sambhavna kitni hai”, choose “Gujarat wala”, then ask “aur shaam ko?” and “kitni mm barish hogi us time?”. Or ask “What was Ahmedabad district rainfall in 2010?”—the historical source lookup returns **1096.8 mm** with provenance.

Read the [current context and retrieval results](docs/19-context-and-retrieval-coverage.md): **340 passing automated tests** and 18 real local-model HTTP turns, with 26 passage instances and 50 hourly forecast values replayed against source bytes. The [previous bulletin/lifecycle batch](docs/18-bulletin-retrieval-and-warning-lifecycle.md) retains its separate 15-turn results; the prior [conversation-engine checkpoint](docs/17-conversation-engine-refinement.md) retains its separate 23-turn results. Partial answers and clarifications are counted separately from completed requests. The earlier [conversational recovery](docs/13-conversational-recovery.md) remains a separate historical checkpoint. A GeoNames India snapshot supplies 549,021 source settlement points; this is not an official village count or complete location coverage. Hinglish forecast follow-ups and Hindi historical lookups have scoped acceptance; broader language quality and browser/mobile visual QA remain unverified.

This is structured retrieval-augmented answering: tools retrieve and calculate values, and the model interprets/explains. Hourly rain probability and up to seven daily ERA5 values per question are now supported. Actionable official warnings, exact rain onset, validated crop advice and route clearance remain unsupported. Published agricultural passages now use a versioned, crop/stage-filtered lexical and semantic retrieval path; unrestricted document grounding remains disabled. See the [current RAG readiness decision](data/registry/rag-readiness.json) and [living review checklist](docs/08-hardening-progress.md).

Try “What does the bulletin say about groundnut in Ahmedabad district, Gujarat?”, then “Show all the matching passages, not just three.” Or ask for cotton and groundnut in the same question. The original dated passages and saved PDF pages are available; individual field decisions remain unresolved. For another machine, install `requirements-bulletins.txt` and run `python3 scripts/setup_bulletin_retrieval.py` to fetch the pinned local embedding model.

Try “What is the chance of rain in Ahmedabad, Gujarat tomorrow morning?” or “Show daily rainfall in Ahmedabad city, Gujarat from 1 July through 7 July 2025, including the total.” ERA5 recent-date availability and all source/model distinctions remain explicit.

Earlier milestones below are historical evidence, not current completion claims. The [extensive validation checkpoint](docs/11-extensive-validation-and-rag-gate.md) verified historical source transcription and numerical contracts before this conversation layer existed.

The [fourth repair batch and first grounded answer workflow](docs/10-grounded-answer-workflow.md) are implemented: place/time resolution, stored forecast selection, deterministic totals and cited answers. Verified with 130 tests, 16 saved-data answer scenarios and one governed live forecast request. Start there for the `answer` command and its explicit prototype limits.

Read the [national ingestion readiness review](research/reviews/national-readiness-20260912/review.md) for newly reproduced gaps and the next implementation gates.

The [first hardening batch is verified](docs/06-hardening-batch-one.md): numeric interval/grid checks and validated cache publication, plus checkpoint protection. Broader coverage and ingestion gates remain open.

Next work follows the [PS-aligned hardening plan](docs/05-foundation-hardening-plan.md), with deliverables and acceptance gates.

The [second hardening batch](docs/07-geography-and-coverage.md) adds a versioned source geography catalogue and coverage ledger. Track all twelve review findings in the [living checklist](docs/08-hardening-progress.md); authoritative administrative mappings and operational coverage remain open.

The [third hardening batch](docs/09-bounded-ingestion.md) adds bounded numeric ingestion with shared local budgets, retry queues, recovery, transactional publication and database-first reads. Verified with 100 tests, ten saved-response replays and three live requests. It runs only when explicitly invoked.

Start with the [data foundation guide](docs/04-data-foundation.md): installation, working commands, data contracts, verification results and remaining gates.

- [Machine-readable readiness](data/registry/readiness.json)
- [Source registry and evidence](data/registry/README.md)
- [National climate pipeline](docs/03-climate-pipeline.md)
- [Earlier coverage audit](data/registry/coverage-audit.md)
- [Problem statement](docs/00-problem-statement.md)

Ahmedabad remains the shared example; the requested acceptance scope is nationwide and includes specialist coverage. Source availability, adapter correctness and operational suitability are tracked separately. Do not publicly package raw or processed source material until its reuse rights are resolved.
