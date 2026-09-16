# 90 — The flagship transcript, the first real modules, and the front door

17 September 2026. The user asked for the whole React overhaul to be taken to a flagship standard: *every
animation, every page, every small component*, no compromises, brainstorm and build wherever there is
potential. This document records what that produced, what was measured, and what is still open. It changes no
claim made elsewhere; where it finds a defect it names the measurement that found it.

## 1. What this batch delivers

| Deliverable | Where | State |
| --- | --- | --- |
| The transcript (R2, the flagship) | `frontend/src/chat/` | the question is kept, the working turn names the engine's stages and its provisional first reading, the answer card carries the lead value, the validity ruler, the other facts, the receipt, the sources, the disclosures and the actions |
| The reading register | transcript rail | `brief` / `conversational` / `full`, remembered per browser, changing how much of the evidence is unfolded and nothing else |
| Voice path | composer + `chat/voice.ts` | recording → the engine's transcript for correction, labelled with the recogniser's own confidence and the rule that speech is refused where the project has not measured it |
| Stored conversations | transcript rail | the ledger, a filter, open and delete, with the engine's own note about what the store is |
| Six real modules (R3, first tranche) | `frontend/src/modules/` | Today, Warnings, Forecast, Observations, Published documents, Sources and settings — each rendering its envelope with coverage, limitations, not-established and source rows |
| Module host | `shell/SurfaceHost.tsx`, `modules/registry.ts` | one lazily loaded chunk per module; a module that is not ported says which stage it arrives in and offers its questions to the conversation |
| The front door and the owner gate (R7) | `src/landing/` | an honest landing page with live reads and the README's own limits, and a local passphrase gate that explains what it is not before asking for anything |
| Shell work | `shell/` | command palette (Alt+K), reading-position switch, theme cycle, sky phases from the local clock, one route hook for surfaces and shell routes |
| The check-port ledger | `scripts/audit_check_port.py`, `research/reviews/frontend-react-r2-20260917/check-port.json` | 19 of the 110 vanilla component checks now name a React counterpart, and every named test is verified to exist |
| Pictures of this build | `frontend/public/shots/`, `research/reviews/frontend-react-r2-20260917/shots-clean/` | ten captures at 1440×900 from a throwaway store, taken in headless Chrome against the served build |

The build gate is unchanged: `verify_all.py` stays green and the vanilla frontend stays the default until R6.

## 2. Measured

| Measure | Value | How it was measured |
| --- | --- | --- |
| Frontend component checks | **10 suites, 68 checks** | `cd frontend && npx vitest run` |
| TypeScript | **0 errors** | `npx tsc --noEmit` |
| Initial bundle graph | **107 KB gzip** against the 312 KB budget | `scripts/audit_react_build.py`, which follows the manifest's static imports |
| Per-module chunks | 2.2–2.6 KB gzip each | the same manifest: each module is its own lazy chunk |
| Built-output audit | 11 of 11 pass | `scripts/audit_react_build.py` |
| Surface registry audit | 8 of 8 pass | `scripts/audit_surface_registry.py` |
| Check-port ledger | 5 of 5 pass | `scripts/audit_check_port.py` |
| Live HTTP acceptance of the served build | **14 of 14 pass** | `research/reviews/frontend-react-r2-20260917/live-r2.py` (page, token, CSP, hashed assets, authorised and refused reads, a real turn, progress, preview) |
| A real turn through the served build | 43.14 s cold, 4.72 s warm | the same run, against the configured providers |
| Browser evidence | 10 screenshots at 1440×900 | headless Chrome (agent-browser) against `--frontend react` on loopback, throwaway store |

## 3. Defects the port found, and how each was fixed

These are the reason the plan insisted the checks be ported rather than rewritten: the harness found four real
defects, and each is now a check.

1. **jsdom's `AbortSignal` is not the one the fetch implementation accepts.** Every read through `src/api/client.ts`
   failed in tests with `Expected signal ("AbortSignal {}") to be an instance of AbortSignal`, and the client
   reported it as "the workspace did not answer". Two fixes, both kept: the client now creates a controller only
   when there is something to cancel or a timeout to bound, and the harness supplies the class the fetch
   implementation accepts instead of the product giving up cancellation.
2. **A turn's question was replaced by its own answer.** The user turn and the answer shared one key, and the
   reducer dropped the turn with that key before appending the answer — so the transcript showed an answer with no
   question above it. Found by the first transcript check; the question, the answer and the notice are now three
   identities, and the check asserts the question is still there.
3. **jsdom has no `Element.scrollTo` and no modal `<dialog>`.** The transcript and the palette ask the browser for
   real behaviour rather than reimplementing it; the transcript now degrades to a plain scroll assignment, and the
   harness gains `showModal`/`close`.
4. **This Node build ships no `localStorage`.** The register and theme preferences silently had nowhere to live, so
   the harness provides in-memory storage and the preference paths are exercised rather than skipped.

