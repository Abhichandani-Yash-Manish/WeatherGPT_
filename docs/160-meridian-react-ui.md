# Meridian Light in the active React frontend

22 September 2026. Local implementation and scoped verification; no deployment or PS acceptance claim.

## Direction and authority

The user selected the second Meridian concept, requested a calm **light** theme for evaluators, substantial stateful motion and no glassmorphism, then explicitly directed work into the active React frontend. This supersedes the dark/solar/glass material choices in docs/111 and docs/134. Their evidence remains historical. The product rules of docs/14, docs/21, docs/72, docs/108 and the later engine batches still apply.

The review traced `src/main.tsx → App.tsx → gpt/Workspace.tsx`, the live conversation controller, source receipts, voice path, route host and build configuration. React builds into `web/dist`; `web/tokens.css` and `web/tokens-v2.css` are still imported dependencies. No retired HTML interface was reactivated or edited. The independent exploration under `research/design/2026-09-22-meridian-light` is a prototype, not the production entry point.

Research and alternatives are preserved in `research/design/2026-09-22-overhaul/design-brief.md` and `research/design/2026-09-22-motion-direction/motion-and-material.md`. The selected image is recorded in the design QA note beside the prototype. No additional library was necessary: the active app already has Motion, Lucide and HeroUI.

## What changed

- A fixed mineral-white ground, slate ink and one muted blue accent. Matte rail, header, question, composer, reading panel, cards and receipts replace the active glass materials. Published warning hues retain their separate meaning and measured contrast.
- Original contour artwork forms the decorative atmosphere. It moves over 24 seconds at rest and 8 seconds while a real request runs; composing pauses and dims it. A visible pause control persists locally. Hidden tabs pause it; reduced-motion CSS stops it. It is neither a weather map nor a condition report.
- The actual astronomical hour remains in the welcome mark. The decorative city skyline was removed from the opening. Existing place, observed condition, source and verse behavior remain connected.
- Each answer has its own source margin. A source disclosure retains **every** citation for that source, including different editions, read times, hashes, pages and URLs. The conversation-wide source inventory stays separately in the reading panel.
- A matching comparison becomes a compact table for two or three places and two sources. The UI only uses values already returned as facts or engine calculations. It does not sum samples. Missing inputs, duplicate totals, differing entities/parameters/units/windows, gaps, overlaps and observations fall back to the original claims. All detailed values and receipts remain available. An answer with published warnings stays in the original open evidence layout.
- The composer exposes held-place and answer-language controls through the real reading panel. It retains recording, transcript confirmation, send and stop behavior. IME confirmation no longer submits a partially composed question.
- Real engine stage changes receive an entrance transition, with the existing state-mapped activity orb and stage history. No invented progress percentage or timed fake retrieval stage was introduced. The wait no longer incorrectly claims every model is local.
- Watch receives a sticky section navigator and the shared matte treatment. No watch, push consent, delivery or subscription is created by a design action.
- A copy-feedback timeout found during final regression testing is cleared when its claim unmounts; repeated copies restart that feedback timer safely.

## Evidence and guardrails

The retained design-review mapping is P01/P02 provenance; P03 and F01/F02 task/context completeness; P06/P10/P11 and R02/R08 warning and delivery semantics; P07/R09/F07/A06 bulletin context; P08/R01/R10/F03/F04 place identity; P12/P13/F10/A02 language honesty; P15/R11/R12/A07 evidence-backed progress. This UI batch does not close their wider acceptance gaps. `hardening-progress.json` and the PS scorecard are unchanged.

The provenance walker now recognizes the narrow citation-id/receipt regions as metadata, with a component test pinning two editions, their hashes and links to their owning packet. Weather values still require the existing claim/calculation checks. FE14 and FE16 now measure the active Meridian palette as well as the historical palettes. FE15 checks the selected stable light ground instead of claiming that the active interface must switch between day and night colors. The live port ledger names the revised front-door test; historical packet evidence is unchanged.

The full 21-step repository gate passed, including 1,630 backend tests and all 85 React suites. The final React rerun after the Watch navigation, keyboard-scroll region and copy-timer repair is recorded separately: 559 checks. TypeScript and production build are checked. Evidence lives in `research/design/2026-09-22-meridian-light/verification/`.

Browser work used the main Python-served React app on port 8765, not the prototype. A fresh Surat/Vadodara comparison returned through the real engine; source disclosures, restored receipts, composer settings, narrow layout, warning overview and Watch were inspected. The matrix preserves S21 zero totals and S62 0.4/0.2 mm from the actual returned packet. These are one question's recorded values, not a current public forecast claim or forecast-skill benchmark.

## Limits carried forward

The full set of module workflows has not received fresh visual acceptance in this batch; the shared design layer applies to them, with live checks concentrated on chat, the warning overview, reading settings and Watch. The 360px check establishes bounded layout and reachable controls, not mobile PS acceptance. No real-device voice/push journey or sustained animation-performance benchmark was run. The existing build still reports a large main-chunk warning. Runtime conversations remain local.

Watch still exposes conflicting **backend-returned** lifecycle wording in its receipts and limits (including older text claiming no push channel beside current opt-in push machinery). This was observed and is not concealed by the visual redesign. Resolving that contract needs its own evidence-backed product repair; this batch does not relabel a stale service as healthy.

An open tab can reference old hashed chunks after the local production directory is rebuilt. During QA, one such navigation hit the existing error boundary; reloading the workspace fetched the current build and the route worked. No deployment or zero-downtime release claim is made.
