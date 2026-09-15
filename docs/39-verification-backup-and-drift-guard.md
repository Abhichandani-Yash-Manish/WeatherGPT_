# Verifiable setup, state backup and the drift guard — 15 September 2026

[The gap register](31-full-solution-gap-register.md) recorded **G15** (reproducible setup, packaging and a retention/restore rehearsal) and **G17** (progress accounting drift: README, docs and registries disagreeing with the code). This batch adds one command that verifies the workspace, a verified backup/restore path for the local stores, and a guard that fails when the current summary drifts from what pytest actually collects.

## One verification command

python3 scripts/verify_all.py runs 18 steps and fails loudly: Python version, Node availability, dependency files, every registry JSON (sources, source review, product progress, hardening progress, language support, acceptance benchmark, answer policy), the status drift guard, the Python suite, and all five JavaScript component suites. It changes no runtime state.

A live run on this machine: **18 steps, 0 failed**, with 631 Python tests passing.

## Dependencies

requirements.txt now names the runtime dependencies and includes the two tested files (pypdf, shapely, pdfplumber, sentence-transformers, pinned to the versions the workspace was verified with). Ollama and the local model weights are not pip dependencies and stay documented in the README. Python 3.9+ and Node are checked by the verify script.

## Backup and restore, rehearsed on the real stores

weathergpt_data/state_backup.py copies SQLite stores through the backup API (no torn reads), records every file size and sha256 in a manifest, and refuses to write into an existing directory. Restore verifies the whole manifest before writing anything, so a tampered or partial backup restores nothing rather than half a store. The excluded set is stated: document bodies and raw evidence blobs, source response caches, model files.

Rehearsal evidence: research/implementation/packaging-rehearsal-20260915/summary.json. The backup contained conversations.sqlite, watches.sqlite, ingestion.sqlite and the bulletin index (about 96 MB across four stores), and the restore reproduced **369 conversation rows from 369** in a fresh directory. The backup itself was kept outside the repository because it holds runtime conversation payloads, which must not be published; only counts, sizes and hash prefixes are recorded.

## The drift guard

scripts/check_status_drift.py fails when:

- README's recorded Python test count differs from what pytest collects,
- a batch document, plan or evidence path named by product-progress or hardening-progress does not exist,
- a finding status is outside the declared vocabulary,
- the source ledger's counts disagree with its own rows, or
- a registry does not parse.

It found real drift on its first run (README said 611 tests while pytest collected 631) and is now part of the verify command.

## What this does not establish

- **No CI service, container or one-click installer.** The verify command is the reproducible entry point on a machine that already has Python, Node and Ollama.
- **No full disaster recovery.** The backup covers the runtime stores, not source PDFs, model weights or the operating environment, and no off-machine copy is made.
- **No continuous monitoring.** The drift guard runs when it is invoked, not on a schedule.
- **No published runtime content.** Conversations, watches and logs stay local and out of Git.

## The batches as commits, 15 September 2026

Everything recorded in docs/31–docs/46 was committed in planned phases and pushed to
`origin/main` on 15 September 2026, newest first:

| Commit | Contents |
|---|---|
| `d6c5d6b` | Registers, README, the docs/14 pointer, docs/31 R14, the registry README counts |
| `9e1e783` | The Instrument Desk frontend batch (docs/46), its evidence and the measurement scripts |
| `95f3788` | Speech round trips, document retention and forecast vintages (docs/40–43) |
| `1981c64` | Bounded queue and cancellation, context edits, alias candidates, watches (docs/34, 36, 37, 38) |
| `55a2c57` | Conversational corpus, planner repair, source ledger and language write reach (docs/30, 32, 33) |
| `34e0ca6` | The declared acceptance benchmark and its sealed holdout (docs/35, 45) |
| `6421aa7` | The verification, backup/restore and drift-guard batch (docs/39) |

Each phase staged its own files, and the tree was clean with `scripts/verify_all.py`
reporting 21 steps, 0 failed on the committed state. The earlier batches (docs/01–30) were
already committed. Runtime stores, the browser profile and scratch probes are not in Git;
the measurement scripts that produced the frontend evidence are.

The [answer transparency and edition coverage](47-answer-transparency-and-edition-coverage.md) batch followed the same pattern: one commit for the code and tests, one for the recorded evidence and the measurement scripts, one for the documents and registers, and one for the per-document passage lookup.
The [intake publication identity](48-intake-publication-identity.md) cycle followed the same pattern: one commit for the repairs and their tests, one for the recorded evidence and the scripts that produced it, and one for the documents and registers.


