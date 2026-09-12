# WeatherGPT — SIH26068

A working data foundation for a conversational weather product, with nationwide source discovery and representative agriculture, aviation, marine, hydrology and climate integrations. Current checkpoint: **development prototype; ingestion correctness and coverage gates must pass before scheduled state/national operation**. A local forecast web workspace is now implemented; no native mobile app or live warning-distribution service has been built yet.

Start the local workspace with `python3 -m weathergpt_data.workspace`, then open [WeatherGPT](http://127.0.0.1:8765). Ask a forecast question, resolve the place, refresh stale evidence and inspect cited values. The [fifth batch and product guide](docs/12-product-workspace-and-repairs.md) records the review repairs, 194 passing tests and successful live HTTP refresh. Browser/mobile visual verification is still blocked by the browser tool's policy-verification failure.

The [extensive validation and RAG gate](docs/11-extensive-validation-and-rag-gate.md) now verify all 640 historical district series against the original PDF, with 178 passing tests and 63,072 independent forecast interval checks. Use `rag-context` for controlled, verified point-forecast grounding. Full-corpus RAG, generated-answer faithfulness and operational accuracy remain unverified; see the [current RAG readiness decision](data/registry/rag-readiness.json).

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