## 4. The transcript, in detail

`src/chat/model.ts` is the ported rule set: status labels, which statuses are *held*, the evidence-kind names, the
parameter names, the warning parameter that is drawn as an official statement rather than a fact row, the
fact-ordering rules (a value a chart already draws is not repeated as a row), the language-downgrade note, the
task-coverage sentence and the register vocabulary. `web/views.js` stayed the specification; the wording a reader
has already seen is part of the product.

The card order is the argument it makes: what was asked, what came back, how far it is valid, where it came from,
and only then the machine record. A reader who stops after the first sentence has still seen the source and the
retrieval time.

The working turn is deliberately modest: it names the stage the server reports (`/api/chat/progress`), shows the
deterministic first reading (`/api/chat/preview`) labelled as a reading and not evidence, counts elapsed time as
elapsed time, and offers **Stop**, whose reply is the server's own sentence about the next stage boundary — never a
claim that the server stopped. No percentage, no ETA, no confidence.

## 5. The modules, and what a module owes a reader

Each of the six surfaces renders its envelope: the view and status line, the coverage counts, the limitations and
the not-established list as visible sections, the source table, and a failure sentence with a retry when the read
fails. The Warnings surface draws a hazard colour only where the payload stated one for that district-day, and
prints the product's own hazard wording beside it; a district-day with no stated colour gets a word, never a
colour. Today states that a colour is exactly what the product returned. Forecast states that a missing point is a
gap and never a zero. Documents renders a 410 as the edition's stated state — what was pruned and what survives —
rather than as a crash. Settings states each provider's own availability, including "not recorded" when the flag
is absent.

`frontend/src/modules/modules.test.tsx` (13 checks) asserts those rules against payloads shaped from the real
product API, including a count of `[data-colour]` chips against the colours the payload stated.

## 6. The front door, and the gate

The landing page states the product in one breath, shows the **shape** of a receipt with words where a value would
go (a front page that printed an unread value would make the one claim this product refuses to make), reads four
counts live from this machine with the read time beside each, lists the nineteen surfaces from the same registry
the rail uses, quotes the README's limits verbatim, and shows eight pictures of this build. A failed read says the
read failed; no number is invented.

The owner gate derives a PBKDF2-SHA-256 verifier in the browser (16-byte salt, 600 000 iterations, 256-bit) and
keeps only `{v, salt, iterations, hash}`. It explains what it is not before asking for anything, offers *skip*,
and never claims to be authentication or encryption. It does not stand in the way by default: with no verifier
set, the workspace is exactly as open as it has always been, and the gate appears when an owner has set a
passphrase and left the interface locked, or when a reader asks for it.

## 7. What is not done

- **Thirteen surfaces are still placeholders**: map, farm advisories, air quality, aviation, what changed, climate,
  sea and rivers, ensemble spread, forecast verification, compare places, briefcase, workspace, and the deep-link
  brief pages. Each states its stage and offers its questions to the conversation in the meantime.
- **The port ledger covers 19 of 110 vanilla checks.** The vanilla suites remain the regression net and still run
  in `verify_all.py` until R6; `docs/86` keeps the one-for-one port as R2's gate and this batch does not claim it
  is complete.
- **No screen-reader, keyboard-only or contrast acceptance per surface.** The foundation is in (one `h1` per
  surface, real tables, `aria-live` on changing counts, focus-visible rings, reduced-motion gating), but no
  recorded audit exists yet. R5 is that work.
- **No SSE seam**: the answer still arrives as one response; the stages are polled.
- **Voice**: the interface path is built and the measured-language rules are enforced, but no real-audio or field
  acceptance has been recorded.
- **Mobile and hosting** are unchanged: desktop web is the surface, hosting is held.

## 8. Evidence

- `research/reviews/frontend-react-r2-20260917/live-r2.py` and `live-r2.json` — the served build read over HTTP.
- `research/reviews/frontend-react-r2-20260917/check-port.json` — the port ledger the audit verifies.
- `research/reviews/frontend-react-r2-20260917/shots-clean/` — the ten captures, and
  `frontend/public/shots/` — the eight the landing page shows.
- `scripts/audit_check_port.py` — now a step of `scripts/verify_all.py`.

## 9. What comes next

1. The remaining surfaces in the docs/88 ranking order: map and what-changed next (PS feature 4 is still the
   weakest journey), then farm advisories, air quality, climate, marine, ensemble, verification, compare,
   briefcase and the workspace panel.
2. The rest of the check port, suite by suite, with the ledger as the record.
3. Charts (R4): `web/viz.js` wrapped as a component so a returned series is drawn by the engine that already has
   checks, then print parity for a card.
4. R5: the accessibility, RTL and language acceptance runs, with recorded evidence per surface.
5. R6: decommission the vanilla path once `verify_all.py` passes on the React-only tree.
