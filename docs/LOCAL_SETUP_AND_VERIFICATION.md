# Local setup and verification

What this machine runs, how to start it, and what each command was measured to produce on 18 September 2026.

## 1. Start the application

```bash
# from the repository root
python3 -m venv .venv && . .venv/bin/activate        # once
pip install -r requirements.txt                       # foundation + bulletins + push
cd frontend && npm ci && npm run build && cd ..       # builds web/dist (the server serves it)
python3 -m weathergpt_data.workspace --port 8765      # the application
# open http://127.0.0.1:8765/  (the session token is injected into the page)
```

- **Ports.** The workspace defaults to 8765. This session also ran a second instance on 8790 for scripted checks;
  only one process may hold a port.
- **Token.** Every API read and write checks the per-process token printed into the served page
  (`<meta name="workspace-token">`). Restarting the server invalidates a page that is already open: **reload
  the page** after a restart, or reads answer 403.
- **No dev proxy.** `npm run dev` serves the React dev server without a token; use the built app on 8765.
- **Failure without a build.** If `web/dist` is missing the server answers 503 with the build instruction.

## 2. Optional providers (the assistant works without them)

| setting | effect |
| --- | --- |
| `WEATHERGPT_PROVIDERS=local` | the local Ollama model answers prose; facts still come from the tools |
| `WEATHERGPT_PROVIDERS=deepseek_first` (with a key) | a hosted model writes prose, validated against the facts |
| `WEATHERGPT_PROVIDERS=cloud_free` | OpenRouter free models |
| `WEATHERGPT_PLANNER=rules` | the deterministic planner only (no model call) |
| Sarvam key in the local backend environment | speech-to-text and text-to-speech |

With no provider reachable the engine still answers: the deterministic planner runs, the tools retrieve, and the
template renderer writes the answer. A missing model changes the wording, never the evidence.

## 3. Verify

```bash
python3 -m pytest tests/ -q                 # 1351 passed
cd frontend && npx tsc --noEmit && npm test # 339 checks in 61 suites
python3 scripts/verify_all.py               # 20-step gate (tests, audits, registries, drift guard)
python3 scripts/audit_react_frontend.py     # 13 checks over the built page
python3 scripts/audit_react_build.py        # 11 checks, including the bundle budget
python3 scripts/audit_surface_registry.py   # 10 checks: every route has a surface and a read
python3 scripts/audit_port_ledger.py        # 2 checks: 203 named tests still exist
```

Measured on this run: `pytest` **1351 passed**; Vitest **61 suites / 339 checks**; `verify_all.py`
**20 of 20 steps**; the frontend audit **13/13**, build audit **11/11** (initial graph inside the 312 KB gzip
budget), surface registry **10/10**, port ledger **2/2** with all 203 names verified.

## 4. Drive it like the brief's phases

| task | command |
| --- | --- |
| Route sweep with console and failed-request capture | `python3 tmp/qa/route_sweep.py` (needs the driver on 8899 and Chrome on 9333) |
| The 100 assistant questions | `python3 tmp/qa/run_100_questions.py` → `tmp/qa/ai100-results.json` |
| API ↔ UI comparison | `python3 tmp/qa/verify_api_ui2.py` |
| Responsive overflow at four widths | `python3 tmp/qa/verify_responsive.py` |

The harness in `tmp/qa/` is this session's instrument, not part of the product: `driver.py` speaks CDP to a
headless Chrome, and the scripts above are the measurements quoted in the other records.

Starting that instrument on this machine, measured 18 September 2026:

```bash
mkdir -p tmp/qa-chrome-crash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless=new --remote-debugging-port=9333 --user-data-dir=tmp/qa-chrome-profile10 \
  --crash-dumps-dir=tmp/qa-chrome-crash --disable-crash-reporter --disable-breakpad \
  --no-first-run --disable-gpu --no-sandbox &
python3 tmp/qa/driver.py --port 8899 &
```

The four crash-reporting flags are needed in a sandboxed shell: Chrome's crashpad writer is denied
`~/Library/Application Support/Google/Chrome/Crashpad`, and without these flags it aborts at launch and the
debug port never opens (measured: `Operation not permitted` in the launch log and no listener on 9333). Both
paths stay inside the workspace so nothing is written elsewhere. The first request to the driver after a fresh
start may answer `{"error": "reconnected; retry"}`; retry it. A browser that has never loaded the app sits on
an error page, so navigate to `http://127.0.0.1:8765/` before changing the hash.


## 5. First-run state versus a worked state

- `data/runtime/` holds the ingested editions, conversations, watches, plans and briefs. It is git-ignored: a
  fresh clone starts with an empty store, and every surface then states its own absence rather than showing a
  number it does not have.
- The corpus index used by the advisory and document surfaces lives in the same runtime tree; the climate and
  historical tables are published databases under `data/processed/` and are tracked.
- Documents are pruned after seven days while passages, hashes and manifests stay; `/api/documents/<sha>`
  answers 410 naming what survives for a pruned body.

## 6. Known operational limits

1. Restarting the server invalidates open pages (the token is per process). Reload.
2. The first paint of the Dashboard is slower than the single-read surfaces because it reads several routes.
3. A provider that is slow or absent delays prose; the answer falls back to the template after the validators.
4. Two workspace processes cannot share a port; the second exits with an address-in-use error.
